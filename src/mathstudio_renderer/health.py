"""Renderer health and readiness checks."""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Any

from .config import config


def _check(name: str, fn: Any) -> dict[str, Any]:
    try:
        result = fn()
        return {"name": name, "status": "ok", "detail": result}
    except Exception as exc:
        return {"name": name, "status": "fail", "detail": str(exc)}


def check_python() -> str:
    version = sys.version.split(" ")[0]
    major, minor = (int(x) for x in version.split(".")[:2])
    if major < 3 or (major == 3 and minor < 12):
        msg = f"Python >=3.12 required, got {version}"
        raise RuntimeError(msg)
    return version


def check_manim_import() -> str:
    import manim  # type: ignore[import-untyped]

    version: str = str(getattr(manim, "__version__", "unknown"))
    return version


def check_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("ffmpeg not found in PATH")
    r = subprocess.run(  # noqa: S603, S607
        ["ffmpeg", "-version"],
        shell=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    first = r.stdout.splitlines()[0] if r.stdout else ""
    return first


def check_ffprobe() -> str:
    path = shutil.which("ffprobe")
    if not path:
        raise RuntimeError("ffprobe not found in PATH")
    return path


def check_latex() -> str:
    path = shutil.which("latex")
    if not path:
        raise RuntimeError("latex not found in PATH (MathTex will fail)")
    r = subprocess.run(  # noqa: S603, S607
        ["latex", "--version"],
        shell=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    first = (r.stdout + r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr) else "unknown"
    return first


def check_dvisvgm() -> str:
    path = shutil.which("dvisvgm")
    if not path:
        raise RuntimeError("dvisvgm not found in PATH (MathTex will fail)")
    return path


def check_font(font_name: str = "Noto Sans") -> str:
    """Verify a Vietnamese-capable font is registered with Pango."""
    try:
        import manimpango  # type: ignore[import-untyped]  # noqa: PGH003

        fonts: list[str] = manimpango.list_fonts()
        matched = [f for f in fonts if font_name.lower() in f.lower()]
        if not matched:
            msg = (
                f"Font '{font_name}' not found in Pango font list. "
                "Vietnamese text may fall back to a different font."
            )
            raise RuntimeError(msg)
        return matched[0]
    except ImportError as exc:
        raise RuntimeError("manimpango not importable — cannot check fonts") from exc


def check_workspace_writable() -> str:
    d = config.workspace_dir
    d.mkdir(parents=True, exist_ok=True)
    probe = d / ".health_probe"
    probe.write_text("ok")
    probe.unlink()
    return str(d)


def check_output_writable() -> str:
    d = config.output_dir
    d.mkdir(parents=True, exist_ok=True)
    probe = d / ".health_probe"
    probe.write_text("ok")
    probe.unlink()
    return str(d)


def run_health_checks(deep: bool = False) -> tuple[bool, list[dict[str, Any]]]:
    """Run all health checks; return (hard_ok, results)."""
    checks: list[tuple[str, Any]] = [
        ("python", check_python),
        ("manim_import", check_manim_import),
        ("ffmpeg", check_ffmpeg),
        ("ffprobe", check_ffprobe),
        ("latex", check_latex),
        ("dvisvgm", check_dvisvgm),
        ("font_noto_sans", lambda: check_font("Noto Sans")),
        ("workspace_writable", check_workspace_writable),
        ("output_writable", check_output_writable),
    ]

    results = [_check(name, fn) for name, fn in checks]

    # Degrade gracefully: latex/dvisvgm/font are warnings, not hard failures
    soft_fail_keys = {"latex", "dvisvgm", "font_noto_sans"}
    hard_ok = all(
        r["status"] == "ok"
        for r in results
        if r["name"] not in soft_fail_keys
    )

    return hard_ok, results
