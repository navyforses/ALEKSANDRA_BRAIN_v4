# 00_FOUNDATION_PREREQUISITES.md — საფუძვლის გეგმა

> **მიზანი:** ერთი წინადადებით — რა ხელსაწყოები სჭირდება v7.0-ის გასაშვებად, რა უკვე გვაქვს, რა აკლია, რა თანმიმდევრობით უნდა დავაყენოთ.
>
> **თარიღი:** 2026-05-24
> **სტატუსი:** v7.0-მდე ეს ფაზა აუცილებლად დასრულდეს
> **ვადა:** 2-3 კვირა (paralel-ად v6.0 Sprint A-F-სთან)
> **ხარჯი:** $0-50 ერთჯერადი (უმეტესობა უფასოა) + $10-30 თვეში recurring

---

## ცენტრალური წერტილი

v7.0-ის 13 ახალი ტექნოლოგია ჯერ არც ერთი არ არის დაყენებული. v6.0-ის სტეკი მუშაობს (CrewAI, Neo4j, Qdrant, Claude, Supabase). მაგრამ PyMC, DoWhy, TVB Docker, react-flow, vis.js — არცერთი არ არსებობს.

ეს ფაილი არის foundation work — რომელიც უნდა გავაკეთოთ PRE v7.0 Phase 7.0 Sprint-ის დაწყებამდე.

---

## 1. ლოკალური სამუშაო გარემო (შაკოს ლეპტოპი)

| ხელსაწყო | სტატუსი | install command | დრო |
|---|---|---|---|
| Python 3.12+ | სავარაუდოდ ✅ | `python3 --version` | 0 |
| Node.js 20+ | სავარაუდოდ ✅ | `node --version` | 0 |
| Docker Desktop | სავარაუდოდ ✅ | `docker --version` | 0-30 წთ |
| VS Code + Continue.dev / Cursor | სავარაუდოდ ✅ | extension install | 5 წთ |
| Git + GitHub CLI | სავარაუდოდ ✅ | `gh --version` | 0 |
| uv (Python package manager) | ❌ ალბათ აკლია | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | 2 წთ |
| ფიქსირდი 50 GB დისკის ადგილი | შესამოწმებელია | `df -h` | n/a |
| RAM 16 GB+ | შესამოწმებელია | `free -h` ან Activity Monitor | n/a |
| GPU (M2/M3 ან NVIDIA) | M2/M3 ✅ | `system_profiler SPDisplaysDataType` | n/a |

**შემოწმების ბრძანებები:**
```bash
python3 --version    # უნდა ≥ 3.12
node --version       # უნდა ≥ 20
docker --version     # უნდა ≥ 24
df -h ~              # უნდა ≥ 50 GB free
```

---

## 2. ღრუბლის ანგარიშები

| სერვისი | სტატუსი | რა საჭიროა | ფასი |
|---|---|---|---|
| Anthropic Console | ✅ (v4.0-დან) | API key, budget alerts $80/თვე | $30-50/თვე |
| Google AI Studio | ❌ ახალია v7.0-ში | Gemini Deep Research access | უფასო (rate limit) |
| Google Cloud Console | ❌ ალბათ აკლია | Vertex AI (თუ MedGemma cloud) | $5/თვე |
| Hugging Face Hub | ✅ (v5.0-დან) | Token for MedGemma/TxGemma downloads | უფასო |
| GitHub | ✅ | already in v6.0 | უფასო |
| Railway | ✅ (v4.0-დან) | TVB Docker container | $10/თვე ნამატი |
| Vercel | ✅ | already in v6.0 | $0 (Hobby) |
| Supabase | ✅ | already in v6.0 | $0 (Free tier) |
| Neo4j AuraDB | ✅ | already in v6.0 | $0 (Free tier) |
| Cloudflare R2 | ✅ | already in v6.0 | $0 (Free tier) |
| Langfuse self-hosted | ✅ (v6.0 Sprint D) | already planned | $0 |
| AlphaFold Server | ✅ (v5.0) | Gmail account access | $0 |

**ერთჯერადი signup time:** 30-60 წუთი 2 ახალი ანგარიშისთვის (Google AI Studio + Google Cloud).

