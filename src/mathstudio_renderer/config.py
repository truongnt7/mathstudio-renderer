"""Renderer configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

# Root of the project — used to resolve output/workspace dirs
# config.py lives at: <project_root>/src/mathstudio_renderer/config.py
_HERE = Path(__file__).resolve().parent   # = src/mathstudio_renderer/
_PROJECT_ROOT = _HERE.parent.parent       # = project root


def _resolve(env_key: str, default: str) -> Path:
    raw = os.environ.get(env_key, default)
    p = Path(raw)
    if not p.is_absolute():
        p = (_PROJECT_ROOT / p).resolve()
    return p


class Config:
    """Renderer runtime configuration."""

    output_dir: Path = _resolve("RENDERER_OUTPUT_DIR", "output")
    workspace_dir: Path = _resolve("RENDERER_WORKSPACE_DIR", "workspace")
    default_timeout: float = float(os.environ.get("RENDERER_DEFAULT_TIMEOUT", "120"))
    log_level: str = os.environ.get("RENDERER_LOG_LEVEL", "INFO").upper()
    log_format: str = os.environ.get("RENDERER_LOG_FORMAT", "json")  # "json" | "text"

    @classmethod
    def ensure_dirs(cls) -> None:
        cls.output_dir.mkdir(parents=True, exist_ok=True)
        cls.workspace_dir.mkdir(parents=True, exist_ok=True)


config = Config()
