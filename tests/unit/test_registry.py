"""Unit tests for the template registry."""

from __future__ import annotations

import pytest

from mathstudio_renderer.registry import REGISTRY, TemplateRegistryEntry

EXPECTED_CODES = {"HELLO_V1", "MATHTEX_SMOKE_V1", "VIETNAMESE_TEXT_V1", "GEOMETRY_SMOKE_V1"}


class TestRegistryContents:
    def test_exactly_four_templates(self):
        assert len(REGISTRY.list_all()) == 4

    def test_expected_codes_present(self):
        assert set(REGISTRY.codes()) == EXPECTED_CODES

    def test_hello_v1_present(self):
        assert REGISTRY.get("HELLO_V1") is not None

    def test_mathtex_present(self):
        assert REGISTRY.get("MATHTEX_SMOKE_V1") is not None

    def test_vietnamese_present(self):
        assert REGISTRY.get("VIETNAMESE_TEXT_V1") is not None

    def test_geometry_present(self):
        assert REGISTRY.get("GEOMETRY_SMOKE_V1") is not None

    def test_unknown_template_returns_none(self):
        assert REGISTRY.get("NONEXISTENT_TEMPLATE") is None

    def test_all_templates_have_versions(self):
        for entry in REGISTRY.list_all():
            assert entry.version
            assert entry.supported_versions

    def test_all_templates_support_mp4(self):
        for entry in REGISTRY.list_all():
            assert "mp4" in entry.supported_formats

    def test_all_templates_support_preview(self):
        for entry in REGISTRY.list_all():
            assert "preview" in entry.supported_qualities

    def test_all_templates_support_16_9(self):
        for entry in REGISTRY.list_all():
            assert "16:9" in entry.supported_aspect_ratios


class TestRegistryEntryFields:
    def test_hello_scene_module(self):
        entry = REGISTRY.get("HELLO_V1")
        assert entry is not None
        assert "hello_scene" in entry.scene_module

    def test_hello_scene_class(self):
        entry = REGISTRY.get("HELLO_V1")
        assert entry is not None
        assert entry.scene_class == "HelloScene"

    def test_mathtex_scene_class(self):
        entry = REGISTRY.get("MATHTEX_SMOKE_V1")
        assert entry is not None
        assert entry.scene_class == "MathTexSmokeScene"

    def test_vietnamese_scene_class(self):
        entry = REGISTRY.get("VIETNAMESE_TEXT_V1")
        assert entry is not None
        assert entry.scene_class == "VietnameseTextScene"

    def test_geometry_scene_class(self):
        entry = REGISTRY.get("GEOMETRY_SMOKE_V1")
        assert entry is not None
        assert entry.scene_class == "GeometrySmokeScene"


class TestRegistrySceneFile:
    def test_hello_scene_file_resolves(self):
        entry = REGISTRY.get("HELLO_V1")
        assert entry is not None
        path = entry.resolve_scene_file()
        assert path.exists()
        assert path.suffix == ".py"
        assert "hello_scene" in path.name

    def test_scene_file_is_inside_package(self):
        for entry in REGISTRY.list_all():
            path = entry.resolve_scene_file()
            assert path.exists(), f"Scene file missing: {path}"
            assert "mathstudio_renderer" in str(path)


class TestRegistryProtection:
    """Registry should be sealed — no further registration."""

    def test_registry_sealed(self):
        with pytest.raises(RuntimeError, match="sealed"):
            REGISTRY.register(
                TemplateRegistryEntry(
                    code="EVIL_TEMPLATE",
                    version="1.0.0",
                    description="evil",
                    scene_module="mathstudio_renderer.scenes.hello_scene",
                    scene_class="HelloScene",
                    supported_versions=frozenset({"1.0.0"}),
                    supported_aspect_ratios=frozenset({"16:9"}),
                    supported_formats=frozenset({"mp4"}),
                    supported_qualities=frozenset({"preview"}),
                    capabilities=frozenset(),
                )
            )

    def test_to_dict_contains_all(self):
        result = REGISTRY.to_dict()
        codes = {e["code"] for e in result}
        assert codes == EXPECTED_CODES
