"""Closed request/response schemas for the Manim renderer.

Design invariants
-----------------
* ``model_config = ConfigDict(extra="forbid")`` on every model — unknown
  fields are rejected at validation time, not silently ignored.
* ``request_id`` is validated with a strict safe-identifier regex that
  rejects path-separator characters, encoded traversal sequences, shell
  metacharacters, and excessively long strings.
* The request schema does NOT contain Python source, module paths, scene
  class names, shell arguments, host paths, or environment overrides.
  All of those are resolved internally from the registry.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Safe request-ID pattern
# ---------------------------------------------------------------------------
_REQUEST_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")

# Characters that must never appear in a request ID (belt-and-suspenders)
_FORBIDDEN_ID_CHARS = set("/\\.:@#%&+= \t\n\r\x00")


def _validate_request_id(v: str) -> str:
    if not v:
        raise ValueError("request_id must not be empty")
    if len(v) > 64:
        raise ValueError("request_id must not exceed 64 characters")
    if any(c in _FORBIDDEN_ID_CHARS for c in v):
        raise ValueError("request_id contains forbidden characters")
    if ".." in v:
        raise ValueError("request_id must not contain path traversal sequences")
    if not _REQUEST_ID_RE.match(v):
        raise ValueError("request_id must match ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
    return v


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class RequestVersion(StrEnum):
    V1 = "1.0.0"


class RenderQuality(StrEnum):
    PREVIEW = "preview"
    FINAL = "final"


class AspectRatio(StrEnum):
    RATIO_16_9 = "16:9"
    RATIO_9_16 = "9:16"
    RATIO_1_1 = "1:1"


class OutputFormat(StrEnum):
    MP4 = "mp4"
    PNG = "png"


class RenderPhase(StrEnum):
    RECEIVED = "received"
    VALIDATING = "validating"
    PREPARING_WORKSPACE = "preparing_workspace"
    BUILDING_SCENE = "building_scene"
    RENDERING = "rendering"
    VALIDATING_ARTIFACTS = "validating_artifacts"
    WRITING_METADATA = "writing_metadata"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RenderStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class OutputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formats: list[OutputFormat] = Field(
        default=[OutputFormat.MP4],
        min_length=1,
        description="Output formats to produce.",
    )


# ---------------------------------------------------------------------------
# Main request model
# ---------------------------------------------------------------------------

SafeRequestId = Annotated[
    str,
    Field(
        min_length=1,
        max_length=64,
        description="Safe alphanumeric request identifier (no path characters).",
    ),
]


class RenderRequest(BaseModel):
    """Closed render request — unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_version: Literal["1.0.0"] = Field(
        description="Schema version. Must be '1.0.0'.",
    )
    request_id: SafeRequestId = Field(
        description="Unique request identifier.",
    )
    template_code: str = Field(
        min_length=1,
        max_length=64,
        description="Registered template code.",
    )
    template_version: str = Field(
        min_length=1,
        max_length=32,
        description="Template version string.",
    )
    quality: RenderQuality = Field(
        description="Render quality preset.",
    )
    aspect_ratio: AspectRatio = Field(
        description="Output aspect ratio.",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Template-specific parameters (schema validated by registry).",
    )
    output: OutputSpec = Field(
        default_factory=OutputSpec,
        description="Output format specification.",
    )

    @field_validator("request_id", mode="before")
    @classmethod
    def validate_request_id(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("request_id must be a string")
        return _validate_request_id(v)

    @field_validator("template_code", mode="before")
    @classmethod
    def validate_template_code(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("template_code must be a string")
        # Template codes are uppercase alphanumeric + underscores
        if not re.match(r"^[A-Z][A-Z0-9_]{0,63}$", v):
            raise ValueError("template_code must match ^[A-Z][A-Z0-9_]{0,63}$ (e.g. HELLO_V1)")
        return v


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ArtifactInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    mime_type: str
    size_bytes: int
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    duration_s: float | None = None
    codec: str | None = None


class RenderMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    template_code: str
    template_version: str
    renderer_version: str
    python_version: str
    manim_version: str
    ffmpeg_version: str
    architecture: str
    quality: str
    aspect_ratio: str
    status: str
    started_at: str
    completed_at: str
    elapsed_ms: float
    artifacts: dict[str, ArtifactInfo]
