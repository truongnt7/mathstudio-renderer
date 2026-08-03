"""Integration tests — render each fixture locally using real Manim.

These tests are marked ``integration`` and ``slow``.  They require:
- Manim and all its dependencies installed
- FFmpeg / ffprobe installed
- For MATHTEX: LaTeX + dvisvgm installed (marked ``latex``)
- For VIETNAMESE: Vietnamese-capable font installed
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from mathstudio_renderer.errors import ErrorCode, RenderError
from mathstudio_renderer.runtime import Renderer
from mathstudio_renderer.schemas import RenderRequest
from mathstudio_renderer.subprocess_runner import RenderSubprocessRunner
from mathstudio_renderer.workspace import WorkspaceManager

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


def _make_renderer(ws_root: Path, out_root: Path, timeout: float = 120.0) -> Renderer:
    ws = WorkspaceManager(ws_root, out_root)
    runner = RenderSubprocessRunner(timeout=timeout)
    return Renderer(workspace_manager=ws, subprocess_runner=runner)


def _load_request(fixture_name: str) -> RenderRequest:
    path = FIXTURES_DIR / fixture_name
    return RenderRequest.model_validate(json.loads(path.read_text()))


@pytest.fixture
def isolated_dirs(tmp_path):
    ws = tmp_path / "workspace"
    out = tmp_path / "output"
    ws.mkdir()
    out.mkdir()
    return ws, out


@pytest.mark.integration
@pytest.mark.slow
class TestHelloFixture:
    def test_hello_renders_mp4(self, isolated_dirs):
        ws, out = isolated_dirs
        renderer = _make_renderer(ws, out)
        request = _load_request("hello.json")

        result = renderer.render(request)

        assert result.status.value == "completed"
        mp4 = result.output_dir / "render.mp4"
        assert mp4.exists()
        assert mp4.stat().st_size > 1024

    def test_hello_produces_poster(self, isolated_dirs):
        ws, out = isolated_dirs
        renderer = _make_renderer(ws, out)
        request = _load_request("hello.json")
        result = renderer.render(request)
        poster = result.output_dir / "poster.png"
        assert poster.exists()

    def test_hello_produces_metadata(self, isolated_dirs):
        ws, out = isolated_dirs
        renderer = _make_renderer(ws, out)
        request = _load_request("hello.json")
        result = renderer.render(request)
        meta = result.output_dir / "metadata.json"
        assert meta.exists()
        data = json.loads(meta.read_text())
        assert data["status"] == "completed"
        assert data["template_code"] == "HELLO_V1"

    def test_hello_elapsed_ms_positive(self, isolated_dirs):
        ws, out = isolated_dirs
        renderer = _make_renderer(ws, out)
        request = _load_request("hello.json")
        result = renderer.render(request)
        assert result.elapsed_ms > 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.latex
class TestMathTexFixture:
    @pytest.fixture(autouse=True)
    def skip_without_latex(self):
        if not shutil.which("latex"):
            pytest.skip("LaTeX not installed — skipping MathTex integration test")
        if not shutil.which("dvisvgm"):
            pytest.skip("dvisvgm not installed — skipping MathTex integration test")

    def test_mathtex_renders(self, isolated_dirs):
        ws, out = isolated_dirs
        renderer = _make_renderer(ws, out)
        request = _load_request("mathtex.json")
        result = renderer.render(request)
        assert result.status.value == "completed"
        assert (result.output_dir / "render.mp4").exists()


@pytest.mark.integration
@pytest.mark.slow
class TestVietnameseFixture:
    def test_vietnamese_renders(self, isolated_dirs):
        ws, out = isolated_dirs
        renderer = _make_renderer(ws, out)
        request = _load_request("vietnamese_text.json")
        result = renderer.render(request)
        assert result.status.value == "completed"
        assert (result.output_dir / "render.mp4").exists()


@pytest.mark.integration
@pytest.mark.slow
class TestGeometryFixture:
    def test_geometry_renders(self, isolated_dirs):
        ws, out = isolated_dirs
        renderer = _make_renderer(ws, out)
        request = _load_request("geometry_smoke.json")
        result = renderer.render(request)
        assert result.status.value == "completed"
        assert (result.output_dir / "render.mp4").exists()


@pytest.mark.integration
@pytest.mark.slow
class TestTimeout:
    def test_very_short_timeout_raises(self, isolated_dirs):
        ws, out = isolated_dirs
        renderer = _make_renderer(ws, out, timeout=0.5)
        request = _load_request("hello.json")
        with pytest.raises(RenderError) as exc_info:
            renderer.render(request)
        assert exc_info.value.code == ErrorCode.RENDER_TIMEOUT


@pytest.mark.integration
class TestUnknownTemplate:
    def test_unknown_template_raises(self, isolated_dirs):
        ws, out = isolated_dirs
        renderer = _make_renderer(ws, out)
        bad_request = RenderRequest.model_validate(
            {
                "request_version": "1.0.0",
                "request_id": "unknown-tpl-001",
                "template_code": "UNKNOWN_TEMPLATE",
                "template_version": "1.0.0",
                "quality": "preview",
                "aspect_ratio": "16:9",
                "parameters": {},
                "output": {"formats": ["mp4"]},
            }
        )
        with pytest.raises(RenderError) as exc_info:
            renderer.render(bad_request)
        assert exc_info.value.code == ErrorCode.RENDER_TEMPLATE_UNKNOWN
