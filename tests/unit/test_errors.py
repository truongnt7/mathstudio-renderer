"""Unit tests for the error model."""

from __future__ import annotations

from mathstudio_renderer.errors import ErrorCode, RenderError


class TestErrorCodes:
    def test_all_codes_defined(self):
        expected = {
            "RENDER_REQUEST_INVALID",
            "RENDER_TEMPLATE_UNKNOWN",
            "RENDER_TEMPLATE_VERSION_UNSUPPORTED",
            "RENDER_OUTPUT_FORMAT_UNSUPPORTED",
            "RENDER_ASPECT_RATIO_UNSUPPORTED",
            "RENDER_TIMEOUT",
            "RENDER_PROCESS_FAILED",
            "RENDER_ARTIFACT_MISSING",
            "RENDER_ARTIFACT_INVALID",
            "RENDER_LATEX_FAILED",
            "RENDER_FONT_MISSING",
            "RENDER_CANCELLED",
            "RENDER_INTERNAL_ERROR",
        }
        actual = {str(c) for c in ErrorCode}
        assert expected == actual


class TestRenderError:
    def test_constructs_with_code_and_message(self):
        err = RenderError(ErrorCode.RENDER_TIMEOUT, "timed out")
        assert err.code == ErrorCode.RENDER_TIMEOUT
        assert err.message == "timed out"

    def test_is_exception(self):
        err = RenderError(ErrorCode.RENDER_INTERNAL_ERROR, "boom")
        assert isinstance(err, Exception)

    def test_safe_dict_contains_code_and_message(self):
        err = RenderError(ErrorCode.RENDER_TIMEOUT, "timed out after 120s")
        d = err.safe_dict()
        assert d["code"] == "RENDER_TIMEOUT"
        assert d["message"] == "timed out after 120s"

    def test_safe_dict_does_not_contain_diagnostics(self):
        err = RenderError(
            ErrorCode.RENDER_INTERNAL_ERROR,
            "internal",
            diagnostics={"secret_key": "abc123", "host_path": "/root"},
        )
        d = err.safe_dict()
        assert "diagnostics" not in d
        assert "secret_key" not in d

    def test_diagnostics_stored_internally(self):
        diag = {"returncode": 1, "stderr": "error output"}
        err = RenderError(ErrorCode.RENDER_PROCESS_FAILED, "failed", diagnostics=diag)
        assert err.diagnostics == diag

    def test_empty_diagnostics_default(self):
        err = RenderError(ErrorCode.RENDER_ARTIFACT_MISSING, "missing")
        assert err.diagnostics == {}
