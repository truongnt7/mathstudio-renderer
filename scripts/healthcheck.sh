#!/usr/bin/env bash
# Container healthcheck script
# Called by Docker HEALTHCHECK directive
set -euo pipefail

exec python -m mathstudio_renderer health 2>&1
