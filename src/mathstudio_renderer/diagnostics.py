"""Diagnostics collection — internal only, never exposed to untrusted callers."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from typing import Any


def _run_version_cmd(cmd: list[str]) -> str:
    try:
        r = subprocess.run(  # noqa: S603
            cmd,
            shell=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return (
            (r.stdout + r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr) else "unknown"
        )
    except Exception as exc:
        return f"error: {exc}"


def collect_runtime_info() -> dict[str, Any]:
    """Collect renderer runtime diagnostics for internal logging."""
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "ffmpeg": shutil.which("ffmpeg") or "not found",
        "ffprobe": shutil.which("ffprobe") or "not found",
        "latex": shutil.which("latex") or "not found",
        "dvisvgm": shutil.which("dvisvgm") or "not found",
        "manim": _get_manim_version(),
    }


def _get_manim_version() -> str:
    try:
        import manim  # type: ignore[import-untyped]

        return str(getattr(manim, "__version__", "unknown"))
    except ImportError:
        return "not importable"


def collect_render_diagnostics(
    stdout: str,
    stderr: str,
    returncode: int,
    elapsed_ms: float,
    workspace_dir: str,
) -> dict[str, Any]:
    """Collect per-render diagnostics — safe subset for storage."""
    # Truncate stdout/stderr to avoid huge files
    return {
        "returncode": returncode,
        "elapsed_ms": round(elapsed_ms, 1),
        "stderr_tail": stderr[-2000:] if stderr else "",
        "stdout_tail": stdout[-500:] if stdout else "",
        # workspace_dir is an internal path — do NOT include in external responses
        # but safe to store in internal diagnostics.json
        "workspace": workspace_dir,
    }
