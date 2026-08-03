"""Renderer runtime — orchestrates the full render pipeline."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .artifacts import ArtifactPipeline
from .config import config
from .errors import ErrorCode, RenderError
from .events import EventEmitter
from .registry import REGISTRY, TemplateRegistryEntry
from .schemas import ArtifactInfo, RenderPhase, RenderRequest, RenderStatus
from .subprocess_runner import RenderSubprocessRunner
from .workspace import WorkspaceManager

logger = logging.getLogger(__name__)


@dataclass
class RenderResult:
    request_id: str
    status: RenderStatus
    output_dir: Path
    artifacts: dict[str, ArtifactInfo] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    error: RenderError | None = None
    phase: RenderPhase = RenderPhase.COMPLETED


class Renderer:
    """Top-level render orchestrator."""

    def __init__(
        self,
        workspace_manager: WorkspaceManager | None = None,
        subprocess_runner: RenderSubprocessRunner | None = None,
        artifact_pipeline: ArtifactPipeline | None = None,
    ) -> None:
        config.ensure_dirs()
        ws = workspace_manager or WorkspaceManager(config.workspace_dir, config.output_dir)
        self._ws = ws
        self._runner = subprocess_runner or RenderSubprocessRunner(config.default_timeout)
        self._artifacts = artifact_pipeline or ArtifactPipeline(ws)

    def render(self, request: RenderRequest) -> RenderResult:
        started_at = datetime.now(UTC)
        started_ns = time.monotonic_ns()
        rid = request.request_id
        current_phase = RenderPhase.RECEIVED

        logger.info(
            "Render started",
            extra={"request_id": rid, "template": request.template_code, "phase": current_phase},
        )

        output_dir = self._ws.create_output_dir(rid)
        workspace_dir = self._ws.create_workspace(rid)
        media_dir = workspace_dir / "manim_media"

        emitter = EventEmitter(output_dir, rid, started_ns)
        emitter.received()

        try:
            # ---- Phase: validating ----
            current_phase = RenderPhase.VALIDATING
            emitter.validating()
            entry = self._resolve_entry(request)

            # ---- Phase: preparing workspace ----
            current_phase = RenderPhase.PREPARING_WORKSPACE
            emitter.preparing_workspace()
            media_dir.mkdir(parents=True, exist_ok=True)
            scene_file = entry.resolve_scene_file()

            # ---- Phase: building scene ----
            current_phase = RenderPhase.BUILDING_SCENE
            emitter.building_scene()

            # ---- Phase: rendering ----
            current_phase = RenderPhase.RENDERING
            emitter.rendering(25)
            logger.info(
                "Running Manim",
                extra={
                    "request_id": rid,
                    "scene_class": entry.scene_class,
                    "quality": request.quality,
                    "phase": current_phase,
                },
            )
            subprocess_result = self._runner.run_manim(
                scene_file=scene_file,
                scene_class=entry.scene_class,
                quality=request.quality,
                media_dir=media_dir,
            )

            # ---- Phase: validating artifacts ----
            current_phase = RenderPhase.VALIDATING_ARTIFACTS
            emitter.validating_artifacts()
            artifacts = self._artifacts.collect(
                entry=entry,
                quality=request.quality,
                media_dir=media_dir,
                output_dir=output_dir,
                formats={fmt for fmt in request.output.formats},
            )

            # ---- Phase: writing metadata ----
            current_phase = RenderPhase.WRITING_METADATA
            emitter.writing_metadata()
            completed_at = datetime.now(UTC)
            elapsed_ms = (completed_at - started_at).total_seconds() * 1000

            metadata = self._artifacts.build_metadata(
                request=request,
                entry=entry,
                artifacts=artifacts,
                started_at=started_at,
                completed_at=completed_at,
                elapsed_ms=elapsed_ms,
            )
            self._artifacts.write_metadata(output_dir, metadata)
            self._artifacts.write_diagnostics(
                output_dir,
                {
                    "returncode": subprocess_result.returncode,
                    "stderr_tail": subprocess_result.stderr[-2000:],
                    "elapsed_ms": round(elapsed_ms, 1),
                },
            )

            # Write safe render log
            log_path = output_dir / "safe-render.log"
            log_path.write_text(
                f"request_id: {rid}\n"
                f"template: {request.template_code}\n"
                f"quality: {request.quality}\n"
                f"elapsed_ms: {round(elapsed_ms, 1)}\n"
                f"status: completed\n"
            )

            current_phase = RenderPhase.COMPLETED
            emitter.completed(elapsed_ms)
            logger.info(
                "Render completed",
                extra={"request_id": rid, "elapsed_ms": round(elapsed_ms, 1)},
            )

            return RenderResult(
                request_id=rid,
                status=RenderStatus.COMPLETED,
                output_dir=output_dir,
                artifacts=artifacts,
                metadata=metadata,
                elapsed_ms=elapsed_ms,
                phase=current_phase,
            )

        except RenderError as exc:
            emitter.failed(str(exc.code), exc.message)
            raise
        except Exception as exc:
            logger.exception("Unexpected error during render", extra={"request_id": rid})
            render_err = RenderError(
                code=ErrorCode.RENDER_INTERNAL_ERROR,
                message="Internal render error",
                diagnostics={"exc_type": type(exc).__name__, "exc": str(exc)},
            )
            emitter.failed(str(render_err.code), render_err.message)
            raise render_err from exc
        finally:
            try:
                self._ws.cleanup_workspace(rid)
            except Exception:  # noqa: BLE001
                logger.debug("Workspace cleanup failed for %s", rid)

    def _resolve_entry(self, request: RenderRequest) -> TemplateRegistryEntry:
        entry = REGISTRY.get(request.template_code)
        if entry is None:
            raise RenderError(
                code=ErrorCode.RENDER_TEMPLATE_UNKNOWN,
                message=f"Template not found: {request.template_code}",
            )
        if request.template_version not in entry.supported_versions:
            raise RenderError(
                code=ErrorCode.RENDER_TEMPLATE_VERSION_UNSUPPORTED,
                message=(
                    f"Template '{request.template_code}' does not support "
                    f"version '{request.template_version}'. "
                    f"Supported: {sorted(entry.supported_versions)}"
                ),
            )
        if request.aspect_ratio not in entry.supported_aspect_ratios:
            raise RenderError(
                code=ErrorCode.RENDER_ASPECT_RATIO_UNSUPPORTED,
                message=(
                    f"Template '{request.template_code}' does not support "
                    f"aspect ratio '{request.aspect_ratio}'."
                ),
            )
        for fmt in request.output.formats:
            if fmt not in entry.supported_formats:
                raise RenderError(
                    code=ErrorCode.RENDER_OUTPUT_FORMAT_UNSUPPORTED,
                    message=(
                        f"Template '{request.template_code}' does not support format '{fmt}'."
                    ),
                )
        return entry