---

## 3. Python ბიბლიოთეკები (v7.0-ის backend)

ფიქსირდი v7.0-ის requirements.txt-ად:

```txt
# Bayesian core (NEW v7.0)
pymc>=5.18
numpyro>=0.16
jax[cpu]>=0.4.30   # ან jax[metal] M2/M3-ისთვის
arviz>=0.20

# Causal reasoning (NEW v7.0)
dowhy>=0.12
causalnex>=0.13
econml>=0.15

# Existing v6.0 stack (already installed)
crewai>=1.14
anthropic>=0.40
google-generativeai>=0.8
litellm>=1.50

# Schemas + safety
pydantic>=2.0
pydantic-settings>=2.0

# Data + ML
numpy>=1.26
scipy>=1.13
pandas>=2.2
scikit-learn>=1.5

# Medical AI clients
huggingface-hub>=0.25
transformers>=4.46
accelerate>=1.0

# Monitoring
langfuse>=2.50
```

**Install command:**
```bash
cd ~/projects/ALEKSANDRA_BRAIN
uv venv .venv-v7
source .venv-v7/bin/activate
uv pip install -r requirements-v7.txt
```

**ცდის ვადა:** 30-45 წუთი (download + compile).

**მოსალოდნელი დისკის ოკუპაცია:** ~3 GB Python deps.

---

## 4. Docker Images

| Image | სტატუსი | pull command | ცდის ვადა |
|---|---|---|---|
| TheVirtualBrain (TVB) | ❌ NEW | `docker pull thevirtualbrain/tvb-run:latest` | 10 წთ (~2 GB) |
| Qdrant | ✅ | already running | 0 |
| Postgres (event sourcing) | შესაძლოა ✅ | `docker pull postgres:17` | 5 წთ |
| Langfuse | სავარაუდოდ ✅ | v6.0 Sprint D | 0 |

**TVB-ის ცდის ბრძანება:**
```bash
docker pull thevirtualbrain/tvb-run:latest
docker run -d --name tvb -p 8888:8888 \
  -v ~/tvb-data:/home/jovyan/work \
  thevirtualbrain/tvb-run:latest
```

---

## 5. Frontend ბიბლიოთეკები (Next.js საიტი)

ფიქსირდი viewer/package.json-ში:

```json
{
  "dependencies": {
    "next": "^16.0",
    "react": "^19.0",
    "tailwindcss": "^4.0",
    "shadcn/ui": "latest",
    "@niivue/niivue": "^0.49",
    "@niivue/nvreact": "latest",
    "@react-three/fiber": "^9.6",
    "@react-three/drei": "^9.0",
    "three": "^0.169",

    "plotly.js-dist-min": "^2.35",      // NEW v7.0
    "react-plotly.js": "^2.6",           // NEW v7.0
    "vis-network": "^9.1",                // NEW v7.0
    "vis-data": "^7.1",                   // NEW v7.0
    "@xyflow/react": "^12.0",             // react-flow NEW v7.0

    "ai": "^5.0",
    "next-intl": "^4.12",
    "swr": "^2.2"
  }
}
```

**Install command:**
```bash
cd viewer/
npm install plotly.js-dist-min react-plotly.js vis-network vis-data @xyflow/react
```

**ცდის ვადა:** 5-10 წთ.

**მოსალოდნელი ცვლა:** ~50 MB node_modules ნამატი.

---

## 6. AI მოდელების downloads (Hugging Face)

| მოდელი | ზომა | download command | დისკი |
|---|---|---|---|
| MedGemma 4B (local) | ~8 GB | `huggingface-cli download google/medgemma-4b-it` | 8 GB |
| MedGemma 27B (cloud only) | n/a | HF Inference Endpoint | 0 |
| TxGemma 9B | ~18 GB | `huggingface-cli download google/txgemma-9b-chat` | 18 GB |
| TxGemma 27B (cloud only) | n/a | HF Inference Endpoint | 0 |
| MedSigLIP encoder | ~2 GB | `huggingface-cli download google/medsiglip-448` | 2 GB |
| BIBSnet weights | ~500 MB | already in v6.0 | 0 |
| FastSurfer-LIT weights | ~1 GB | already in v6.0 | 0 |
| MedSAM2 (optional) | ~2 GB | `huggingface-cli download wanglab/medsam2` | 2 GB |
| HF datasets (otter, drug-target, BONBID-HIE) | ~500 MB | already in v6.0 | 0 |

