# Phase 0.1 — Environment Check Log

**Date:** 2026-05-24
**Host:** Windows 11 Home (10.0.26200), PowerShell + Git Bash
**Project root:** `c:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane`

---

## Results

| Check | Required | Found | Status |
|---|---|---|---|
| Python | >= 3.12 | 3.12.13 (`python`) + 3.14.3 (`python3`) | PASS |
| Node.js | >= 20 | v24.15.0 | PASS |
| npm | bundled | 11.12.1 | PASS |
| Docker (binary) | >= 24 | 29.4.3 | PASS |
| Docker daemon | running | **NOT RUNNING** (pipe missing) | FAIL |
| uv | latest | 0.11.8 (2026-04-27) | PASS |
| gh CLI | any | 2.92.0 | PASS |
| git | any | 2.53.0.windows.3 | PASS |
| Hugging Face CLI | `hf` (new) | 1.14.0 installed; not logged in | PARTIAL |
| Disk C: free | >= 50 GB | 194.39 GB free / 475.58 GB total | PASS |
| RAM total | >= 16 GB | 15.66 GB | **MARGINAL** (0.34 GB short) |
| RAM free (now) | n/a | 2.53 GB | TIGHT |
| GPU | any (8 GB+ recommended) | Intel Arc 130V (8 GB) | PASS-INTEGRATED |
| `.env` | present | 10,649 bytes (v6.0 keys) | PASS |
| `.env.example` | template | 7,637 bytes | PASS |
| `.gitignore` covers `.env*` | yes | `.env`, `.env.local`, `.env.*.local`, `venv/`, `.venv/` | PASS |
| Existing `.venv` | n/a | present (v6.0) | INFO |
| Existing `requirements.txt` | n/a | present (v6.0) | INFO |
| `viewer/package.json` | present | yes | PASS |

---

## Blockers / Warnings

1. **Docker daemon offline.** `docker ps` errors with `npipe:////./pipe/dockerDesktopLinuxEngine ... cannot find the file`. Docker Desktop must be started before Phase 0.4 (TVB pull).
2. **RAM = 15.66 GB.** Below the 16 GB minimum threshold from `00_FOUNDATION_PREREQUISITES.md` section 10. MedGemma 4B (8 GB model weights + overhead) may swap. TxGemma 9B (18 GB) will not fit in RAM at all — must run quantized or cloud-only.
3. **GPU = Intel Arc 130V integrated.** JAX has no Metal backend on Windows and no CUDA. Must install `jax[cpu]`, not `jax[metal]`. Bayesian inference (PyMC + NumPyro) will be CPU-bound — slower but functional.
4. **`hf` CLI not logged in.** Need `hf auth login` with HF_TOKEN before Phase 0.6 (model downloads).
5. **Filename is `.env` not `.env.local`.** Foundation doc references `.env.local`; project actually uses `.env`. Will write new v7.0 keys to `.env` to match existing convention.

---

## What passes silently (no action)

- `python`, `node`, `npm`, `uv`, `gh`, `git` all installed and ahead of minimum versions.
- Disk has 194 GB free — comfortably above the 50 GB requirement plus 30 GB AI models + 3 GB Python deps.
- `.gitignore` already protects secrets correctly.

---

## Conclusion

Phase 0.1: **15 PASS / 1 FAIL (Docker daemon) / 4 WARN (RAM, GPU type, hf-login, env-filename)**.

Can proceed to Phase 0.2 without unblocking Docker (Docker only needed at Phase 0.4). RAM ceiling and GPU type are hardware realities — adapt install plan: use `jax[cpu]`, defer TxGemma 9B local download (cloud-only via HF Inference Endpoint), keep MedGemma 4B local but expect slow inference.
