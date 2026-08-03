"""Unit tests for workspace and path management."""

from __future__ import annotations

from pathlib import Path

import pytest

from mathstudio_renderer.workspace import PathEscapeError, WorkspaceManager


@pytest.fixture
def tmp_roots(tmp_path: Path):
    ws = tmp_path / "workspace"
    out = tmp_path / "output"
    ws.mkdir()
    out.mkdir()
    return ws, out


@pytest.fixture
def manager(tmp_roots):
    ws, out = tmp_roots
    return WorkspaceManager(ws, out)


class TestWorkspaceCreation:
    def test_create_workspace_returns_path(self, manager, tmp_roots):
        ws_root, _ = tmp_roots
        path = manager.create_workspace("req-001")
        assert path.exists()
        assert path.is_dir()

    def test_workspace_is_under_root(self, manager, tmp_roots):
        ws_root, _ = tmp_roots
        path = manager.create_workspace("req-002")
        assert str(path).startswith(str(ws_root))

    def test_cleanup_removes_dir(self, manager):
        path = manager.create_workspace("req-003")
        assert path.exists()
        manager.cleanup_workspace("req-003")
        assert not path.exists()

    def test_cleanup_nonexistent_is_safe(self, manager):
        manager.cleanup_workspace("nonexistent-999")  # should not raise


class TestOutputCreation:
    def test_create_output_returns_path(self, manager, tmp_roots):
        _, out_root = tmp_roots
        path = manager.create_output_dir("req-out-001")
        assert path.exists()
        assert path.is_dir()
        assert str(path).startswith(str(out_root))


class TestPathValidation:
    def test_normal_artifact_validates(self, manager, tmp_path):
        out_dir = tmp_path / "output" / "req-001"
        out_dir.mkdir(parents=True)
        artifact = out_dir / "render.mp4"
        artifact.write_bytes(b"fake mp4 data")
        result = manager.validate_artifact_path(artifact, out_dir)
        assert result == artifact.resolve()

    def test_symlink_rejected(self, manager, tmp_path):
        out_dir = tmp_path / "output" / "req-002"
        out_dir.mkdir(parents=True)
        target = tmp_path / "secret.txt"
        target.write_text("secret")
        link = out_dir / "evil.mp4"
        link.symlink_to(target)
        with pytest.raises(PathEscapeError):
            manager.validate_artifact_path(link, out_dir)

    def test_path_outside_output_rejected(self, manager, tmp_path):
        out_dir = tmp_path / "output" / "req-003"
        out_dir.mkdir(parents=True)
        outside = tmp_path / "etc" / "passwd"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_text("root:x:0:0")
        with pytest.raises(PathEscapeError):
            manager.validate_artifact_path(outside, out_dir)


class TestWorkspaceIsolation:
    def test_different_requests_get_different_dirs(self, manager):
        p1 = manager.create_workspace("req-a")
        p2 = manager.create_workspace("req-b")
        assert p1 != p2

    def test_cleanup_only_affects_own_request(self, manager):
        p1 = manager.create_workspace("req-x")
        p2 = manager.create_workspace("req-y")
        manager.cleanup_workspace("req-x")
        assert not p1.exists()
        assert p2.exists()
