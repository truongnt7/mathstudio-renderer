"""Unit tests for the closed request schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mathstudio_renderer.schemas import (
    OutputFormat,
    RenderQuality,
    RenderRequest,
)

VALID_BASE = {
    "request_version": "1.0.0",
    "request_id": "test-request-001",
    "template_code": "HELLO_V1",
    "template_version": "1.0.0",
    "quality": "preview",
    "aspect_ratio": "16:9",
    "parameters": {},
    "output": {"formats": ["mp4"]},
}


def make_request(**overrides: object) -> dict:
    return {**VALID_BASE, **overrides}


class TestValidRequest:
    def test_valid_hello(self):
        req = RenderRequest.model_validate(VALID_BASE)
        assert req.request_id == "test-request-001"
        assert req.template_code == "HELLO_V1"
        assert req.quality == RenderQuality.PREVIEW

    def test_all_qualities(self):
        for q in ("preview", "final"):
            req = RenderRequest.model_validate(make_request(quality=q))
            assert req.quality == q

    def test_all_aspect_ratios(self):
        for ar in ("16:9", "9:16", "1:1"):
            req = RenderRequest.model_validate(make_request(aspect_ratio=ar))
            assert req.aspect_ratio == ar

    def test_mp4_format(self):
        req = RenderRequest.model_validate(make_request(output={"formats": ["mp4"]}))
        assert OutputFormat.MP4 in req.output.formats

    def test_png_format(self):
        req = RenderRequest.model_validate(make_request(output={"formats": ["png"]}))
        assert OutputFormat.PNG in req.output.formats

    def test_multiple_formats(self):
        req = RenderRequest.model_validate(make_request(output={"formats": ["mp4", "png"]}))
        assert len(req.output.formats) == 2

    def test_empty_parameters_allowed(self):
        req = RenderRequest.model_validate(make_request(parameters={}))
        assert req.parameters == {}


class TestClosedSchema:
    """Unknown extra fields must be rejected (extra='forbid')."""

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            RenderRequest.model_validate(make_request(unknown_field="evil"))
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
            or "unknown_field" in str(exc_info.value)
        )

    def test_python_source_field_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(python_source="import os; os.system('evil')"))

    def test_module_path_field_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(
                make_request(module="mathstudio_renderer.scenes.hello_scene")
            )

    def test_scene_class_field_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(scene_class="HelloScene"))

    def test_shell_command_field_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(command="rm -rf /"))

    def test_output_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(
                make_request(
                    output={
                        "formats": ["mp4"],
                        "host_path": "/etc/passwd",
                    }
                )
            )


class TestRequestIdValidation:
    """Request ID must match ^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$ and reject traversal."""

    def test_valid_ids(self):
        for rid in ("abc", "abc-123", "abc_123", "A1B2C3", "x" * 64):
            req = RenderRequest.model_validate(make_request(request_id=rid))
            assert req.request_id == rid

    def test_dotdot_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(request_id="../etc/passwd"))

    def test_absolute_path_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(request_id="/etc/passwd"))

    def test_slash_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(request_id="hello/world"))

    def test_backslash_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(request_id="hello\\world"))

    def test_empty_string_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(request_id=""))

    def test_too_long_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(request_id="x" * 65))

    def test_space_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(request_id="hello world"))

    def test_shell_metachar_rejected(self):
        for bad in (";", "&", "|", "`", "$", "(", ")", "<", ">"):
            with pytest.raises(ValidationError):
                RenderRequest.model_validate(make_request(request_id=f"hello{bad}world"))

    def test_newline_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(request_id="hello\nworld"))

    def test_null_byte_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(request_id="hello\x00world"))

    def test_encoded_traversal_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(request_id="..%2Fetc%2Fpasswd"))

    def test_dot_prefix_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(request_id=".hidden"))


class TestTemplateCodeValidation:
    def test_valid_template_codes(self):
        for code in ("HELLO_V1", "MATHTEX_SMOKE_V1", "GEOMETRY_SMOKE_V1"):
            req = RenderRequest.model_validate(make_request(template_code=code))
            assert req.template_code == code

    def test_lowercase_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(template_code="hello_v1"))

    def test_empty_template_code_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(template_code=""))


class TestQualityValidation:
    def test_invalid_quality_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(quality="ultra"))

    def test_integer_quality_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(quality=1))


class TestAspectRatioValidation:
    def test_invalid_ratio_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(aspect_ratio="4:3"))

    def test_freeform_ratio_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(aspect_ratio="1920x1080"))


class TestRequestVersion:
    def test_wrong_version_rejected(self):
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(make_request(request_version="2.0.0"))

    def test_missing_version_rejected(self):
        data = {k: v for k, v in VALID_BASE.items() if k != "request_version"}
        with pytest.raises(ValidationError):
            RenderRequest.model_validate(data)
