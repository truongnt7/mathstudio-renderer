"""Workspace and output directory management.

Each render request gets an isolated workspace under ``workspace/{request_id}/``
(temporary Manim work) and a persistent output directory under
``output/{request_id}/`` (validated artifacts).

Path validation ensures that derived paths never escape their root, even if a
crafted request_id somehow bypassed schema validation.
"""

from __future__ import annotations

import shutil
from pathlib import Path


class PathEscapeError(ValueError):
    """Raised when a computed path escapes its allowed root."""


def _assert_within(path: Path, root: Path) -> Path:
    """Resolve path and assert it is strictly under root."""
    resolved = path.resolve()
    resolved_root = root.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise PathEscapeError(f"Computed path {resolved} escapes root {resolved_root}") from exc
    return resolved


class WorkspaceManager:
    def __init__(self, workspace_root: Path, output_root: Path) -> None:
        self._workspace_root = workspace_root.resolve()
        self._output_root = output_root.resolve()

    # ------------------------------------------------------------------
    # Workspace (temporary Manim work directory)
    # ------------------------------------------------------------------

    def workspace_dir(self, request_id: str) -> Path:
        """Return (and verify) the workspace directory for a request."""
        p = self._workspace_root / request_id
        return _assert_within(p, self._workspace_root)

    def create_workspace(self, request_id: str) -> Path:
        """Create an isolated workspace and return its path."""
        d = self.workspace_dir(request_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def cleanup_workspace(self, request_id: str) -> None:
        """Remove the workspace directory after render completion."""
        try:
            d = self.workspace_dir(request_id)
            if d.exists():
                shutil.rmtree(d)
        except (PathEscapeError, OSError):
            pass

    # ------------------------------------------------------------------
    # Output (validated artifacts — persisted after container exit)
    # ------------------------------------------------------------------

    def output_dir(self, request_id: str) -> Path:
        """Return (and verify) the output directory for a request."""
        p = self._output_root / request_id
        return _assert_within(p, self._output_root)

    def create_output_dir(self, request_id: str) -> Path:
        """Create the output directory and return its path."""
        d = self.output_dir(request_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ------------------------------------------------------------------
    # Symlink guard
    # ------------------------------------------------------------------

    def validate_artifact_path(self, artifact: Path, output_dir: Path) -> Path:
        """Ensure artifact is a regular file within output_dir (no symlinks)."""
        if artifact.is_symlink():
            raise PathEscapeError(f"Artifact path is a symlink: {artifact}")
        resolved = artifact.resolve()
        resolved_out = output_dir.resolve()
        try:
            resolved.relative_to(resolved_out)
        except ValueError as exc:
            raise PathEscapeError(f"Artifact {resolved} escapes output dir {resolved_out}") from exc
        if not resolved.is_file():
            raise FileNotFoundError(f"Artifact is not a regular file: {resolved}")
        return resolved
