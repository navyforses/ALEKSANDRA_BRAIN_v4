# v7.0 Foundation — Status Report

**Date:** 2026-05-24
**Verifier:** `scripts/verify_v7_foundation.py`
**Last run:** 21/25 PASS

---

## Result by phase

| Phase | Scope | Status | Evidence |
|---|---|---|---|
| 0.1 | Environment probe | DONE | `01_environment_check.md` |
| 0.2 | Cloud accounts | DONE | GEMINI_API_KEY + ANTHROPIC budget set |
| 0.3 | Python deps (PyMC, DoWhy, NumPyro, ...) | DONE | `03_uv_install.log` + `03_imports_check.log` (15/15 imports PASS) |
| 0.4 | Docker TVB pull + smoke test | DONE | image 10.6 GB; container start+stop verified |
| 0.5 | Frontend libs (plotly, vis, xyflow) | DONE | `05_npm_install.log` (271 packages) |
| 0.6 | AI model downloads | **BLOCKED** | needs HF_TOKEN |
| 0.7 | `.env` keys | DONE (placeholders) | HF_TOKEN value still empty |
| 0.8 | Verifier 25/25 | **21/25** | `08_verifier_run3.log` |

---

## What was created or modified

| Path | Action | Notes |
|---|---|---|
| `requirements-v7.txt` | NEW | 21 pinned deps. `causalnex` dropped (pandas<2 conflict) — replaced with `pgmpy`. `jax[metal]` → `jax[cpu]` (Intel Arc, no backend). |
| `.venv-v7/` | NEW | Python 3.12.13. Gitignored. Separate from existing v6.0 `.venv`. |
| `viewer/package.json` | MODIFIED | +5 v7.0 deps: plotly.js-dist-min 3.5.1, react-plotly.js 2.6.0, vis-network 10.1.0, vis-data 8.0.4, @xyflow/react 12.10.2. |
| `viewer/package-lock.json` | MODIFIED | npm resolved tree. |
| `scripts/verify_v7_foundation.py` | NEW | 25-check verifier with UTF-8 stdout, no external deps. |
| `scripts/download_v7_models.py` | NEW | Phase 0.6 helper — runs after HF_TOKEN is set. |
| `.env` | MODIFIED | +v7.0 section (GEMINI_API_KEY, GOOGLE_AI_STUDIO_KEY, GCP_PROJECT_ID, TVB_DOCKER_URL, HF_TOKEN placeholder). Gitignored. |
| `v7_architecture/foundation_logs/` | NEW | 5 log files + this status doc. |

---

## 4 remaining checks (all block on HF_TOKEN)

```
FAIL  hf_token_set            → user adds HF_TOKEN to .env
FAIL  medgemma_4b_downloaded  → blocked on HF_TOKEN + license accept
FAIL  txgemma_9b_downloaded   → blocked on HF_TOKEN + license accept
FAIL  medsiglip_downloaded    → blocked on HF_TOKEN + license accept
```

### Unblock procedure (~30-90 min for downloads)

1. **Get HF_TOKEN.** Visit https://huggingface.co/settings/tokens → "New token" → name `aleksandra-v7` → role `Read` → create → copy.
2. **Paste into `.env` line ~172**: `HF_TOKEN=hf_...`
3. **Accept 3 model licenses** (gated by Google, instant approval after click):
   - https://huggingface.co/google/medgemma-4b-it
   - https://huggingface.co/google/txgemma-9b-chat
   - https://huggingface.co/google/medsiglip-448
4. **Run download:**
   ```bash
   .venv-v7/Scripts/python.exe scripts/download_v7_models.py
   ```
   Expected: ~28 GB total, 30-90 min depending on bandwidth. `resume_download=True` is set, safe to interrupt.
5. **Re-run verifier:**
   ```bash
   .venv-v7/Scripts/python.exe scripts/verify_v7_foundation.py
   ```
   Target: 25/25 PASS.

---

## Deviations from `00_FOUNDATION_PREREQUISITES.md`

| Doc says | Actual | Reason |
|---|---|---|
| `causalnex>=0.13` | dropped, `pgmpy>=0.1.25` instead | causalnex max version is 0.12.1 (2022) and pins pandas<2.0 — incompatible with PyMC's pandas 2.x stack. pgmpy is the modern DAG library. |
| `jax[metal]` | `jax[cpu]` | Host is Windows + Intel Arc GPU. JAX Metal is macOS-only; no CUDA either. |
| `.env.local` filename | `.env` (existing v6.0 convention) | Project already uses `.env`; v7.0 keys appended to same file. |
| `huggingface-cli` command | `hf` (new official CLI) | huggingface_hub 1.x deprecated `huggingface-cli`. `hf` ships in the same package. |
| TVB image "~2 GB" | actual 10.6 GB | Doc estimate stale — current `thevirtualbrain/tvb-run:latest` includes full SciPy + Jupyter + neuro stack. |
| Vertex AI / GCP | NOT signed up | Foundation doc marks it OPTIONAL ("only if MedGemma 27B cloud"). MVP uses MedGemma 4B local + HF Inference Endpoint if larger models become necessary. |

---

## Hardware reality (Phase 0.1 findings)

| Resource | Required | Host | Implication |
|---|---|---|---|
| RAM | >= 16 GB | 15.66 GB | TxGemma 9B (18 GB) won't fit in RAM during inference — will swap heavily or OOM. MedGemma 4B (8 GB) should run but with overhead pressure. |
| GPU | any | Intel Arc 130V (8 GB VRAM, integrated) | No JAX backend (no CUDA, no Metal). PyMC/NumPyro CPU-bound. Bayesian inference workable but slower than M2/M3 reference. |
| Disk C: | >= 50 GB | 194 GB free | Comfortable. After all v7.0 models + Docker: ~150 GB still free. |

---

## Constraints honored

- [x] Did not touch v6.0 production stack (no n8n restart, no Neo4j migration).
- [x] Did not install anything globally with sudo.
- [x] Did not commit `.env` to git (verified `.gitignore` covers `.env`, `.env.local`, `.env.*.local`).
- [x] Cost so far: **$0** (everything used so far is free tier or pre-paid).

---

## Next action

Decide between:

1. **Provide HF_TOKEN now** → run `download_v7_models.py` → reach 25/25 → tag commit `v7-foundation-ready`. Recommended path.
2. **Skip models for now** → commit current 21/25 progress under tag `v7-foundation-partial` → revisit Phase 0.6 later.
3. **Hold off on git commits** → keep everything local until you've reviewed `requirements-v7.txt`, `verify_v7_foundation.py`, and the `.env` v7.0 section.

After Foundation 25/25: proceed to v7.0 Phase 7.0 (Belief State Foundation) per `v7_architecture/AI_BRAIN.md` section 4.