**ჯამური დისკი:** ~30 GB AI მოდელებისთვის.

**ცდის ვადა:** 1-2 საათი (broadband).

**Setup command:**
```bash
huggingface-cli login
huggingface-cli download google/medgemma-4b-it --local-dir ~/models/medgemma-4b
huggingface-cli download google/txgemma-9b-chat --local-dir ~/models/txgemma-9b
huggingface-cli download google/medsiglip-448 --local-dir ~/models/medsiglip
```

---

## 7. API Keys და Secrets

ფიქსირდი .env.local ფაილში (NE commit-დე git-ში!):

```bash
# Anthropic (v4.0-დან)
ANTHROPIC_API_KEY=sk-ant-...

# Google AI Studio (NEW v7.0)
GOOGLE_AI_STUDIO_KEY=...
GEMINI_API_KEY=...

# Google Cloud (NEW v7.0, optional)
GCP_PROJECT_ID=...
GCP_SERVICE_ACCOUNT_KEY=path/to/key.json

# Hugging Face (v5.0-დან)
HF_TOKEN=hf_...

# Supabase (v4.0-დან)
SUPABASE_URL=https://...supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_ANON_KEY=eyJ...

# Neo4j Aura (v4.0-დან)
NEO4J_URI=neo4j+s://...
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...

# Cloudflare R2 (v4.0-დან)
R2_ACCOUNT_ID=...
R2_ACCESS_KEY=...
R2_SECRET_KEY=...

# Langfuse (v6.0-დან)
LANGFUSE_SECRET_KEY=...
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_HOST=http://localhost:3000

# v7.0 NEW: TVB
TVB_DOCKER_URL=http://localhost:8888

# v7.0 NEW: Telegram for active questions
TELEGRAM_BOT_TOKEN=... (already v4.0)
TELEGRAM_WIFE_CHAT_ID=...
```

**კონსტიტუციური წესი:** .env.local arasodes commit-დე git-ში. გამოიყენე .env.example template-ად.

---

## 8. MCP Servers (Claude Code / Cursor-ში)

რომელი MCP-ები გჭირდება v7.0 sessions-ისთვის:

| MCP | სტატუსი | install ბრძანება |
|---|---|---|
| healthcare (PubMed, ClinicalTrials) | ✅ | already in Claude Code |
| github | ✅ | already in Claude Code |
| brave-search | ✅ | already in Claude Code |
| workspace (bash) | ✅ | already in Cowork |
| firecrawl | ✅ | already in v6.0 |
| code-review-graph | ✅ | already in v6.0 |
| visualize (diagrams) | ✅ | already in Claude Code |
| serena (code intelligence) | ✅ | already in Claude Code |
| aipulsegeorgia (custom) | ✅ | already in v6.0 |

შენიშვნა: ვერ გვჭირდება ახალი MCP-ები. v7.0-ის სამუშაო კოვერდდება v6.0-ში არსებული MCP-ებით.

---

## 9. CLI ხელსაწყოები

| ხელსაწყო | სტატუსი | install | დანიშნულება |
|---|---|---|---|
| rclone | სავარაუდოდ ✅ | `brew install rclone` | R2 file sync |
| ffmpeg | სავარაუდოდ ✅ | `brew install ffmpeg` | voice processing |
| imagemagick | სავარაუდოდ ✅ | `brew install imagemagick` | image manipulation |
| jq | სავარაუდოდ ✅ | `brew install jq` | JSON parsing in shell |
| yq | ალბათ ❌ | `brew install yq` | YAML parsing |
| litecli | NEW | `pip install litecli` | SQLite ცდისთვის |

---

## 10. Hardware მოთხოვნები

