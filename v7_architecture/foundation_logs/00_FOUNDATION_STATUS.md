# v7.0 Foundation — Status Report

**Date:** 2026-05-24
**Verifier:** `scripts/verify_v7_foundation.py`
**Last run:** **25/25 PASS — FOUNDATION COMPLETE** (git tag `v7-foundation-ready`)

---

## Result by phase

| Phase | Scope | Status | Evidence |
|---|---|---|---|
| 0.1 | Environment probe | DONE | `01_environment_check.md` |
| 0.2 | Cloud accounts | DONE | GEMINI_API_KEY + ANTHROPIC budget set |
| 0.3 | Python deps (PyMC, DoWhy, NumPyro, ...) | DONE | `03_uv_install.log` + `03_imports_check.log` (15/15 imports PASS) |
| 0.4 | Docker TVB pull + smoke test | DONE | image 10.6 GB; container start+stop verified |
| 0.5 | Frontend libs (plotly, vis, xyflow) | DONE | `05_npm_install.log` (271 packages) |
| 0.6 | AI model downloads | DONE | MedGemma 4B 8.1 GB · TxGemma 9B 18 GB · MedSigLIP 3.3 GB; `06_model_downloads.log` |
| 0.7 | `.env` keys | DONE | all 25 verifier-tracked env vars set |
| 0.8 | Verifier 25/25 | **DONE** | `08_verifier_run4.log` — 25/25 PASS |

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

## How Foundation reached 25/25 (HF_TOKEN unblock)

Initial verifier run hit 21/25; the 4 blocked checks all depended on an
HF_TOKEN with access to Google's gated medical models. A fine-grained
token created at https://huggingface.co/settings/tokens initially failed
with HTTP 403 — root cause was the missing "Read access to public gated
repositories" permission, not the license accepts (those were already
done). After adding the 3 model slugs (`google/medgemma-4b-it`,
`google/txgemma-9b-chat`, `google/medsiglip-448`) to the token's
"Repositories permissions" with all 4 checkboxes enabled, file-resolve
URLs went from 403 → 200 and `scripts/download_v7_models.py` pulled all
3 models cleanly:

- `~/models/medgemma-4b`   8.1 GB
- `~/models/txgemma-9b`   18 GB
- `~/models/medsiglip`     3.3 GB
- **Total disk used:** 29 GB

Total download time: ~46 minutes. TxGemma 9B (18 GB) dominated.

---

## Deviations from `00_FOUNDATION_PREREQUISITES.md`

| Doc says | Actual | Reason |
|---|---|---|
| `causalnex>=0.13` | dropped, `pgmpy>=0.1.25` instead | causalnex max version is 0.12.1 (2022) and pins pandas<2.0 — incompatible with PyMC's pandas 2.x stack. pgmpy is the modern DAG library. |
| `jax[metal]` | `jax[cpu]` | Host is Windows + Intel Arc GPU. JAX Metal is macOS-only; no CUDA either. |
| `.env.local` filename | `.env` (existing v6.0 convention) | Project already uses `.env`; v7.0 keys appended to same file. |
| `huggingface-cli` command | `hf` (new official CLI) | huggingface_hub 1.x deprecated `huggingface-cli`. `hf` ships in the same package. |
| TVB image "~2 GB" | actual 10.6 GB | Doc estimate stale — current `thevirtualbrain/tvb-run:latest` includes full SciPy + Jupyter + neuro stack. |
| TVB port `8888:8888` | actual `8888:8080` | TVB Framework web UI listens on **port 8080** inside the container, not 8888. Verified by HTTP 200 probe. Helper `scripts/run_tvb.sh` uses the correct mapping. The base image also prints a deprecation notice ("Updates discontinued after 26.7.x"); revisit upstream image choice during Phase 7.0 simulation work. |
| Vertex AI / GCP | NOT signed up | Foundation doc marks it OPTIONAL ("only if MedGemma 27B cloud"). MVP uses MedGemma 4B local + HF Inference Endpoint if larger models become necessary. |

---

## Hardware reality (Phase 0.1 findings)

| Resource | Required | Host | Implication |
|---|---|---|---|
| RAM | >= 16 GB | 15.66 GB | TxGemma 9B (18 GB) won't fit in RAM during inference — will swap heavily or OOM. MedGemma 4B (8 GB) should run but with overhead pressure. |
| GPU | any | Intel Arc 130V (8 GB VRAM, integrated) | No JAX backend (no CUDA, no Metal). PyMC/NumPyro CPU-bound. Bayesian inference workable but slower than M2/M3 reference. |
| Disk C: | >= 50 GB | 194 GB free | Comfortable. After all v7.0 models + Docker: ~150 GB still free. |

---

## Phase 7.0 smoke tests (post-install validation)

Ran on 2026-05-24 after the verifier hit 21/25, to confirm the new
stack is not just importable but actually usable:

| Test | Result | Detail |
|---|---|---|
| PyMC NUTS sampling | PASS | 21 s for 2 chains × 1000 draws. Posterior means within tolerance of synthetic truth (alpha Δ=0.053, beta Δ=0.016, sigma Δ=0.015). |
| DoWhy ATE estimation | PASS | Backdoor linear regression on a synthetic Z→T→Y graph. Estimate 1.4817 vs truth 1.50, Δ=0.018 (tol 0.15). |
| TVB Framework web UI | PASS | Container starts in ~27 s, web UI returns HTTP 200 at `http://localhost:8888/` (host port → container port 8080). |

Side findings: PyMC prints `g++ not available` and falls back to the
pure-Python sampler. Acceptable for MVP; install `gxx`/MSVC build tools
later if NUTS speed becomes a bottleneck.

Smoke-test scripts live at `v7_architecture/foundation_logs/smoke_*.py`
and the TVB launcher is at `scripts/run_tvb.sh`.

---

## Constraints honored

- [x] Did not touch v6.0 production stack (no n8n restart, no Neo4j migration).
- [x] Did not install anything globally with sudo.
- [x] Did not commit `.env` to git (verified `.gitignore` covers `.env`, `.env.local`, `.env.*.local`).
- [x] Cost so far: **$0** (everything used so far is free tier or pre-paid).

---

## Next action

Foundation 25/25 PASS — tagged as `v7-foundation-ready`. Proceed to
v7.0 Phase 7.0 (Belief State Foundation) per
`v7_architecture/AI_BRAIN.md` section 4. The recommended path is a fresh
chat session using `v7_architecture/70_PHASES/PROMPT_FOR_VSCODE.md` as
the session prompt — but note that the v7_architecture/ docs themselves
have a known squishy-token bug, separately tracked in
`C:/Users/jinch/.claude/plans/vscode-confirm-and-plan-prompt-md-vs-squishy-token.md`.
Resolve that cleanup BEFORE handing the prompts to a new AI session.
