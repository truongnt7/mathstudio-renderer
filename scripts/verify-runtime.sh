#!/usr/bin/env bash
# Verify all runtime dependencies are available.
# Exit 0 if all hard checks pass; non-zero otherwise.
set -euo pipefail

PASS=0
WARN=0
FAIL=0

check() {
    local name="$1"
    local cmd="$2"
    local soft="${3:-false}"
    if result=$(eval "${cmd}" 2>&1); then
        echo "[OK]   ${name}: ${result:-present}"
        ((PASS++)) || true
    else
        if [[ "${soft}" == "true" ]]; then
            echo "[WARN] ${name}: not found (optional)"
            ((WARN++)) || true
        else
            echo "[FAIL] ${name}: not found (required)"
            ((FAIL++)) || true
        fi
    fi
}

echo "=== mathstudio-renderer Runtime Verification ==="
echo ""

check "Python 3.12+"       "python --version | grep -E 'Python 3\.(1[2-9]|[2-9][0-9])'"
check "Manim"              "python -c 'import manim; print(manim.__version__)'"
check "ffmpeg"             "ffmpeg -version 2>&1 | head -1"
check "ffprobe"            "ffprobe -version 2>&1 | head -1"
check "latex"              "latex --version 2>&1 | head -1" "true"
check "dvisvgm"            "dvisvgm --version 2>&1 | head -1" "true"
check "Noto Sans font"     "python -c 'import manimpango; fonts=manimpango.list_fonts(); assert any(\"Noto\" in f for f in fonts), fonts'" "true"
check "output writable"    "test -w \"\${RENDERER_OUTPUT_DIR:-./output}\" && echo writable"
check "workspace writable" "test -w \"\${RENDERER_WORKSPACE_DIR:-./workspace}\" && echo writable"

echo ""
echo "=== Summary: ${PASS} ok | ${WARN} warn | ${FAIL} fail ==="

if [[ "${FAIL}" -gt 0 ]]; then
    exit 1
fi
exit 0