| რესურსი | მინიმუმი | რეკომენდაცია | შაკოს M2/M3 ლეპტოპი |
|---|---|---|---|
| RAM | 16 GB | 32 GB | სავარაუდოდ ✅ |
| GPU VRAM | n/a (CPU OK) | 8 GB+ (NVIDIA ან Metal) | ✅ (M2/M3 Metal) |
| დისკი თავისუფალი | 50 GB | 100 GB | შესამოწმებელია |
| Internet | 10 Mbps | 100 Mbps download | სავარაუდოდ ✅ |

**ერთჯერადი ცდის დრო (foundation setup):** ~5-8 საათი ჯამში.

---

## 11. Install Order (კრიტიკული თანმიმდევრობა)

```
ფაზა 0: Verify existing (30 წთ)
├─ python3 --version, node --version, docker --version
├─ existing .env.local keys-ის ცდა
└─ existing Docker containers status

ფაზა 1: New cloud accounts (1-2 საათი)
├─ Google AI Studio signup → GEMINI_API_KEY
├─ (optional) Google Cloud signup → GCP credentials
└─ Anthropic budget alerts $80/თვე

ფაზა 2: Local tools install (1-2 საათი)
├─ uv install (Python package manager)
├─ create .venv-v7 virtual environment
├─ install Python deps (PyMC, DoWhy, NumPyro, etc.)
└─ verify imports work (pytest fixture)

ფაზა 3: Docker images (30 წთ)
├─ docker pull thevirtualbrain/tvb-run:latest
├─ docker pull postgres:17 (if needed)
└─ test TVB container starts

ფაზა 4: Frontend libraries (15 წთ)
├─ cd viewer/
├─ npm install plotly.js vis-network @xyflow/react
└─ npm run dev (verify no errors)

ფაზა 5: AI model downloads (1-2 საათი)
├─ huggingface-cli login
├─ download MedGemma 4B
├─ download TxGemma 9B
├─ download MedSigLIP encoder
└─ verify models load

ფაზა 6: Verification (1 საათი)
├─ run scripts/verify_v7_foundation.py
├─ check 25 items
└─ document any failures
```

**ჯამური ცდის დრო:** 5-8 საათი ჯამში 6 ფაზაში.

---

## 12. Verification Script

შესაქმნელია `scripts/verify_v7_foundation.py`:

```python
#!/usr/bin/env python3
"""v7.0 Foundation Prerequisites Verifier."""
import subprocess, sys, importlib.util, os

CHECKS = {
    "python_3_12_plus": lambda: sys.version_info >= (3, 12),
    "node_20_plus": lambda: int(subprocess.check_output(["node", "--version"]).decode().lstrip("v").split(".")[0]) >= 20,
    "docker_installed": lambda: subprocess.run(["docker", "--version"], capture_output=True).returncode == 0,
    "pymc_importable": lambda: importlib.util.find_spec("pymc") is not None,
    "numpyro_importable": lambda: importlib.util.find_spec("numpyro") is not None,
    "dowhy_importable": lambda: importlib.util.find_spec("dowhy") is not None,
    "anthropic_key_set": lambda: bool(os.getenv("ANTHROPIC_API_KEY")),
    "gemini_key_set": lambda: bool(os.getenv("GEMINI_API_KEY")),
    "hf_token_set": lambda: bool(os.getenv("HF_TOKEN")),
    "medgemma_4b_downloaded": lambda: os.path.exists(os.path.expanduser("~/models/medgemma-4b")),
    "txgemma_9b_downloaded": lambda: os.path.exists(os.path.expanduser("~/models/txgemma-9b")),
    "medsiglip_downloaded": lambda: os.path.exists(os.path.expanduser("~/models/medsiglip")),
    "tvb_docker_running": lambda: "tvb" in subprocess.check_output(["docker", "ps"]).decode(),
    "supabase_url_set": lambda: bool(os.getenv("SUPABASE_URL")),
    "neo4j_uri_set": lambda: bool(os.getenv("NEO4J_URI")),
    # ... 10 more checks
}

passed = sum(1 for check in CHECKS.values() if check())
total = len(CHECKS)
print(f"v7.0 Foundation: {passed}/{total} passed")
sys.exit(0 if passed == total else 1)
```

**წარმატების კრიტერიუმი:** 25/25 PASS.

---

## 13. ხარჯის Summary

