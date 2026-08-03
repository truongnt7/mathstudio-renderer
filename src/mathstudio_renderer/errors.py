"""Renderer error model — M2-B3.1 local error catalog.

These codes are local to the renderer.  They do NOT modify the B0/B1 error
catalog.  A future B3.2 integration layer will map these codes to B-plane
status values.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    RENDER_REQUEST_INVALID = "RENDER_REQUEST_INVALID"
    RENDER_TEMPLATE_UNKNOWN = "RENDER_TEMPLATE_UNKNOWN"
    RENDER_TEMPLATE_VERSION_UNSUPPORTED = "RENDER_TEMPLATE_VERSION_UNSUPPORTED"
    RENDER_OUTPUT_FORMAT_UNSUPPORTED = "RENDER_OUTPUT_FORMAT_UNSUPPORTED"
    RENDER_ASPECT_RATIO_UNSUPPORTED = "RENDER_ASPECT_RATIO_UNSUPPORTED"
    RENDER_TIMEOUT = "RENDER_TIMEOUT"
    RENDER_PROCESS_FAILED = "RENDER_PROCESS_FAILED"
    RENDER_ARTIFACT_MISSING = "RENDER_ARTIFACT_MISSING"
    RENDER_ARTIFACT_INVALID = "RENDER_ARTIFACT_INVALID"
    RENDER_LATEX_FAILED = "RENDER_LATEX_FAILED"
    RENDER_FONT_MISSING = "RENDER_FONT_MISSING"
    RENDER_CANCELLED = "RENDER_CANCELLED"
    RENDER_INTERNAL_ERROR = "RENDER_INTERNAL_ERROR"


# Future B3.2 mapping reference (not implemented here):
#
#   RENDER_REQUEST_INVALID       -> job status: failed, b1_code: JOB_INPUT_INVALID
#   RENDER_TEMPLATE_UNKNOWN      -> job status: failed, b1_code: JOB_INPUT_INVALID
#   RENDER_TIMEOUT               -> job status: failed, b1_code: JOB_RENDER_TIMEOUT
#   RENDER_PROCESS_FAILED        -> job status: failed, b1_code: JOB_RENDER_ERROR
#   RENDER_ARTIFACT_MISSING      -> job status: failed, b1_code: JOB_RENDER_ERROR
#   RENDER_CANCELLED             -> job status: cancelled, b1_code: JOB_CANCELLED
#   RENDER_INTERNAL_ERROR        -> job status: failed, b1_code: JOB_INTERNAL_ERROR


class RenderError(Exception):
    """Renderer-level error with structured code and safe message."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        diagnostics: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        # Diagnostics are kept INTERNAL — never exposed to untrusted callers.
        self.diagnostics: dict[str, Any] = diagnostics or {}

    def safe_dict(self) -> dict[str, str]:
        """Return only the fields safe to surface in responses/logs."""
        return {"code": str(self.code), "message": self.message}

    def __repr__(self) -> str:
        return f"RenderError(code={self.code!r}, message={self.message!r})"
