#!/usr/bin/env bash
# mathstudio-renderer container entrypoint
# M2-B3.1
set -euo pipefail

# Ensure runtime directories exist and are writable
mkdir -p "${RENDERER_OUTPUT_DIR:-/output}"
mkdir -p "${RENDERER_WORKSPACE_DIR:-/workspace}"

# Refresh font cache if needed (first start)
if [ "${REFRESH_FONTS:-0}" = "1" ]; then
    fc-cache -fv 2>/dev/null || true
fi

# Execute the CLI with all provided arguments
exec python -m mathstudio_renderer "$@"
