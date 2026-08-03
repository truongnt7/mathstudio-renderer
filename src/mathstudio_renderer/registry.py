"""Explicit template registry — the single source of trusted scene mappings.

Design invariants
-----------------
* Exactly the four approved smoke templates are registered.
* No template data is derived from request input.
* Unknown template codes raise RENDER_TEMPLATE_UNKNOWN at runtime.
* Duplicate registry codes raise RuntimeError at import time (startup guard).
* Scene module paths are resolved internally via importlib — callers never
  supply import paths.
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from .schemas import AspectRatio, OutputFormat, RenderQuality


@dataclass(frozen=True)
class TemplateRegistryEntry:
    """Immutable description of a registered render template."""

    code: str
    version: str
    description: str
    scene_module: str  # fully-qualified module name inside this package
    scene_class: str  # class name within that module
    supported_versions: frozenset[str]
    supported_aspect_ratios: frozenset[str]
    supported_formats: frozenset[str]
    supported_qualities: frozenset[str]
    capabilities: frozenset[str]

    def resolve_scene_file(self) -> Path:
        """Return the absolute filesystem path of the scene module.

        The path is derived from the registry's trusted module name, not
        from any user-supplied value.
        """
        mod = importlib.import_module(self.scene_module)
        return Path(inspect.getfile(mod))


class TemplateRegistry:
    """In-process template registry with startup duplicate detection."""

    _entries: ClassVar[dict[str, TemplateRegistryEntry]] = {}
    _sealed: ClassVar[bool] = False

    @classmethod
    def register(cls, entry: TemplateRegistryEntry) -> None:
        if cls._sealed:
            raise RuntimeError("Registry is sealed — no further registration allowed.")
        if entry.code in cls._entries:
            raise RuntimeError(
                f"Duplicate template code in registry: {entry.code!r}. "
                "Each template_code must be unique."
            )
        cls._entries[entry.code] = entry

    @classmethod
    def seal(cls) -> None:
        """Prevent further registrations (called after all templates are loaded)."""
        cls._sealed = True

    @classmethod
    def get(cls, code: str) -> TemplateRegistryEntry | None:
        return cls._entries.get(code)

    @classmethod
    def list_all(cls) -> list[TemplateRegistryEntry]:
        return list(cls._entries.values())

    @classmethod
    def codes(cls) -> list[str]:
        return list(cls._entries.keys())

    @classmethod
    def to_dict(cls) -> list[dict[str, Any]]:
        result = []
        for e in cls._entries.values():
            result.append(
                {
                    "code": e.code,
                    "version": e.version,
                    "description": e.description,
                    "scene_class": e.scene_class,
                    "supported_versions": sorted(e.supported_versions),
                    "supported_aspect_ratios": sorted(e.supported_aspect_ratios),
                    "supported_formats": sorted(e.supported_formats),
                    "supported_qualities": sorted(e.supported_qualities),
                    "capabilities": sorted(e.capabilities),
                }
            )
        return result


# ---------------------------------------------------------------------------
# Register the four approved smoke templates
# ---------------------------------------------------------------------------

TemplateRegistry.register(
    TemplateRegistryEntry(
        code="HELLO_V1",
        version="1.0.0",
        description="Hello Math Studio — basic text animation smoke test.",
        scene_module="mathstudio_renderer.scenes.hello_scene",
        scene_class="HelloScene",
        supported_versions=frozenset({"1.0.0"}),
        supported_aspect_ratios=frozenset(
            {
                AspectRatio.RATIO_16_9,
                AspectRatio.RATIO_9_16,
                AspectRatio.RATIO_1_1,
            }
        ),
        supported_formats=frozenset({OutputFormat.MP4, OutputFormat.PNG}),
        supported_qualities=frozenset({RenderQuality.PREVIEW, RenderQuality.FINAL}),
        capabilities=frozenset({"text", "animation"}),
    )
)

TemplateRegistry.register(
    TemplateRegistryEntry(
        code="MATHTEX_SMOKE_V1",
        version="1.0.0",
        description="MathTex smoke — LaTeX math expression rendering via dvisvgm.",
        scene_module="mathstudio_renderer.scenes.mathtex_scene",
        scene_class="MathTexSmokeScene",
        supported_versions=frozenset({"1.0.0"}),
        supported_aspect_ratios=frozenset(
            {
                AspectRatio.RATIO_16_9,
                AspectRatio.RATIO_9_16,
                AspectRatio.RATIO_1_1,
            }
        ),
        supported_formats=frozenset({OutputFormat.MP4, OutputFormat.PNG}),
        supported_qualities=frozenset({RenderQuality.PREVIEW, RenderQuality.FINAL}),
        capabilities=frozenset({"mathtex", "latex", "animation"}),
    )
)

TemplateRegistry.register(
    TemplateRegistryEntry(
        code="VIETNAMESE_TEXT_V1",
        version="1.0.0",
        description="Vietnamese text smoke — Unicode / Pango font rendering.",
        scene_module="mathstudio_renderer.scenes.vietnamese_text_scene",
        scene_class="VietnameseTextScene",
        supported_versions=frozenset({"1.0.0"}),
        supported_aspect_ratios=frozenset(
            {
                AspectRatio.RATIO_16_9,
                AspectRatio.RATIO_9_16,
                AspectRatio.RATIO_1_1,
            }
        ),
        supported_formats=frozenset({OutputFormat.MP4, OutputFormat.PNG}),
        supported_qualities=frozenset({RenderQuality.PREVIEW, RenderQuality.FINAL}),
        capabilities=frozenset({"text", "unicode", "vietnamese", "animation"}),
    )
)

TemplateRegistry.register(
    TemplateRegistryEntry(
        code="GEOMETRY_SMOKE_V1",
        version="1.0.0",
        description="Geometry smoke — shapes, labels, deterministic transformation.",
        scene_module="mathstudio_renderer.scenes.geometry_smoke_scene",
        scene_class="GeometrySmokeScene",
        supported_versions=frozenset({"1.0.0"}),
        supported_aspect_ratios=frozenset(
            {
                AspectRatio.RATIO_16_9,
                AspectRatio.RATIO_9_16,
                AspectRatio.RATIO_1_1,
            }
        ),
        supported_formats=frozenset({OutputFormat.MP4, OutputFormat.PNG}),
        supported_qualities=frozenset({RenderQuality.PREVIEW, RenderQuality.FINAL}),
        capabilities=frozenset({"geometry", "shapes", "animation"}),
    )
)

TemplateRegistry.seal()

# Convenience alias
REGISTRY = TemplateRegistry
