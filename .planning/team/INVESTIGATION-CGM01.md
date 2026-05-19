# Investigation: CGM-01 Qdrant 403 Root Cause
**Agent:** R2 (Wave 1)
**Audit reference:** `.planning/AUDIT_2026-05-18.md` §Phase 3
**Date:** 2026-05-18

## Call stack
1. `scripts/verify_phase3.py:143` — `check_cgm_01(report)` calls `generate_summary(fixture_query, audience="internal", language="en")` on line 164.
2. `scripts/communicator/summarize.py:212` — `generate_summary()` calls `retrieve(query, t_at=None, top_k=8)` on line 227 (imported from `scripts.rag.retrieve` line 42).
3. `scripts/rag/retrieve.py:218` — `retrieve()` calls `_qdrant_search(qvec, top_k=top_k, min_score=min_score)` on line 260.
4. **`scripts/rag/retrieve.py:130`** — `_qdrant_search()` defined; **BUG SITE**: `httpx.post()` to `/collections/<name>/points/search` without an `api-key` header. Against Qdrant Cloud (`*.aws.cloud.qdrant.io:6333`), an unauthenticated request returns HTTP 403, which surfaces as `HTTPStatusError: Client error '403 Forbidden'` via `r.raise_for_status()` on line 144.

## Bug site (verbatim)
File: `scripts/rag/retrieve.py`
Lines: 130-145
```python
def _qdrant_search(query_vec: list[float], top_k: int, min_score: float) -> list[dict]:
    """Cosine search on `papers`. Returns raw point hits."""
    body = {
        "vector": query_vec,
        "limit": top_k,
        "score_threshold": min_score,
        "with_payload": True,
        "with_vector": False,
    }
    r = httpx.post(
        f"{_qdrant_url()}/collections/{QDRANT_COLLECTION}/points/search",
        json=body,
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("result", []) or []
```

## Reference fix (already applied to one of the 5 patched files)
File: `scripts/verify_phase2.py` (clearest example — same `httpx`-direct pattern, not the SDK pattern).

Diff from HEAD (via `git diff HEAD -- scripts/verify_phase2.py`):
```diff
@@ scripts/verify_phase2.py:95-100 (_qdrant_collection_info)
     url = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333").replace(
         "localhost", "127.0.0.1"
     )
-    r = httpx.get(f"{url}/collections/{name}", timeout=10)
+    api_key = os.environ.get("QDRANT_API_KEY")
+    headers = {"api-key": api_key} if api_key else {}
+    r = httpx.get(f"{url}/collections/{name}", headers=headers, timeout=10)
     r.raise_for_status()
     return r.json().get("result", {})

@@ scripts/verify_phase2.py:299-309 (check_mem_alignment)
     qdrant_url = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333").replace(
         "localhost", "127.0.0.1"
     )
+    qdrant_key = os.environ.get("QDRANT_API_KEY")
+    qdrant_headers = {"api-key": qdrant_key} if qdrant_key else {}
     r = httpx.post(
         f"{qdrant_url}/collections/papers/points/scroll",
         json={"limit": 50, "with_payload": True, "with_vector": False},
+        headers=qdrant_headers,
         timeout=30,
     )
```

Pattern in plain English: read `QDRANT_API_KEY` from env, build `{"api-key": api_key}` headers (empty dict when unset for local Docker), pass `headers=headers` into the `httpx` call. The SDK-style patches (embedder.py / retrofit_qdrant_stamps.py / setup_qdrant.py) use `QdrantClient(url=url, api_key=os.environ.get("QDRANT_API_KEY") or None)` — same env var, different binding because they use the Python SDK rather than raw HTTP.

