---
phase: quick-260615-ca6
plan: "01"
subsystem: perception
tags: [bugfix, ci, supabase, httpx, whitespace]
dependency_graph:
  requires: []
  provides: [clean-supabase-headers]
  affects: [scripts/ledger.py]
tech_stack:
  added: []
  patterns: [defense-in-depth .strip()]
key_files:
  created: []
  modified:
    - scripts/ledger.py
decisions:
  - "Strip at two sites (source + header builder) for defense-in-depth: _supabase_creds() is the upstream fix; _supabase_headers() is the fallback for any future caller that passes a raw env-var value directly."
metrics:
  duration: "< 5 minutes"
  completed: "2026-06-15"
---

# Quick CA6: Strip Whitespace from Supabase Credentials — Summary

**One-liner:** Defensive `.strip()` at two sites in `_supabase_creds()` and `_supabase_headers()` eliminates trailing-newline httpx `Illegal header value` crash in CI.

## What Was Done

The GitHub secret `SUPABASE_SERVICE_ROLE_KEY` arrives in the CI environment with a trailing
newline. `load_env()` only strips values it reads from `.env` for keys **not** already in
`os.environ`, so the GitHub-secret code path bypassed all stripping — causing
`httpx.LocalProtocolError: Illegal header value b'***'` on the first HTTP call in the
"Perception fallback (worker-independent)" workflow job.

Two defensive `.strip()` calls were added to `scripts/ledger.py`:

**Site 1 — `_supabase_creds()` (line ~172):**
- `SUPABASE_URL`: `.strip().rstrip("/")` — strips surrounding whitespace before the
  existing trailing-slash removal.
- `SUPABASE_SERVICE_ROLE_KEY`: `.strip()` — removes any leading/trailing whitespace
  including `\n`.
- Existing `if not url or not key` guard unchanged (an all-whitespace value strips to `""`
  and still trips the guard correctly).

**Site 2 — `_supabase_headers()` (line ~181):**
- `key = key.strip()` added as the first statement in the function body.
- Protects all callers (including `perception_tick.py`) that pass a key coming from
  `_supabase_creds()` or directly from `os.environ`.

Both sites carry an English comment explaining the root cause.

No other files were touched. Function signatures and return shapes are unchanged.

## Verification Output

```
PASS: no newline in headers; creds stripped
```

Command used:
```bash
.venv/Scripts/python.exe -c "
import sys; sys.argv=['x']
from scripts.ledger import _supabase_headers, _supabase_creds
import os
h = _supabase_headers('secretkey\n')
assert all('\n' not in v for v in h.values()), 'newline leaked into header value'
assert h['apikey']=='secretkey' and h['Authorization']=='Bearer secretkey', h
os.environ['SUPABASE_URL'] = 'https://x.supabase.co/\n'
os.environ['SUPABASE_SERVICE_ROLE_KEY'] = ' k \n'
u, k = _supabase_creds()
assert u=='https://x.supabase.co' and k=='k', (u, k)
print('PASS: no newline in headers; creds stripped')
"
```

## Commit

| Hash    | Message                                                                         |
|---------|---------------------------------------------------------------------------------|
| 75f8641 | fix(perception): strip whitespace from Supabase creds to prevent httpx Illegal header value in CI |

`git diff --stat` confirms only `scripts/ledger.py` changed (1 file, 7 insertions, 2 deletions).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — change is purely defensive input sanitisation with no new network endpoints,
auth paths, or schema changes.

## Self-Check: PASSED

- `scripts/ledger.py` exists and contains `.strip()` at both required sites.
- Commit `75f8641` exists in `git log`.
- Verification command printed `PASS`.
- No other files modified.
