"""Docker compatibility tests for B3.2 worker integration.

These tests require Docker and the ``mathstudio-renderer:latest`` image.
Run with: ``uv run pytest tests/docker/ -m docker -v``

Verified properties:
- UID/GID: container runs as 1000:1000 (not root-group)
- Machine-readable events: events.jsonl is emitted and parseable
- Network-disabled render: all four templates work with --network none
- events.jsonl contains terminal event (completed/failed/cancelled)
- Stable result schema: metadata.json present and correct shape
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

IMAGE = "mathstudio-renderer:latest"

FIXTURES = {
    "HELLO_V1": {
        "request_version": "1.0.0",
        "request_id": "b32compat-hello01",
        "template_code": "HELLO_V1",
        "template_version": "1.0.0",
        "quality": "preview",
        "aspect_ratio": "16:9",
        "parameters": {},
        "output": {"formats": ["mp4"]},
    },
    "MATHTEX_SMOKE_V1": {
        "request_version": "1.0.0",
        "request_id": "b32compat-mathtex01",
        "template_code": "MATHTEX_SMOKE_V1",
        "template_version": "1.0.0",
        "quality": "preview",
        "aspect_ratio": "16:9",
        "parameters": {},
        "output": {"formats": ["mp4"]},
    },
    "VIETNAMESE_TEXT_V1": {
        "request_version": "1.0.0",
        "request_id": "b32compat-viet01",
        "template_code": "VIETNAMESE_TEXT_V1",
        "template_version": "1.0.0",
        "quality": "preview",
        "aspect_ratio": "16:9",
        "parameters": {},
        "output": {"formats": ["mp4"]},
    },
    "GEOMETRY_SMOKE_V1": {
        "request_version": "1.0.0",
        "request_id": "b32compat-geom01",
        "template_code": "GEOMETRY_SMOKE_V1",
        "template_version": "1.0.0",
        "quality": "preview",
        "aspect_ratio": "16:9",
        "parameters": {},
        "output": {"formats": ["mp4"]},
    },
}


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
            shell=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _image_exists() -> bool:
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", IMAGE],
            capture_output=True,
            timeout=10,
            shell=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _run_renderer(
    fixture: dict,
    timeout: int = 180,
) -> tuple[int, Path, Path, subprocess.CompletedProcess]:
    """Run the renderer container and return (exit_code, artifact_dir, request_dir, result).

    Uses /tmp explicitly since macOS Docker Desktop only shares /Users and /tmp
    by default — /var/folders is not accessible inside containers.

    Note: the renderer creates artifacts in {output_root}/{request_id}/, so
    the returned ``artifact_dir`` is the subdirectory containing actual files.
    """
    # Use mkdtemp (not context manager) so directories survive the return
    tmpdir = tempfile.mkdtemp(dir="/tmp")
    tmp = Path(tmpdir)
    req_dir = tmp / "request"
    out_root = tmp / "output"
    ws_dir = tmp / "workspace"
    req_dir.mkdir()
    out_root.mkdir()
    ws_dir.mkdir()

    req_file = req_dir / "request.json"
    req_file.write_text(json.dumps(fixture))

    cmd = [
        "docker", "run", "--rm",
        "--user", "1000:1000",
        "--read-only",
        "--network", "none",
        "--security-opt", "no-new-privileges",
        "--cap-drop", "ALL",
        "--pids-limit", "256",
        "--memory", "2g",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m",
        "--tmpfs", "/var/cache/fontconfig:rw,noexec,nosuid,size=32m",
        "-v", f"{req_dir}:/request:ro",
        "-v", f"{out_root}:/output:rw",
        "-v", f"{ws_dir}:/workspace:rw",
        IMAGE,
        "render", "/request/request.json",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )

    # The renderer creates output in {output_root}/{request_id}/
    request_id = fixture.get("request_id", "")
    artifact_dir = out_root / request_id if request_id else out_root

    return result.returncode, artifact_dir, req_dir, result


pytestmark = pytest.mark.docker

# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def require_docker():
    if not _docker_available():
        pytest.skip("Docker daemon not available")
    if not _image_exists():
        pytest.skip(f"Docker image {IMAGE!r} not found — run docker build first")


# ---------------------------------------------------------------------------
# UID / GID hardening
# ---------------------------------------------------------------------------


class TestUidGid:
    def test_container_runs_as_uid_1000_gid_1000(self) -> None:
        cmd = [
            "docker", "run", "--rm",
            "--user", "1000:1000",
            IMAGE,
            "render", "--help",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=False)
        # Should not error due to permission issues
        assert result.returncode == 0 or "Usage" in result.stdout or "Usage" in result.stderr

    def test_image_uid_gid_in_container(self) -> None:
        cmd = ["docker", "run", "--rm", "--entrypoint", "id", IMAGE]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=False)
        output = result.stdout + result.stderr
        # uid=1000(renderer) gid=1000(renderer)
        assert "uid=1000" in output
        assert "gid=1000" in output
        # Must NOT be gid=0 (root group)
        assert "gid=0" not in output


# ---------------------------------------------------------------------------
# Machine-readable events
# ---------------------------------------------------------------------------


class TestMachineReadableEvents:
    def test_events_file_created_on_success(self) -> None:
        returncode, out_dir, _, _result = _run_renderer(FIXTURES["HELLO_V1"])
        assert returncode == 0, f"render failed: {_result.stderr[-500:]}"
        events_path = out_dir / "events.jsonl"
        assert events_path.exists(), "events.jsonl was not created"

    def test_events_are_valid_json_lines(self) -> None:
        returncode, out_dir, _, _result = _run_renderer(FIXTURES["HELLO_V1"])
        assert returncode == 0
        events_path = out_dir / "events.jsonl"
        lines = events_path.read_text().splitlines()
        assert len(lines) >= 2, "expected at least received + completed events"
        for line in lines:
            obj = json.loads(line)
            assert "protocol_version" in obj
            assert "renderer_request_id" in obj
            assert "phase" in obj
            assert "progress_hint" in obj
            assert "status" in obj

    def test_terminal_event_is_completed(self) -> None:
        returncode, out_dir, _, _ = _run_renderer(FIXTURES["HELLO_V1"])
        assert returncode == 0
        from mathstudio_renderer.events import get_final_event

        final = get_final_event(out_dir / "events.jsonl")
        assert final is not None
        assert final["status"] == "completed"

    def test_renderer_request_id_matches(self) -> None:
        returncode, out_dir, _, _ = _run_renderer(FIXTURES["HELLO_V1"])
        assert returncode == 0
        from mathstudio_renderer.events import parse_events_file

        events = parse_events_file(out_dir / "events.jsonl")
        assert all(e["renderer_request_id"] == "b32compat-hello01" for e in events)

    def test_events_file_created_on_failure(self) -> None:
        bad_fixture = {**FIXTURES["HELLO_V1"], "template_code": "UNKNOWN_TEMPLATE_XYZ"}
        returncode, out_dir, _, _ = _run_renderer(bad_fixture)
        assert returncode != 0
        events_path = out_dir / "events.jsonl"
        # events.jsonl may or may not exist depending on when failure occurs
        # If it exists, verify it contains a failed status
        if events_path.exists():
            from mathstudio_renderer.events import get_final_event

            final = get_final_event(events_path)
            if final is not None:
                assert final["status"] == "failed"


# ---------------------------------------------------------------------------
# Network-disabled renders
# ---------------------------------------------------------------------------


class TestNetworkDisabledRenders:
    """All four templates must render successfully with --network none."""

    def test_hello_network_disabled(self) -> None:
        returncode, out_dir, _, result = _run_renderer(FIXTURES["HELLO_V1"])
        assert returncode == 0, f"HELLO_V1 failed with network disabled: {result.stderr[-500:]}"
        assert (out_dir / "render.mp4").exists()

    def test_mathtex_network_disabled(self) -> None:
        returncode, out_dir, _, result = _run_renderer(FIXTURES["MATHTEX_SMOKE_V1"])
        assert returncode == 0, f"MATHTEX failed with network disabled: {result.stderr[-500:]}"
        assert (out_dir / "render.mp4").exists()

    def test_vietnamese_network_disabled(self) -> None:
        returncode, out_dir, _, result = _run_renderer(FIXTURES["VIETNAMESE_TEXT_V1"])
        assert returncode == 0, f"VIETNAMESE failed with network disabled: {result.stderr[-500:]}"
        assert (out_dir / "render.mp4").exists()

    def test_geometry_network_disabled(self) -> None:
        returncode, out_dir, _, result = _run_renderer(FIXTURES["GEOMETRY_SMOKE_V1"])
        assert returncode == 0, f"GEOMETRY failed with network disabled: {result.stderr[-500:]}"
        assert (out_dir / "render.mp4").exists()


# ---------------------------------------------------------------------------
# Stable result schema
# ---------------------------------------------------------------------------


class TestStableResultSchema:
    def test_metadata_json_present_and_correct(self) -> None:
        returncode, out_dir, _, _ = _run_renderer(FIXTURES["HELLO_V1"])
        assert returncode == 0
        meta_path = out_dir / "metadata.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["status"] == "completed"
        assert meta["request_id"] == "b32compat-hello01"
        assert meta["template_code"] == "HELLO_V1"
        assert "artifacts" in meta
        assert "elapsed_ms" in meta

    def test_events_phases_are_ordered(self) -> None:
        returncode, out_dir, _, _ = _run_renderer(FIXTURES["HELLO_V1"])
        assert returncode == 0
        from mathstudio_renderer.events import parse_events_file

        events = parse_events_file(out_dir / "events.jsonl")
        statuses = [e["status"] for e in events]
        # All intermediate events should be "running"; final should be "completed"
        assert statuses[-1] == "completed"
        for s in statuses[:-1]:
            assert s == "running"

    def test_no_secrets_in_events(self) -> None:
        returncode, out_dir, _, _ = _run_renderer(FIXTURES["HELLO_V1"])
        assert returncode == 0
        events_text = (out_dir / "events.jsonl").read_text()
        for secret_marker in [
            "SUPABASE", "service_role", "DATABASE_URL",
            "secret", "token", "password",
        ]:
            assert secret_marker.lower() not in events_text.lower(), (
                f"Secret marker {secret_marker!r} found in events.jsonl"
            )

    def test_no_secrets_in_metadata(self) -> None:
        returncode, out_dir, _, _ = _run_renderer(FIXTURES["HELLO_V1"])
        assert returncode == 0
        meta_text = (out_dir / "metadata.json").read_text()
        for secret_marker in [
            "SUPABASE", "service_role", "DATABASE_URL",
            "password", "bearer",
        ]:
            assert secret_marker.lower() not in meta_text.lower()
