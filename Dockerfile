# ============================================================
# mathstudio-renderer — Dockerized Manim Renderer Runtime
# M2-B3.1
# ============================================================
#
# Targets: linux/arm64 (Apple Silicon) and linux/amd64
# Build:   docker buildx build --platform linux/arm64 -t mathstudio-renderer:latest .
#
# Security:
#   - Non-root user (renderer, UID 1000)
#   - No secrets in image
#   - Read-only root filesystem compatible (tmpfs for /tmp)
#   - No Docker socket
#   - No privileged mode required

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# ---------------------------------------------------------------------------
# OCI metadata labels
# ---------------------------------------------------------------------------
LABEL org.opencontainers.image.title="mathstudio-renderer"
LABEL org.opencontainers.image.description="Dockerized Manim Renderer Runtime — M2-B3.1"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.source="https://github.com/ai-math-studio/mathstudio-renderer"

# ---------------------------------------------------------------------------
# System dependencies
# ---------------------------------------------------------------------------
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools
    gcc \
    g++ \
    pkg-config \
    # Cairo and Pango (Manim rendering backend)
    libcairo2-dev \
    libpango1.0-dev \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-dev \
    # FFmpeg and ffprobe
    ffmpeg \
    # LaTeX for MathTex (dvisvgm-based pipeline)
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-science \
    dvisvgm \
    ghostscript \
    # Vietnamese-capable open-source fonts (Noto family)
    fonts-noto \
    fonts-noto-cjk \
    fonts-open-sans \
    fonts-liberation \
    # Other utilities
    curl \
    fontconfig \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ---------------------------------------------------------------------------
# uv — fast Python package manager
# ---------------------------------------------------------------------------
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------
WORKDIR /app

# uv venv configuration
ENV UV_LINK_MODE=copy
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy dependency specification first for layer cache optimization
COPY pyproject.toml uv.lock ./

# Install dependencies (excluding the project itself) for cache efficiency
RUN uv sync --no-dev --frozen --no-cache --no-install-project

# Copy application source
COPY src/ ./src/
COPY fixtures/ ./fixtures/
COPY scripts/ ./scripts/

# Install the project package itself into the venv
RUN uv sync --no-dev --frozen --no-cache

# Make scripts executable
RUN chmod +x scripts/*.sh

# ---------------------------------------------------------------------------
# Non-root user
# ---------------------------------------------------------------------------
RUN useradd --uid 1000 --gid 0 --no-create-home --shell /bin/bash renderer

# Create runtime directories owned by renderer
RUN mkdir -p /output /workspace && chown renderer:root /output /workspace
RUN chmod 750 /output /workspace

# ---------------------------------------------------------------------------
# Runtime environment
# ---------------------------------------------------------------------------
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV RENDERER_OUTPUT_DIR=/output
ENV RENDERER_WORKSPACE_DIR=/workspace
ENV RENDERER_LOG_FORMAT=json
ENV RENDERER_DEFAULT_TIMEOUT=120

# Fonts
ENV FONTCONFIG_PATH=/etc/fonts
ENV MANIMGL_OPENGL_RENDERER=0

# ---------------------------------------------------------------------------
# Healthcheck
# ---------------------------------------------------------------------------
HEALTHCHECK \
    --interval=30s \
    --timeout=15s \
    --start-period=60s \
    --retries=3 \
    CMD /app/scripts/healthcheck.sh

# ---------------------------------------------------------------------------
# Final
# ---------------------------------------------------------------------------
USER renderer
WORKDIR /app

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["health"]

# PATH already includes /app/.venv/bin — python resolves to venv python
