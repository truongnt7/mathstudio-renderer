"""Unit tests for the subprocess runner — security-critical component."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from mathstudio_renderer.errors import ErrorCode, RenderError
from mathstudio_renderer.subprocess_runner import RenderSubprocessRunner, quality_subdir


class TestCommandConstruction:
    """Verify the Manim command is built safely from trusted values."""

    def setup_method(self):
        self.runner = RenderSubprocessRunner(timeout=30.0)

    def test_shell_false_never_set_true(self):
        """shell=False is an unconditional invariant."""
        # We verify by checking that the command is always a list, never a string.
        # A string command would imply shell=True.
        cmd = self.runner._build_command(
            scene_file=Path("/app/src/scenes/hello_scene.py"),
            scene_class="HelloScene",
            quality="preview",
            media_dir=Path("/tmp/media"),
        )
        assert isinstance(cmd, list), "Command must be a list (never a string)"
        assert len(cmd) > 0

    def test_command_uses_sys_executable(self):
        cmd = self.runner._build_command(
            scene_file=Path("/app/src/scenes/hello_scene.py"),
            scene_class="HelloScene",
            quality="preview",
            media_dir=Path("/tmp/media"),
        )
        assert cmd[0] == sys.executable

    def test_preview_quality_flag(self):
        cmd = self.runner._build_command(
            scene_file=Path("/app/scenes/hello_scene.py"),
            scene_class="HelloScene",
            quality="preview",
            media_dir=Path("/tmp/m"),
        )
        assert "-ql" in cmd

    def test_final_quality_flag(self):
        cmd = self.runner._build_command(
            scene_file=Path("/app/scenes/hello_scene.py"),
            scene_class="HelloScene",
            quality="final",
            media_dir=Path("/tmp/m"),
        )
        assert "-qh" in cmd

    def test_media_dir_in_command(self):
        media = Path("/tmp/test_media")
        cmd = self.runner._build_command(
            scene_file=Path("/app/scenes/hello_scene.py"),
            scene_class="HelloScene",
            quality="preview",
            media_dir=media,
        )
        assert "--media_dir" in cmd
        assert str(media) in cmd

    def test_scene_class_at_end(self):
        cmd = self.runner._build_command(
            scene_file=Path("/app/scenes/hello_scene.py"),
            scene_class="MyScene",
            quality="preview",
            media_dir=Path("/tmp/m"),
        )
        assert cmd[-1] == "MyScene"

    def test_no_shell_arg_in_command(self):
        cmd = self.runner._build_command(
            scene_file=Path("/app/scenes/hello_scene.py"),
            scene_class="HelloScene",
            quality="preview",
            media_dir=Path("/tmp/m"),
        )
        for item in cmd:
            assert "shell" not in str(item).lower()


class TestEnvironmentSanitization:
    """Verify the environment is sanitized — only allowlisted keys forwarded."""

    def setup_method(self):
        self.runner = RenderSubprocessRunner()

    def test_only_safe_keys_in_env(self):
        import os

        with patch.dict(os.environ, {"EVIL_VAR": "evil_value", "PATH": "/bin"}):
            env = self.runner._build_env(None)
        assert "EVIL_VAR" not in env

    def test_path_forwarded(self):
        import os

        with patch.dict(os.environ, {"PATH": "/usr/bin:/bin"}):
            env = self.runner._build_env(None)
        assert env.get("PATH") == "/usr/bin:/bin"

    def test_extra_env_only_safe_keys_allowed(self):
        env = self.runner._build_env({"EVIL_EXTRA": "bad", "PATH": "/safe"})
        assert "EVIL_EXTRA" not in env

    def test_env_is_dict_of_strings(self):
        env = self.runner._build_env(None)
        for k, v in env.items():
            assert isinstance(k, str)
            assert isinstance(v, str)


class TestTimeoutBehavior:
    """Test timeout enforcement and process termination."""

    def setup_method(self):
        self.runner = RenderSubprocessRunner(timeout=1.0)

    def test_timeout_raises_render_error(self, tmp_path):
        """A process that sleeps longer than timeout must raise RENDER_TIMEOUT."""
        # Use a simple sleep command — this is a trusted internal test command
        with pytest.raises(RenderError) as exc_info:
            self.runner._run(
                cmd=[sys.executable, "-c", "import time; time.sleep(10)"],
                cwd=tmp_path,
                env={"PATH": "/usr/bin:/bin"},
                timeout=0.5,
            )
        assert exc_info.value.code == ErrorCode.RENDER_TIMEOUT

    def test_successful_process_returns_result(self, tmp_path):
        result = self.runner._run(
            cmd=[sys.executable, "-c", "print('hello')"],
            cwd=tmp_path,
            env={"PATH": "/usr/bin:/bin"},
            timeout=10.0,
        )
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_failed_process_raises_render_error(self, tmp_path):
        with pytest.raises(RenderError) as exc_info:
            self.runner._run(
                cmd=[sys.executable, "-c", "import sys; sys.exit(1)"],
                cwd=tmp_path,
                env={"PATH": "/usr/bin:/bin"},
                timeout=10.0,
            )
        assert exc_info.value.code == ErrorCode.RENDER_PROCESS_FAILED


class TestQualitySubdir:
    def test_preview_subdir(self):
        assert quality_subdir("preview") == "480p15"

    def test_final_subdir(self):
        assert quality_subdir("final") == "1080p60"

    def test_unknown_falls_back(self):
        assert quality_subdir("unknown") == "480p15"
