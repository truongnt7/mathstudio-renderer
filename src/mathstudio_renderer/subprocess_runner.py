"""Controlled Manim subprocess runner.

Security invariants
-------------------
* ``shell=False`` — always and unconditionally.
* The command list is constructed from registry-trusted values only.
* A sanitized environment is built from an explicit allowlist; the host
  environment is never passed through wholesale.
* The process is started in a new session (``start_new_session=True``) so
  that a SIGKILL to the process group terminates any child Manim sub-processes.
* Timeout enforcement uses SIGTERM → wait → SIGKILL escalation.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .errors import ErrorCode, RenderError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Maximum seconds to wait for graceful SIGTERM shutdown before SIGKILL
_GRACEFUL_WAIT_S = 5.0

# Keys copied from the host environment into the sanitized subprocess env.
# Everything else is stripped.
_SAFE_ENV_KEYS = frozenset(
    {
        "PATH",
        "HOME",
        "USER",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TMPDIR",
        "TMP",
        "TEMP",
        "DISPLAY",
        "FONTCONFIG_PATH",
        "XDG_DATA_DIRS",
        # Manim / Cairo-specific env vars that are safe to forward
        "MANIMGL_OPENGL_RENDERER",
    }
)

# Manim quality flag mapping
_QUALITY_FLAG: dict[str, str] = {
    "preview": "-ql",
    "final": "-qh",
}

# Expected Manim output sub-directory per quality
_QUALITY_SUBDIR: dict[str, str] = {
    "preview": "480p15",
    "final": "1080p60",
}


class SubprocessResult:
    __slots__ = ("returncode", "stdout", "stderr")

    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class RenderSubprocessRunner:
    """Runs Manim as a controlled subprocess."""

    def __init__(self, timeout: float = 120.0) -> None:
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_manim(
        self,
        scene_file: Path,
        scene_class: str,
        quality: str,
        media_dir: Path,
        timeout: float | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> SubprocessResult:
        """Invoke the Manim CLI with trusted, registry-derived arguments.

        Parameters
        ----------
        scene_file:
            Absolute path to the scene .py file — resolved from the registry,
            never from request data.
        scene_class:
            Scene class name — from the registry, never from request data.
        quality:
            "preview" | "final"
        media_dir:
            Manim media output directory (inside the request workspace).
        timeout:
            Per-request override; falls back to ``self.timeout``.
        extra_env:
            Additional safe environment variables (allowlisted).
        """
        cmd = self._build_command(scene_file, scene_class, quality, media_dir)
        env = self._build_env(extra_env)
        effective_timeout = timeout if timeout is not None else self.timeout

        logger.info(
            "Spawning Manim subprocess",
            extra={
                "cmd": cmd,
                "scene_class": scene_class,
                "quality": quality,
                "timeout_s": effective_timeout,
            },
        )

        return self._run(cmd, cwd=scene_file.parent, env=env, timeout=effective_timeout)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_command(
        self,
        scene_file: Path,
        scene_class: str,
        quality: str,
        media_dir: Path,
    ) -> list[str]:
        quality_flag = _QUALITY_FLAG.get(quality, "-ql")
        return [
            sys.executable,  # same interpreter that runs the renderer
            "-m",
            "manim",
            "render",
            quality_flag,
            "--media_dir",
            str(media_dir),
            "--disable_caching",
            "--",
            str(scene_file),
            scene_class,
        ]

    def _build_env(self, extra: dict[str, str] | None) -> dict[str, str]:
        """Return a sanitized environment dictionary."""
        env: dict[str, str] = {}
        for key in _SAFE_ENV_KEYS:
            if key in os.environ:
                env[key] = os.environ[key]
        if extra:
            for k, v in extra.items():
                if k in _SAFE_ENV_KEYS:
                    env[k] = v
        return env

    def _run(
        self,
        cmd: list[str],
        cwd: Path,
        env: dict[str, str],
        timeout: float,
    ) -> SubprocessResult:
        proc = subprocess.Popen(  # noqa: S603
            cmd,
            shell=False,  # NEVER shell=True
            env=env,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,  # new process group → clean kill
        )

        # Record process group id immediately
        pgid: int | None = None
        try:
            pgid = os.getpgid(proc.pid)
        except (ProcessLookupError, PermissionError):
            pass

        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            stdout, stderr = self._kill_and_drain(proc, pgid, timeout)
            raise RenderError(  # noqa: B904
                code=ErrorCode.RENDER_TIMEOUT,
                message=f"Manim process timed out after {timeout:.0f}s",
                diagnostics={
                    "timeout_s": timeout,
                    "stdout_tail": stdout[-2000:],
                    "stderr_tail": stderr[-2000:],
                },
            )

        logger.debug(
            "Manim subprocess exited",
            extra={"returncode": proc.returncode, "stderr_tail": stderr[-500:]},
        )

        if proc.returncode != 0:
            raise RenderError(
                code=ErrorCode.RENDER_PROCESS_FAILED,
                message=f"Manim exited with code {proc.returncode}",
                diagnostics={
                    "returncode": proc.returncode,
                    "stdout_tail": stdout[-3000:],
                    "stderr_tail": stderr[-3000:],
                },
            )

        return SubprocessResult(proc.returncode, stdout, stderr)

    def _kill_and_drain(
        self,
        proc: subprocess.Popen[str],
        pgid: int | None,
        timeout: float,
    ) -> tuple[str, str]:
        """Send SIGTERM to process group, escalate to SIGKILL, drain pipes."""
        logger.warning(
            "Render timed out — sending SIGTERM",
            extra={"pid": proc.pid, "timeout_s": timeout},
        )
        self._send_signal(pgid, proc, signal.SIGTERM)

        try:
            proc.wait(timeout=_GRACEFUL_WAIT_S)
        except subprocess.TimeoutExpired:
            logger.warning("SIGTERM ignored — sending SIGKILL", extra={"pid": proc.pid})
            self._send_signal(pgid, proc, signal.SIGKILL)
            proc.wait()

        # Drain any buffered output from the pipes
        stdout = stderr = ""
        try:
            stdout, stderr = proc.communicate(timeout=2.0)
        except Exception:  # noqa: BLE001,S110
            pass
        return stdout, stderr

    @staticmethod
    def _send_signal(pgid: int | None, proc: subprocess.Popen[str], sig: signal.Signals) -> None:
        if pgid is not None:
            try:
                os.killpg(pgid, sig)
                return
            except (ProcessLookupError, PermissionError, OSError):
                pass
        try:
            proc.send_signal(sig)
        except (ProcessLookupError, PermissionError, OSError):
            pass


# Singleton used by the runtime
def quality_subdir(quality: str) -> str:
    """Return the Manim output sub-directory name for a quality preset."""
    return _QUALITY_SUBDIR.get(quality, "480p15")
