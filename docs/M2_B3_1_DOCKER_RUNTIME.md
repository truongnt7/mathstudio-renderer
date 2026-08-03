# M2-B3.1 Docker Runtime

## Image Contents

| Component | Version | Notes |
|-----------|---------|-------|
| Base | python:3.12-slim-bookworm | Debian 12 |
| Manim | 0.20.1 | Community edition |
| Cairo | Debian package | Rendering backend |
| Pango | Debian package | Font rendering |
| FFmpeg | Debian package | Video encoding |
| ffprobe | Included with FFmpeg | Artifact validation |
| LaTeX | texlive-latex-base + extras | MathTex support |
| dvisvgm | Debian package | LaTeX→SVG |
| Noto Sans | fonts-noto | Vietnamese support |
| User | renderer (UID 1000) | Non-root |

## Security Constraints

```yaml
user: "1000"
read_only: true
tmpfs:
  - /tmp:rw,noexec,nosuid,size=256m
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
pids_limit: 256
```

## Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: "4"
      memory: 4g
```

## Volume Mounts

| Path | Type | Purpose |
|------|------|---------|
| `/output` | Named volume | Validated artifacts (persisted) |
| `/workspace` | Named volume | Manim working directory (temporary) |
| `/tmp` | tmpfs | Scratch space (in-memory, no-exec) |

## Build

```bash
docker build \
  --platform linux/arm64 \
  --tag mathstudio-renderer:latest \
  --file Dockerfile \
  .
```

## Run (single render)

```bash
docker run --rm \
  --user 1000 \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  --security-opt no-new-privileges:true \
  -v "$(pwd)/output:/output:rw" \
  -v "$(pwd)/workspace:/workspace:rw" \
  mathstudio-renderer:latest \
  render /app/fixtures/hello.json
```

## Health Check

```bash
docker run --rm \
  --user 1000 \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  mathstudio-renderer:latest \
  health
```

## What the Container Does NOT Have

- No Supabase credentials
- No worker claim loop
- No network requirements for rendering
- No privileged mode
- No Docker socket mount
- No host filesystem access beyond mounted volumes
- No production secrets of any kind