| კატეგორია | ერთჯერადი | recurring/თვე |
|---|---|---|
| ლოკალური tools | $0 | $0 |
| Cloud accounts signup | $0 | $0 |
| Python deps install | $0 | $0 |
| Docker pulls | $0 | $0 |
| Frontend npm install | $0 | $0 |
| AI model downloads | $0 | $0 |
| Google AI Studio | $0 | $0-5 |
| Google Cloud (optional) | $0 | $5-15 |
| Anthropic increased usage | $0 | +$20-30 |
| TVB Docker on Railway | $0 | +$10 |
| ჯამი | $0 | +$30-50 |

**Foundation setup cost:** $0 ერთჯერადი (ყველაფერი უფასოა).
**v7.0 recurring nameat:** +$30-50/თვე v6.0-ის $60-დან, ჯამში $80-110/თვე.

---

## 14. რისკები Foundation-ში

| რისკი | ალბათობა | mitigation |
|---|---|---|
| Disk სავსეა (>50 GB models) | Medium | external SSD ან models on cloud |
| RAM არ ჰყოფნის MedGemma 4B-ისთვის | Low | quantize to 8-bit, ან cloud-ში |
| GPU არ მუშაობს JAX-ით M-სერიაზე | Medium | jax[metal] backend, fallback CPU |
| Google AI Studio quota exceeded | Low | rate limit handling, fallback Anthropic |
| TVB Docker container crashes | Medium | restart policy, healthcheck |
| Hugging Face download fails | Low | retry, mirror, ლოკალური cache |
| Python deps version conflicts | High | uv pinning, lock file, virtual env |

---

## 15. Sequential Action Plan

შაკოს დასაწყისის სია (ერთი წინადადებიანი):

1. გადააიხადე ლეპტოპის disk free space ≥ 50 GB
2. გადააიხადე RAM ≥ 16 GB
3. შექმენი Google AI Studio account
4. გადააიხადე Anthropic budget alerts $80/თვე
5. install uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
6. create venv `uv venv .venv-v7`
7. install Python deps `uv pip install -r requirements-v7.txt`
8. docker pull TVB image
9. npm install frontend libs
10. download AI models (MedGemma 4B, TxGemma 9B, MedSigLIP)
11. configure .env.local with all keys
12. run `python scripts/verify_v7_foundation.py`
13. fix any failures
14. commit `requirements-v7.txt`, `viewer/package.json` to git
15. tag commit as `v7-foundation-ready`

---

## 16. შემდეგი ფაზა

Foundation-ის დასრულების შემდეგ:
- v7.0 Phase 7.0 (Belief State Foundation) გადადგა
- ცალკეულ ჩატში გადააცი 70_PHASES/PROMPT_FOR_VSCODE.md
- Phase 7.0 ვადა: 4 კვირა

შენიშვნა: Foundation არ ჩაითვლება Phase 7.0-ში. ეს არის Phase 0 / "v7.0 prereq sprint" (2-3 კვირა).

---

## წყაროები

- [PyMC installation](https://www.pymc.io/projects/docs/en/stable/installation.html)
- [NumPyro JAX install](https://num.pyro.ai/en/latest/getting_started.html)
- [DoWhy quickstart](https://www.pywhy.org/dowhy/main/getting_started/intro.html)
- [TVB Docker Hub](https://hub.docker.com/r/thevirtualbrain/tvb-run)
- [MedGemma Hugging Face](https://huggingface.co/google/medgemma-4b-it)
- [TxGemma Hugging Face](https://huggingface.co/google/txgemma-9b-chat)
- [uv documentation](https://docs.astral.sh/uv/)
- [Plotly.js docs](https://plotly.com/javascript/)
- [vis.js network docs](https://visjs.github.io/vis-network/docs/network/)
- [react-flow / xyflow](https://reactflow.dev/)

---

## ვერსიის შენიშვნა

ეს არის Foundation v1.0. შესაძლოა გაიზარდოს Phase 0-ის გასვლის შემდეგ. cost projections შესაძლოა შეიცვალოს Google AI Studio quota-ისა და Anthropic-ის ფასების ცვლილების მიხედვით.

ნუ ცდი v7.0 Phase 7.0-ის დაწყებას Foundation 25/25 PASS-ის გარეშე.
