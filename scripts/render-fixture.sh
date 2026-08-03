#!/usr/bin/env bash
# Render a named fixture using the local Python environment.
# Usage: ./scripts/render-fixture.sh hello
#        ./scripts/render-fixture.sh mathtex
#        ./scripts/render-fixture.sh vietnamese_text
#        ./scripts/render-fixture.sh geometry_smoke
set -euo pipefail

FIXTURE_NAME="${1:?Usage: $0 <fixture_name>}"
FIXTURE_FILE="fixtures/${FIXTURE_NAME}.json"

if [[ ! -f "${FIXTURE_FILE}" ]]; then
    echo "[ERROR] Fixture not found: ${FIXTURE_FILE}" >&2
    exit 1
fi

echo "[INFO] Rendering fixture: ${FIXTURE_FILE}"
python -m mathstudio_renderer render "${FIXTURE_FILE}"
