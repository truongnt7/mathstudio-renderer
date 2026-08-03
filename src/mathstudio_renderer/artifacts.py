"""Artifact collection, validation and metadata generation.

After Manim finishes rendering, this module:
1. Locates the rendered files inside Manim's ``media/`` tree.
2. Copies them to the request output directory.
3. Generates a poster PNG (first frame) if requested.
4. Validates each artifact (existence, regular file, MIME, dimensions, etc.).
5. Writes ``metadata.json`` and ``diagnostics.json``.
"""

from __future__ import annotations

import json
import logging
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import orjson

from . import __version__
from .errors import ErrorCode, RenderError
from .registry import TemplateRegistryEntry
from .schemas import ArtifactInfo, RenderRequest
from .subprocess_runner import quality_subdir
from .workspace import WorkspaceManager

logger = logging.getLogger(__name__)

# Expected MIME types for each format
_MIME: dict[str, str] = {
    "mp4": "video/mp4",
    "png": "image/png",
}

# Minimum acceptable file sizes
_MIN_BYTES: dict[str, int] = {
    "mp4": 1024,  # at least 1 KiB
    "png": 256,
}


def _run_ffprobe(path: Path) -> dict[str, Any]:
    """Run ffprobe on a file and return parsed JSON."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(  # noqa: S603,S607
            cmd,
            shell=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RenderError(
                code=ErrorCode.RENDER_ARTIFACT_INVALID,
                message="ffprobe failed on MP4 artifact",
                diagnostics={"stderr": result.stderr},
            )
        parsed: dict[str, Any] = json.loads(result.stdout)
        return parsed
    except FileNotFoundError as exc:
        raise RenderError(
            code=ErrorCode.RENDER_ARTIFACT_INVALID,
            message="ffprobe not found — cannot validate MP4",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RenderError(
            code=ErrorCode.RENDER_ARTIFACT_INVALID,
            message="ffprobe timed out",
        ) from exc


def _make_poster(mp4_path: Path, out_path: Path) -> None:
    """Extract the first frame of an MP4 as a PNG poster."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(mp4_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(out_path),
    ]
    result = subprocess.run(  # noqa: S603,S607
        cmd,
        shell=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        logger.warning("ffmpeg poster generation failed: %s", result.stderr)


def _get_manim_output_path(
    workspace_dir: Path,
    scene_file: Path,
    scene_class: str,
    quality: str,
) -> Path:
    """Compute the expected Manim MP4 output path.

    Manim structures output as:
      {media_dir}/videos/{module_name}/{quality_subdir}/{SceneClass}.mp4
    """
    module_name = scene_file.stem  # filename without .py
    subdir = quality_subdir(quality)
    return workspace_dir / "videos" / module_name / subdir / f"{scene_class}.mp4"


def _validate_mp4(path: Path) -> dict[str, Any]:
    """Validate an MP4 file via ffprobe; return stream info."""
    probe = _run_ffprobe(path)
    streams = probe.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    if not video_streams:
        raise RenderError(
            code=ErrorCode.RENDER_ARTIFACT_INVALID,
            message="MP4 contains no video stream",
        )
    vs = video_streams[0]
    return {
        "codec": vs.get("codec_name", ""),
        "width": int(vs.get("width", 0)),
        "height": int(vs.get("height", 0)),
        "fps": _parse_fps(vs.get("r_frame_rate", "0/1")),
        "duration_s": float(vs.get("duration", 0)),
    }


def _validate_png(path: Path) -> dict[str, Any]:
    """Validate a PNG file and return dimensions."""
    try:
        from PIL import Image

        with Image.open(path) as img:
            if img.format != "PNG":
                raise RenderError(
                    code=ErrorCode.RENDER_ARTIFACT_INVALID,
                    message=f"Expected PNG, got {img.format}",
                )
            return {"width": img.width, "height": img.height}
    except ImportError:
        logger.warning("Pillow not available — skipping PNG dimension check")
        return {}


def _parse_fps(fps_str: str) -> float:
    try:
        num, den = fps_str.split("/")
        return round(float(num) / float(den), 3) if float(den) != 0 else 0.0
    except (ValueError, ZeroDivisionError):
        return 0.0


def _get_ffmpeg_version() -> str:
    try:
        r = subprocess.run(  # noqa: S603,S607
            ["ffmpeg", "-version"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        first_line = r.stdout.splitlines()[0] if r.stdout else ""
        if "version" in first_line:
            return first_line.split("version ")[-1].split(" ")[0]
        return "unknown"
    except Exception:
        return "unknown"


def _get_manim_version() -> str:
    try:
        import manim  # type: ignore[import-untyped]

        return str(getattr(manim, "__version__", "unknown"))
    except ImportError:
        return "unknown"


class ArtifactPipeline:
    """Collects, validates, and records render artifacts."""

    def __init__(self, workspace_manager: WorkspaceManager) -> None:
        self._ws = workspace_manager

    def collect(
        self,
        entry: TemplateRegistryEntry,
        quality: str,
        media_dir: Path,
        output_dir: Path,
        formats: set[str],
    ) -> dict[str, ArtifactInfo]:
        """Locate Manim output, copy to output_dir, validate, return info."""
        scene_file = entry.resolve_scene_file()
        mp4_src = _get_manim_output_path(media_dir, scene_file, entry.scene_class, quality)

        if not mp4_src.exists():
            raise RenderError(
                code=ErrorCode.RENDER_ARTIFACT_MISSING,
                message=f"Expected MP4 not found after render: {mp4_src.name}",
                diagnostics={"expected_path": str(mp4_src)},
            )

        artifacts: dict[str, ArtifactInfo] = {}

        # MP4
        if "mp4" in formats:
            mp4_dst = output_dir / "render.mp4"
            shutil.copy2(mp4_src, mp4_dst)
            self._ws.validate_artifact_path(mp4_dst, output_dir)

            mp4_info = _validate_mp4(mp4_dst)
            size = mp4_dst.stat().st_size
            if size < _MIN_BYTES["mp4"]:
                raise RenderError(
                    code=ErrorCode.RENDER_ARTIFACT_INVALID,
                    message=f"MP4 is suspiciously small: {size} bytes",
                )
            artifacts["render.mp4"] = ArtifactInfo(
                path="render.mp4",
                mime_type=_MIME["mp4"],
                size_bytes=size,
                codec=mp4_info.get("codec"),
                width=mp4_info.get("width"),
                height=mp4_info.get("height"),
                fps=mp4_info.get("fps"),
                duration_s=mp4_info.get("duration_s"),
            )

            # Always generate poster from MP4
            poster_dst = output_dir / "poster.png"
            _make_poster(mp4_dst, poster_dst)
            if poster_dst.exists() and poster_dst.stat().st_size > _MIN_BYTES["png"]:
                self._ws.validate_artifact_path(poster_dst, output_dir)
                png_info = _validate_png(poster_dst)
                artifacts["poster.png"] = ArtifactInfo(
                    path="poster.png",
                    mime_type=_MIME["png"],
                    size_bytes=poster_dst.stat().st_size,
                    width=png_info.get("width"),
                    height=png_info.get("height"),
                )

        # Standalone PNG (first frame only)
        if "png" in formats and "mp4" not in formats:
            png_dst = output_dir / "render.png"
            if mp4_src.exists():
                _make_poster(mp4_src, png_dst)
            if png_dst.exists() and png_dst.stat().st_size > _MIN_BYTES["png"]:
                self._ws.validate_artifact_path(png_dst, output_dir)
                png_info = _validate_png(png_dst)
                artifacts["render.png"] = ArtifactInfo(
                    path="render.png",
                    mime_type=_MIME["png"],
                    size_bytes=png_dst.stat().st_size,
                    width=png_info.get("width"),
                    height=png_info.get("height"),
                )

        if not artifacts:
            raise RenderError(
                code=ErrorCode.RENDER_ARTIFACT_MISSING,
                message="No valid artifacts were produced",
            )

        return artifacts

    def build_metadata(
        self,
        request: RenderRequest,
        entry: TemplateRegistryEntry,
        artifacts: dict[str, ArtifactInfo],
        started_at: datetime,
        completed_at: datetime,
        elapsed_ms: float,
    ) -> dict[str, Any]:
        return {
            "request_id": request.request_id,
            "template_code": request.template_code,
            "template_version": request.template_version,
            "renderer_version": __version__,
            "python_version": sys.version.split(" ")[0],
            "manim_version": _get_manim_version(),
            "ffmpeg_version": _get_ffmpeg_version(),
            "architecture": platform.machine(),
            "quality": request.quality,
            "aspect_ratio": request.aspect_ratio,
            "status": "completed",
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "elapsed_ms": round(elapsed_ms, 1),
            "artifacts": {name: info.model_dump() for name, info in artifacts.items()},
        }

    def write_metadata(self, output_dir: Path, metadata: dict[str, Any]) -> None:
        meta_path = output_dir / "metadata.json"
        meta_path.write_bytes(orjson.dumps(metadata, option=orjson.OPT_INDENT_2))
        logger.debug("Wrote metadata to %s", meta_path)

    def write_diagnostics(self, output_dir: Path, diag: dict[str, Any]) -> None:
        """Write internal diagnostics — safe subset only (no secrets, no host paths)."""
        # Strip any keys that might contain sensitive data
        safe_diag = {
            k: v for k, v in diag.items() if k not in {"env", "host_path", "secret", "token", "key"}
        }
        diag_path = output_dir / "diagnostics.json"
        diag_path.write_bytes(orjson.dumps(safe_diag, option=orjson.OPT_INDENT_2))
