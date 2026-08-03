# mathstudio-renderer

**Dockerized Manim Renderer Runtime — M2-B3.1**

A self-contained, hardened renderer that accepts structured render requests, executes Manim scenes via a controlled subprocess, validates the produced artifacts, and emits structured metadata.

---

## Quick Start

```bash
# Install dependencies
make install

# Check local health
make health

# Render hello smoke fixture
make render-hello

# Build Docker image
make docker-build

# Health check in Docker
make docker-health

# Smoke all four fixtures in Docker
make docker-smoke
```

---

## Architecture

```
Request JSON  →  Schema Validation  →  Registry Lookup  →  Subprocess Runner
                  (closed, no extras)    (4 templates)       (shell=False, timeout)
                                                                      ↓
                                              Artifact Pipeline ← Manim output
                                              (ffprobe validation, poster gen)
                                                      ↓
                                              output/{request_id}/
                                                  render.mp4
                                                  poster.png
                                                  metadata.json
                                                  diagnostics.json
```

---

## CLI

```bash
python -m mathstudio_renderer health
python -m mathstudio_renderer list-templates
python -m mathstudio_renderer validate fixtures/hello.json
python -m mathstudio_renderer render fixtures/hello.json
python -m mathstudio_renderer inspect-output output/hello-smoke-001
```

---

## Registered Templates

| Code | Description |
|------|-------------|
| `HELLO_V1` | Hello Math Studio text animation |
| `MATHTEX_SMOKE_V1` | LaTeX math expression (requires LaTeX in Docker) |
| `VIETNAMESE_TEXT_V1` | Vietnamese Unicode text rendering |
| `GEOMETRY_SMOKE_V1` | Shapes + transformation smoke test |

---

## Security

- **Closed schema**: unknown fields rejected at validation time
- **No arbitrary code**: scene classes come from the registry only
- **`shell=False`**: subprocess never uses shell interpretation
- **Sanitized env**: only allowlisted environment variables forwarded
- **Path validation**: output paths validated to stay within request root
- **Symlink guard**: symlinks rejected in artifact validation
- **Non-root**: container runs as UID 1000
- **Read-only root FS**: no writes outside `/output`, `/workspace`, `/tmp`
- **No secrets**: no credentials, tokens, or Supabase keys

---

## Development

```bash
make install       # uv sync
make format        # ruff format
make lint          # ruff check
make typecheck     # mypy
make test          # unit + security tests
make test-integration  # slow integration tests (renders Manim)
```

---

## Docker Hardening

The production compose applies:
- `read_only: true`
- `user: "1000"` (non-root)
- `tmpfs /tmp` (in-memory, no-exec)
- `no-new-privileges: true`
- `cap_drop: [ALL]`
- `pids_limit: 256`
- `memory: 4g`
- `cpus: 4`
- No privileged mode, no Docker socket, no host-root mount
- No Supabase credentials

---

## Boundary — M2-B3.1

This renderer does **not** implement:
- Production Supabase integration
- Worker claim loop or queue polling
- B1/B2 job management
- AI generation
- Arbitrary user scene execution
- Full Math Rendering SDK

B3.2 (Worker ↔ Renderer Integration) begins after this milestone is reviewed.
