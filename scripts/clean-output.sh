#!/usr/bin/env bash
# Clean output and workspace directories.
# Usage: ./scripts/clean-output.sh [--all]
set -euo pipefail

OUTPUT_DIR="${RENDERER_OUTPUT_DIR:-./output}"
WORKSPACE_DIR="${RENDERER_WORKSPACE_DIR:-./workspace}"

echo "[INFO] Cleaning workspace: ${WORKSPACE_DIR}"
find "${WORKSPACE_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true

if [[ "${1:-}" == "--all" ]]; then
    echo "[INFO] Cleaning output: ${OUTPUT_DIR}"
    find "${OUTPUT_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
    # Restore .gitkeep
    touch "${OUTPUT_DIR}/.gitkeep" 2>/dev/null || true
fi

touch "${WORKSPACE_DIR}/.gitkeep" 2>/dev/null || true
echo "[INFO] Done."
