# M2-B3.1 Architecture

## Overview

The renderer is a single-process Python application that accepts JSON render requests, resolves them against an internal template registry, executes Manim via a controlled subprocess, validates the produced artifacts, and writes structured metadata.

## Component Map

```
CLI (cli.py)
  └─ RenderRequest schema validation (schemas.py)
       └─ TemplateRegistry lookup (registry.py)
            └─ Renderer orchestrator (runtime.py)
                 ├─ WorkspaceManager (workspace.py)
                 ├─ RenderSubprocessRunner (subprocess_runner.py)
                 │    └─ Manim CLI subprocess [shell=False]
                 └─ ArtifactPipeline (artifacts.py)
                      ├─ ffprobe validation
                      ├─ Poster generation (ffmpeg)
                      └─ Metadata / diagnostics
```

## Render Flow

1. **received** — Request JSON received by CLI
2. **validating** — Pydantic schema validation (`extra="forbid"`)
3. **preparing_workspace** — Isolated `workspace/{request_id}/manim_media/` created
4. **rendering** — Manim subprocess spawned (`shell=False`, timeout, SIGTERM→SIGKILL)
5. **validating_artifacts** — ffprobe checks MP4; Pillow checks PNG
6. **writing_metadata** — metadata.json, diagnostics.json, safe-render.log written
7. **completed** / **failed** / **cancelled** — Terminal state

## Local Phases → Future B3.2 Mapping

| Local phase | B1 job status (future) |
|-------------|------------------------|
| received | claimed |
| validating | processing |
| rendering | processing |
| completed | completed |
| failed | failed |
| cancelled | cancelled |

## Directories

| Directory | Purpose | Persisted? |
|-----------|---------|-----------|
| `workspace/{req_id}/` | Manim working directory | No — cleaned after render |
| `output/{req_id}/` | Validated artifacts | Yes — survives container exit |

## Security Boundaries

- No user-supplied Python code executes
- Scene class is resolved from the registry, never from request data
- Environment is filtered to an explicit allowlist before being passed to subprocess
- Output paths are resolved and validated against the output root before writing
