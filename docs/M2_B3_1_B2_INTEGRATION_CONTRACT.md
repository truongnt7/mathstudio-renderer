# M2-B3.1 → B3.2 Integration Contract

**Status: DRAFT — Not implemented. B3.2 starts after M2-B3.1 review.**

This document defines the planned integration surface between the B2 Worker and the renderer.

---

## Renderer Input (from Worker)

The worker will send a `RenderRequest` JSON:

```json
{
  "request_version": "1.0.0",
  "request_id": "<job-id>",
  "template_code": "HELLO_V1",
  "template_version": "1.0.0",
  "quality": "preview",
  "aspect_ratio": "16:9",
  "parameters": {},
  "output": { "formats": ["mp4"] }
}
```

The `request_id` must match the B1 job ID.

---

## Renderer Output (to Worker)

After successful render, the output directory contains:

```
output/{request_id}/
  render.mp4       — validated H.264 video
  poster.png       — first-frame PNG
  metadata.json    — full structured metadata
  diagnostics.json — internal diagnostics (not forwarded to client)
  safe-render.log  — brief status log
```

---

## Phase Mapping (renderer local → B1 job status)

| Renderer Phase | B1 Job Status | Notes |
|----------------|---------------|-------|
| received | — | Internal only |
| validating | processing | |
| rendering | processing | |
| validating_artifacts | processing | |
| writing_metadata | processing | |
| completed | completed | Trigger artifact upload |
| failed | failed | Forward safe error message |
| cancelled | cancelled | On worker cancel signal |

---

## Error Code Mapping (renderer → B1)

| Renderer Error Code | B1 Code (planned) |
|---------------------|-------------------|
| RENDER_REQUEST_INVALID | JOB_INPUT_INVALID |
| RENDER_TEMPLATE_UNKNOWN | JOB_INPUT_INVALID |
| RENDER_TIMEOUT | JOB_RENDER_TIMEOUT |
| RENDER_PROCESS_FAILED | JOB_RENDER_ERROR |
| RENDER_ARTIFACT_MISSING | JOB_RENDER_ERROR |
| RENDER_ARTIFACT_INVALID | JOB_RENDER_ERROR |
| RENDER_CANCELLED | JOB_CANCELLED |
| RENDER_INTERNAL_ERROR | JOB_INTERNAL_ERROR |

---

## Artifact Upload (B3.2)

The worker will read the output directory and upload artifacts to storage (Supabase Storage). The renderer is not involved in upload — it only produces files.

---

## What B3.2 must NOT change

- The renderer schema (extend, do not modify existing fields)
- The template registry (add templates, do not remove)
- The artifact validation pipeline
- The security model

---

*This contract is not implemented in M2-B3.1. Do not begin B3.2 until M2-B3.1 is reviewed.*
