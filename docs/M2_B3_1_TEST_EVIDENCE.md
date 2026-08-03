# M2-B3.1 Test Evidence

*This file is updated with real results as tests are run.*

## Test Suite Structure

```
tests/
  unit/
    test_schemas.py        — 40 tests (closed schema, traversal, allowlists)
    test_registry.py       — 20 tests (4 templates, sealed, scene file resolution)
    test_workspace.py      — 12 tests (isolation, symlink guard, path escape)
    test_errors.py         — 8 tests (error codes, safe dict, diagnostics)
    test_subprocess_runner.py — 15 tests (shell=False, env sanitization, timeout)
  security/
    test_security.py       — 35 tests (traversal, injection, no secrets)
  integration/
    test_fixtures.py       — 10 tests (actual renders, timeout, unknown template)
  docker/
    test_docker.py         — 10 tests (image, non-root, read-only, all 4 fixtures)
```

## Evidence Collected

*Evidence is populated by the closure report generation.*
