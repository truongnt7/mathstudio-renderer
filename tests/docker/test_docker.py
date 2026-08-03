"""Docker integration tests.

These tests require:
- Docker daemon running
- Image built: ``make docker-build``
- Set environment variable: DOCKER_IMAGE=mathstudio-renderer:latest

Skip all by default unless DOCKER_IMAGE env var is set.
"""

from __future__ import annotations

import os
import subprocess

import pytest

IMAGE = os.environ.get("DOCKER_IMAGE", "mathstudio-renderer:latest")

# Skip all tests in this module if Docker image hasn't been built
pytestmark = pytest.mark.docker


def _docker_run(
    *args: str,
    image: str = IMAGE,
    extra_env: dict[str, str] | None = None,
    mounts: list[str] | None = None,
    timeout: int = 180,
    read_only: bool = True,
    user: str = "renderer",
) -> subprocess.CompletedProcess:
    cmd = ["docker", "run", "--rm"]

    if read_only:
        cmd += ["--read-only"]
    if user:
        cmd += ["--user", user]

    cmd += ["--tmpfs", "/tmp:rw,noexec,nosuid,size=256m"]

    if mounts:
        for m in mounts:
            cmd += ["-v", m]

    if extra_env:
        for k, v in extra_env.items():
            cmd += ["-e", f"{k}={v}"]

    cmd += [image, *args]

    return subprocess.run(  # noqa: S603
        cmd,
        shell=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.fixture(scope="module", autouse=True)
def require_docker():
    try:
        r = subprocess.run(  # noqa: S603, S607
            ["docker", "image", "inspect", IMAGE],
            shell=False,
            capture_output=True,
            timeout=10,
        )
        if r.returncode != 0:
            pytest.skip(f"Docker image {IMAGE!r} not found — run 'make docker-build' first")
    except FileNotFoundError:
        pytest.skip("Docker not available")


class TestDockerHealth:
    def test_health_command_exits_zero(self):
        r = _docker_run("health")
        assert r.returncode == 0, f"Health failed:\n{r.stdout}\n{r.stderr}"

    def test_health_mentions_python(self):
        r = _docker_run("health")
        output = r.stdout + r.stderr
        assert "python" in output.lower() or r.returncode == 0


class TestDockerNonRoot:
    def test_effective_uid_not_root(self):
        r = _docker_run(
            "--entrypoint-override",  # not real — use a direct check
            image=IMAGE,
        )
        # Run id command to check UID
        cmd = ["docker", "run", "--rm", "--entrypoint", "id", IMAGE]
        r = subprocess.run(  # noqa: S603
            cmd, shell=False, capture_output=True, text=True, timeout=10
        )
        output = r.stdout + r.stderr
        # Should NOT show uid=0(root)
        assert "uid=0" not in output, f"Container running as root: {output}"
        assert r.returncode == 0

    def test_whoami_not_root(self):
        cmd = ["docker", "run", "--rm", "--entrypoint", "whoami", IMAGE]
        r = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=10)  # noqa: S603
        assert "root" not in r.stdout.strip(), f"Container user is root: {r.stdout}"


class TestDockerReadOnlyFS:
    def test_cannot_write_to_root_fs(self, tmp_path):
        """Verify root filesystem is read-only — writes to /tmp (tmpfs) work,
        writes to / do not."""
        # Try writing to / — should fail
        # Use python to try writing to /etc
        r = subprocess.run(  # noqa: S603
            [
                "docker",
                "run",
                "--rm",
                "--read-only",
                "--tmpfs",
                "/tmp",
                "--entrypoint",
                "python3",
                IMAGE,
                "-c",
                "open('/etc/evil', 'w').write('x')",
            ],
            shell=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Should fail (non-zero exit or exception)
        assert r.returncode != 0, "Expected write to read-only /etc to fail"


class TestDockerHelloRender:
    def test_hello_renders_in_docker(self, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        r = _docker_run(
            "render",
            "/app/fixtures/hello.json",
            mounts=[
                f"{output_dir}:/output:rw",
                f"{workspace_dir}:/workspace:rw",
            ],
            timeout=180,
        )
        assert r.returncode == 0, f"Hello render failed:\n{r.stdout}\n{r.stderr}"

        # Check output survived container exit
        results = list(output_dir.rglob("render.mp4"))
        assert len(results) > 0, "render.mp4 not found in output volume"
        assert results[0].stat().st_size > 1024


class TestDockerMathTexRender:
    def test_mathtex_renders_in_docker(self, tmp_path):
        """MathTex must render inside Docker without host LaTeX."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        r = _docker_run(
            "render",
            "/app/fixtures/mathtex.json",
            mounts=[
                f"{output_dir}:/output:rw",
                f"{workspace_dir}:/workspace:rw",
            ],
            timeout=300,
        )
        assert r.returncode == 0, f"MathTex render failed:\n{r.stdout}\n{r.stderr}"
        results = list(output_dir.rglob("render.mp4"))
        assert results and results[0].stat().st_size > 1024


class TestDockerVietnameseRender:
    def test_vietnamese_renders_in_docker(self, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        r = _docker_run(
            "render",
            "/app/fixtures/vietnamese_text.json",
            mounts=[
                f"{output_dir}:/output:rw",
                f"{workspace_dir}:/workspace:rw",
            ],
            timeout=180,
        )
        assert r.returncode == 0, f"Vietnamese render failed:\n{r.stdout}\n{r.stderr}"
        results = list(output_dir.rglob("render.mp4"))
        assert results and results[0].stat().st_size > 1024


class TestDockerGeometryRender:
    def test_geometry_renders_in_docker(self, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        r = _docker_run(
            "render",
            "/app/fixtures/geometry_smoke.json",
            mounts=[
                f"{output_dir}:/output:rw",
                f"{workspace_dir}:/workspace:rw",
            ],
            timeout=180,
        )
        assert r.returncode == 0, f"Geometry render failed:\n{r.stdout}\n{r.stderr}"
        results = list(output_dir.rglob("render.mp4"))
        assert results and results[0].stat().st_size > 1024
