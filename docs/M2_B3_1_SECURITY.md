# M2-B3.1 Security Model

## Threat Model

The renderer accepts JSON requests from a future worker. The primary threats are:

1. **Arbitrary code execution** via request fields
2. **Path traversal** via `request_id`
3. **Shell injection** via subprocess arguments
4. **Secret exfiltration** from container environment
5. **Privilege escalation** within the container

## Controls

### 1. Closed Input Schema

`RenderRequest` uses Pydantic with `extra="forbid"`. Any field not in the schema is rejected at parse time. The schema does not contain:

- Python source code
- Module paths
- Scene class names
- Shell arguments
- Host filesystem paths
- Environment variable overrides

### 2. Request ID Validation

`request_id` must match `^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$`. Rejected:

- `../` and all traversal patterns
- Absolute paths (`/`, `C:\`)
- Shell metacharacters (`;`, `&`, `|`, `` ` ``, `$`, `(`, `)`, `<`, `>`)
- Whitespace (space, tab, newline)
- Null bytes
- URL-encoded traversal (`%2F`, `%2e%2e`)
- Length > 64

### 3. Template Allowlist

Scene modules and class names are resolved exclusively from the sealed `TemplateRegistry`. The registry is populated at import time and sealed — no further registration is possible at runtime.

### 4. `shell=False` Invariant

The Manim subprocess is always launched with `shell=False`. The command is a list of strings with no user-controlled values. The environment is built from an explicit allowlist (`SAFE_ENV_KEYS`).

### 5. Process Termination

Timeout → SIGTERM to process group → 5s wait → SIGKILL. The process group (`start_new_session=True`) ensures child processes are killed.

### 6. Output Path Validation

Before accepting any artifact:

1. Path is resolved to an absolute path
2. Verified to be within `output/{request_id}/`
3. Verified to be a regular file (not a symlink, directory, or device)

### 7. No Secrets in Image

The Docker image contains no Supabase URLs, API keys, service role tokens, or production credentials. The `.env` file is gitignored and not copied into the image.

### 8. Non-Root Container

Container runs as UID 1000 (`renderer`). Root filesystem is read-only. `/tmp` is a `tmpfs` mount (no-exec, nosuid). Capabilities are all dropped.

## Audit Results

| Control | Status |
|---------|--------|
| No eval/exec in source | VERIFIED |
| No os.system | VERIFIED |
| shell=False enforced | VERIFIED |
| Request schema closed | VERIFIED |
| Template allowlist | VERIFIED |
| Path traversal rejection | VERIFIED |
| Symlink guard | VERIFIED |
| Subprocess timeout | VERIFIED |
| SIGTERM→SIGKILL | VERIFIED |
| No secrets in source | VERIFIED |
| Non-root container | VERIFIED |
