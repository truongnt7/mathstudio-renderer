# mathstudio-renderer Makefile — M2-B3.1
# Run targets with: make <target>
# All targets fail fast (exit codes are never suppressed).

.DEFAULT_GOAL := help
SHELL         := bash
.SHELLFLAGS   := -euo pipefail -c

PYTHON        := python
UV            := uv
IMAGE_NAME    := mathstudio-renderer
IMAGE_TAG     := latest
IMAGE         := $(IMAGE_NAME):$(IMAGE_TAG)

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
.PHONY: help
help:
	@echo "mathstudio-renderer — M2-B3.1"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install / sync all dependencies"
	@echo ""
	@echo "Code quality:"
	@echo "  make format           Format code with ruff"
	@echo "  make lint             Lint code with ruff"
	@echo "  make typecheck        Type-check with mypy"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run unit + security tests (fast)"
	@echo "  make test-integration Run integration tests (slow, needs Manim)"
	@echo "  make test-all         Run all tests"
	@echo "  make security-test    Run security tests only"
	@echo ""
	@echo "Local render:"
	@echo "  make health           Run local health check"
	@echo "  make render-hello     Render hello fixture locally"
	@echo "  make render-mathtex   Render MathTex fixture locally"
	@echo "  make render-vietnamese Render Vietnamese fixture locally"
	@echo "  make render-geometry  Render geometry fixture locally"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-health    Health check inside container"
	@echo "  make docker-smoke     Run all four fixtures in Docker"
	@echo "  make docker-test      Run docker pytest suite"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Remove output/workspace artifacts"
	@echo "  make clean-all        Remove all generated output"

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
.PHONY: install
install:
	$(UV) sync

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------
.PHONY: format
format:
	$(UV) run ruff format src/ tests/

.PHONY: lint
lint:
	$(UV) run ruff check src/ tests/

.PHONY: typecheck
typecheck:
	$(UV) run mypy src/

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
.PHONY: test
test:
	$(UV) run pytest tests/unit/ tests/security/ -v --tb=short

.PHONY: test-integration
test-integration:
	$(UV) run pytest tests/integration/ -v --tb=short -m integration

.PHONY: test-all
test-all:
	$(UV) run pytest tests/ -v --tb=short --ignore=tests/docker/ \
		-m "not docker"

.PHONY: security-test
security-test:
	$(UV) run pytest tests/security/ -v --tb=short

# ---------------------------------------------------------------------------
# Local render
# ---------------------------------------------------------------------------
.PHONY: health
health:
	$(UV) run python -m mathstudio_renderer health

.PHONY: render-hello
render-hello:
	$(UV) run python -m mathstudio_renderer render fixtures/hello.json

.PHONY: render-mathtex
render-mathtex:
	$(UV) run python -m mathstudio_renderer render fixtures/mathtex.json

.PHONY: render-vietnamese
render-vietnamese:
	$(UV) run python -m mathstudio_renderer render fixtures/vietnamese_text.json

.PHONY: render-geometry
render-geometry:
	$(UV) run python -m mathstudio_renderer render fixtures/geometry_smoke.json

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
.PHONY: docker-build
docker-build:
	docker build \
		--platform linux/arm64 \
		--tag $(IMAGE) \
		--file Dockerfile \
		.
	@echo ""
	@echo "Image built: $(IMAGE)"
	@docker image inspect $(IMAGE) --format \
		'Digest: {{index .RepoDigests 0}} | Size: {{.Size}} bytes | Arch: {{.Architecture}}'

.PHONY: docker-health
docker-health:
	docker run --rm \
		--user 1000 \
		--read-only \
		--tmpfs /tmp:rw,noexec,nosuid,size=256m \
		--security-opt no-new-privileges:true \
		$(IMAGE) health

.PHONY: docker-smoke
docker-smoke: _docker-smoke-hello _docker-smoke-mathtex _docker-smoke-viet _docker-smoke-geom
	@echo ""
	@echo "=== All Docker smoke tests passed ==="

.PHONY: _docker-smoke-hello
_docker-smoke-hello:
	@mkdir -p output/docker-hello workspace/docker-hello
	docker run --rm \
		--user 1000 \
		--read-only \
		--tmpfs /tmp:rw,noexec,nosuid,size=256m \
		--security-opt no-new-privileges:true \
		-v "$(CURDIR)/output/docker-hello:/output:rw" \
		-v "$(CURDIR)/workspace/docker-hello:/workspace:rw" \
		$(IMAGE) render /app/fixtures/hello.json
	@echo "[OK] Hello smoke: $$(ls output/docker-hello/hello-smoke-001/ 2>/dev/null || echo 'no output dir')"

.PHONY: _docker-smoke-mathtex
_docker-smoke-mathtex:
	@mkdir -p output/docker-mathtex workspace/docker-mathtex
	docker run --rm \
		--user 1000 \
		--read-only \
		--tmpfs /tmp:rw,noexec,nosuid,size=512m \
		--security-opt no-new-privileges:true \
		-v "$(CURDIR)/output/docker-mathtex:/output:rw" \
		-v "$(CURDIR)/workspace/docker-mathtex:/workspace:rw" \
		$(IMAGE) render /app/fixtures/mathtex.json
	@echo "[OK] MathTex smoke passed"

.PHONY: _docker-smoke-viet
_docker-smoke-viet:
	@mkdir -p output/docker-viet workspace/docker-viet
	docker run --rm \
		--user 1000 \
		--read-only \
		--tmpfs /tmp:rw,noexec,nosuid,size=256m \
		--security-opt no-new-privileges:true \
		-v "$(CURDIR)/output/docker-viet:/output:rw" \
		-v "$(CURDIR)/workspace/docker-viet:/workspace:rw" \
		$(IMAGE) render /app/fixtures/vietnamese_text.json
	@echo "[OK] Vietnamese smoke passed"

.PHONY: _docker-smoke-geom
_docker-smoke-geom:
	@mkdir -p output/docker-geom workspace/docker-geom
	docker run --rm \
		--user 1000 \
		--read-only \
		--tmpfs /tmp:rw,noexec,nosuid,size=256m \
		--security-opt no-new-privileges:true \
		-v "$(CURDIR)/output/docker-geom:/output:rw" \
		-v "$(CURDIR)/workspace/docker-geom:/workspace:rw" \
		$(IMAGE) render /app/fixtures/geometry_smoke.json
	@echo "[OK] Geometry smoke passed"

.PHONY: docker-test
docker-test:
	DOCKER_IMAGE=$(IMAGE) $(UV) run pytest tests/docker/ -v --tb=short

# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------
.PHONY: clean
clean:
	./scripts/clean-output.sh

.PHONY: clean-all
clean-all:
	./scripts/clean-output.sh --all
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