## Proposed patch
Edit tool call args:
- `file_path`: `c:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\scripts\rag\retrieve.py`
- `old_string`:
  ```
  def _qdrant_search(query_vec: list[float], top_k: int, min_score: float) -> list[dict]:
      """Cosine search on `papers`. Returns raw point hits."""
      body = {
          "vector": query_vec,
          "limit": top_k,
          "score_threshold": min_score,
          "with_payload": True,
          "with_vector": False,
      }
      r = httpx.post(
          f"{_qdrant_url()}/collections/{QDRANT_COLLECTION}/points/search",
          json=body,
          timeout=30,
      )
      r.raise_for_status()
      return r.json().get("result", []) or []
  ```
- `new_string`:
  ```
  def _qdrant_search(query_vec: list[float], top_k: int, min_score: float) -> list[dict]:
      """Cosine search on `papers`. Returns raw point hits."""
      body = {
          "vector": query_vec,
          "limit": top_k,
          "score_threshold": min_score,
          "with_payload": True,
          "with_vector": False,
      }
      api_key = os.environ.get("QDRANT_API_KEY")
      headers = {"api-key": api_key} if api_key else {}
      r = httpx.post(
          f"{_qdrant_url()}/collections/{QDRANT_COLLECTION}/points/search",
          json=body,
          headers=headers,
          timeout=30,
      )
      r.raise_for_status()
      return r.json().get("result", []) or []
  ```

Note: `import os` is already present on line 46 of `scripts/rag/retrieve.py` — no import change required.

## Verification
```bash
.venv/Scripts/python.exe -X utf8 -m scripts.verify_phase3
```
Expected: CGM-01 PASS (live `summarize()` now reaches Qdrant Cloud with auth, returns evidence chunks, Sonnet drafts cited claims). Total either **10/11** (if REGR cascades from a Phase 2.5 C.3 daily-digest dry-window failure) or **11/11** (if `daily_digest` has fired once since last Phase 2.5 run).

## Drift audit — all Qdrant access sites in scripts/

| File:Line | Type | api_key passed? | Notes |
|---|---|---|---|
| `scripts/setup_qdrant.py:67` | `QdrantClient(url=..., api_key=...)` | **YES** (already patched, uncommitted) | Reference SDK pattern |
| `scripts/chunking/embedder.py:73` | `QdrantClient(url=url, api_key=api_key)` | **YES** (already patched, uncommitted) | Reference SDK pattern |
| `scripts/chunking/retrofit_qdrant_stamps.py:93` | `QdrantClient(url=..., api_key=...)` | **YES** (already patched, uncommitted) | Reference SDK pattern |
| `scripts/verify_phase2.py:100` | `httpx.get` → `/collections/{name}` | **YES** (already patched, uncommitted) | Reference HTTP pattern (`headers={"api-key": ...}`) |
| `scripts/verify_phase2.py:305` | `httpx.post` → `/collections/papers/points/scroll` | **YES** (already patched, uncommitted) | Reference HTTP pattern |
| `scripts/verify_phase2_5.py:132` | `httpx.get` → `/collections/{name}` | **YES** (already patched, uncommitted) | Reference HTTP pattern |
| **`scripts/rag/retrieve.py:139-143`** | `httpx.post` → `/collections/{coll}/points/search` | **NO** | **THIS IS THE BUG SITE — produces the 403 that fails CGM-01** |

Grep evidence:
- `Grep "QdrantClient(" scripts/` → 3 hits, all SDK-pattern, all already patched.
- `Grep "collections/.*/(points|scroll|search)"` → 2 hits: `verify_phase2.py:305` (patched) and `rag/retrieve.py:140` (**unpatched**).
- `Grep "httpx\.(post|get|put|delete).*collections"` → 2 hits: `verify_phase2.py:100` and `verify_phase2_5.py:132`, both patched.
- No `qdrant.io` literal in `scripts/` — URL is always built from `QDRANT_URL` env var.

`scripts/rag/retrieve.py` is the single remaining drift site. No other Qdrant call paths exist in the agent stack (Communicator → `summarize` → `retrieve` → `_qdrant_search` is the only route reachable from CGM-01).
