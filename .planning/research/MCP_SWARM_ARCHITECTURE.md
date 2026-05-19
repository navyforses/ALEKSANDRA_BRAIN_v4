# MCP Swarm Architecture — ALEKSANDRA_BRAIN Neuroimaging Division

**Version:** 1.0
**Date:** 2026-05-16
**Scope:** v2 Visualization Phase (VIS-* requirements)
**MCP Server:** `aleksandra_niivue_mcp.py` (FastMCP-based)
**Target Scale:** 200–500 autonomous agents across 8 competency teams

---

## 1. Executive Summary

ეს დოკუმენტი განსაზღვრავს `aleksandra-niivue-mcp` სერვერის არქიტექტურას, რომელიც ალექსანდრას ტვინის MRI/CT მონაცემების დამუშავებისთვის იქმნება. სისტემა იყენებს **MapReduce + Micro-Agent Swarm** მიდგომას, სადაც ტვინის 3D მოცულობა (16M+ ვოქსელი) ჭრება პატარა chunk-ებად და ასეულობით AI აგენტი პარალელურად ამუშავებს.

**ღირებულების შეთავაზება:** ოჯახს ექნება რეალურ დროში განახლებადი 3D ტვინის მოდელი, სეგმენტაცია, ლეზიების დეტექცია და კლინიკოსებისთვის გასაზიარებელი PDF/HTML — ყველაფერი ლოკალურად, HIPAA-თან შესაბამისად.

---

## 2. MCP Server Core Architecture

### 2.1 Server Stack

| ფენა | ტექნოლოგია | მიზანი |
|------|-----------|--------|
| MCP Framework | FastMCP (Python) | Tool decorators, JSON-RPC, stdio/sse transport |
| Neuroimaging | nibabel + numpy | NIfTI I/O, affine transforms, voxel math |
| 3D Processing | scipy.ndimage, scikit-image | Filtering, morphology, feature extraction |
| Segmentation | FastSurfer-LIT, BONBID-HIE, BIBSnet | Anatomical / lesion segmentation |
| Mesh/GLB | nii2mesh, pyvista, trimesh | Surface extraction, decimation, export |
| Viewer Data | niivue-core (WASM prep) | Client-side WebGL volume rendering |
| Orchestration | Redis Streams + Celery | Agent task queue, result aggregation |
| Storage | Local disk + Prism MCP (HIPAA) | No cloud PHI; local-only with Prism audit |

### 2.2 Tool Inventory (aleksandra-niivue-mcp)

```
┌─────────────────────────────────────┐
│  aleksandra-niivue-mcp              │
├─────────────────────────────────────┤
│  🔧 load_nifti(file_path)           │  ← რეალური nibabel (გაკეთებული)
│  🔧 segment(file_path, model_type)  │  ← FastSurfer / BONBID-HIE / BIBSnet
│  🔧 export_mesh(nifti_path, out)    │  ← nii2mesh → .glb / .obj
│  🔧 family_html(mesh_path, out)     │  ← ქართულად, offline HTML
│  🔧 build_voxel_network(file_path)  │  ← NetworkX 3D graph + tractography
│  🔧 distribute_brain_processing()   │  ← MapReduce chunking (გაკეთებული)
│  🔧 plan_brain_swarm_architecture() │  ← არქიტექტურის დაგეგმვა
└─────────────────────────────────────┘
```

### 2.3 Data Flow (High Level)

```
[DICOM/NIfTI source]
        ↓
[Team Alpha: Ingestion] → validate, normalize, reorient
        ↓
[Team Beta: MapReduce Coordinator] → split into 10×10×10 chunks
        ↓
[Team Gamma: Chunk Workers × 100-300] → parallel processing
        ↓
[Team Delta: Reducers] → aggregate, merge, build surfaces
        ↓
[Team Epsilon: Segmentation QA] → validate masks, compute volumes
        ↓
[Team Zeta: Visualization] → NiiVue scenes, HTML export, 3D print
        ↓
[Family View] + [Clinician PDF]
```

---

## 3. Agent Swarm Topology

### 3.1 Swarm Design Principles

1. **Chunk-Parallelism:** თითოეული 10×10×10 ვოქსელის chunk ერთ აგენტს ეკუთვნის. 256×256×256 ტვინისთვის ≈ 17,000 chunk.
2. **Round-Robin Distribution:** chunk-ები თანაბრად ნაწილდება აგენტებზე, რათა არავინ იყოს overloaded.
3. **Idempotency:** თითოეული აგენტის გაშვება idempotent-ია — თუ ჩავარდა, თავიდან იშვება იმავე input-ით.
4. **Local-Only PHI:** MRI data არასოდეს არ ტოვებს ლოკალურ მანქანას. აგენტები მუშაობენ ლოკალურ Docker-ში ან Python process-ში.
5. **Kill-Switch Integration:** `panic_stop` MCP ყოველთვის შეუძლია swarm-ის გაჩერება 60 წამში.

### 3.2 Agent Identity Model

თითოეულ აგენტს აქვს:

```json
{
  "agent_id": "beta-worker-0427",
  "team": "beta-chunk-workers",
  "competency": "voxel_intensity_analysis",
  "mcp_servers": ["aleksandra-niivue-mcp", "prism-mcp"],
  "chunk_assignment": {
    "chunk_ids": [4270, 4271, 4272, ...],
    "coords": {"x": [120,130], "y": [80,90], "z": [40,50]}
  },
  "max_runtime_sec": 30,
  "max_tokens": 8000,
  "memory_scope": "chunk-local-only"
}
```

---

## 4. Competency Teams (8 Teams, 200–500 Agents)

### Team Alpha: NIfTI Ingestion & Preprocessing (α)
**ზომა:** 20–50 აგენტი
**MCP:** `aleksandra-niivue-mcp` (load_nifti), `prism-mcp`
**მიზანი:** ფაილების ჩატვირთვა, ვალიდაცია, ნორმალიზაცია

| როლი | რაოდენობა | აღწერა |
|------|----------|--------|
| α-1 NIfTI Loader | 5–10 | ტვირთავს .nii/.nii.gz ფაილებს nibabel-ით |
| α-2 Header Validator | 3–5 | ამოწმებს affine, dim, zooms, qform/sform |
| α-3 Orientation Normalizer | 3–5 | RAS+ orientation, reorient to canonical |
| α-4 Intensity Normalizer | 5–10 | Z-score, histogram matching, N4 bias correction |
| α-5 Quality Control | 3–5 | Motion artifacts, signal dropout, ghosting detection |
| α-6 DICOM Converter | 1–3 | dcm2niix wrapper for raw DICOM → NIfTI |
| α-7 Metadata Enricher | 1–3 | Extracts scanner info, TE/TR, patient age at scan |

**Key Tool:** `load_nifti()` — აბრუნებს dim, voxel_size, affine, dtype, data_range, total_voxels

---

### Team Beta: MapReduce Chunk Processing (β)
**ზომა:** 100–300 აგენტი (swarm core)
**MCP:** `aleksandra-niivue-mcp` (distribute_brain_processing)
**მიზანი:** 3D მოცულობის დაჭრა და პარალელური დამუშავება

#### β-0 MapReduce Coordinator (1 აგენტი)
- იღებს NIfTI ფაილს და `num_agents`-ს
- იძახებს `distribute_brain_processing(file_path, num_agents, chunk_size=10)`
- აგენერირებს chunk manifest-ს (JSON)
- ანაწილებს chunk-ებს worker აგენტებზე round-robin-ით
- აკონტროლებს REDUCE ფაზას

#### β-1 Chunk Mappers (5–10 აგენტი)
- ამზადებენ chunk-ების სიას
- ათვლიან chunk overlap-ს (border voxels for continuity)
- ქმნიან chunk metadata: shape, coords, voxel count, boundary flags

#### β-2 Chunk Worker Agents (100–250 აგენტი)
**ეს არის swarm-ის გული.** თითოეული worker:
- იღებს 1–N chunk-ს (round-robin assignment)
- ამუშავებს თავის chunk-ებს:
  - Voxel intensity statistics (mean, std, min, max)
  - Local gradient magnitude
  - Texture features (GLCM, Haralick)
  - Edge detection (Sobel, Canny in 3D)
  - Anomaly detection (outlier voxels vs. atlas)
- აბრუნებს შედეგს JSON-ად
- **არასოდეს არ ინახავს** მთელ ტვინს — მხოლოდ თავის chunk

#### β-3 Chunk Reducers (5–10 აგენტი)
- აგრეგირებენ worker-ების შედეგებს
- აერთიანებენ intensity maps
- აგვირგვინებენ გრადიენტებს
- აგენერირებენ global statistics

#### β-4 Boundary Merger Agents (3–5 აგენტი)
- აგვარებენ chunk-ებს შორის საზღვრების (border) პრობლემებს
- Gaussian blending on overlapping regions
- Seamless volume reconstruction

**Key Tool:** `distribute_brain_processing()` — chunking + distribution + agent load preview

---

### Team Gamma: Segmentation Pipeline (γ)
**ზომა:** 30–50 აგენტი
**MCP:** `aleksandra-niivue-mcp` (segment), `bonbid-mcp`
**მიზანი:** ტვინის სტრუქტურების ავტომატური გამოყოფა

| როლი | რაოდენობა | აღწერა |
|------|----------|--------|
| γ-1 FastSurfer Agent | 5–10 | Cortical surface segmentation (pial, white matter) |
| γ-2 BONBID-HIE Agent | 5–10 | HIE lesion segmentation (cystic encephalomalacia) |
| γ-3 BIBSnet Agent | 5–10 | Infant brain tissue classes (WM, GM, CSF) |
| γ-4 Lesion Detector | 5–10 | Cyst detection, volume, location, count |
| γ-5 Atlas Registration | 3–5 | MNI152 neonatal atlas alignment |
| γ-6 Segmentation QA | 5–10 | Dice overlap check, manual vs. auto comparison |
| γ-7 Volume Calculator | 3–5 | Brain region volumes, asymmetry indices |

**Key Tool:** `segment(file_path, model_type)` — dispatches to correct segmentation engine

---

### Team Delta: 3D Mesh & Visualization (δ)
**ზომა:** 20–40 აგენტი
**MCP:** `aleksandra-niivue-mcp` (export_mesh, family_html)
**მიზანი:** 3D მოდელების ექსპორტი და ოჯახისთვის ვიზუალიზაცია

| როლი | რაოდენობა | აღწერა |
|------|----------|--------|
| δ-1 Surface Extractor | 5–10 | Marching cubes → .obj/.glb from segmentation masks |
| δ-2 Mesh Optimizer | 3–5 | Decimation, smoothing, normal computation |
| δ-3 NiiVue Preparer | 3–5 | Volume data → NiiVue-compatible JSON/blobs |
| δ-4 R3F Scene Builder | 3–5 | React Three Fiber scene composition |
| δ-5 Family HTML Generator | 3–5 | Offline HTML with Georgian labels, no external deps |
| δ-6 Color Mapper | 3–5 | Lesion heatmaps, probability maps → vertex colors |
| δ-7 3D Print Exporter | 1–3 | STL export for physical model printing |

**Key Tools:** `export_mesh()`, `family_html()`

---

### Team Epsilon: Voxel Network & Graph Analysis (ε)
**ზომა:** 15–25 აგენტი
**MCP:** `aleksandra-niivue-mcp` (build_voxel_network)
**მიზანი:** ტვინის გრაფული მოდელი და ტრაქტოგრაფია

| როლი | რაოდენობა | აღწერა |
|------|----------|--------|
| ε-1 Graph Builder | 3–5 | Voxel → node, 26-neighbor → edge, NetworkX |
| ε-2 Tractography Agent | 3–5 | DTI-based fiber tracking (if DTI available) |
| ε-3 Connectivity Mapper | 3–5 | Structural connectivity matrix |
| ε-4 Path Analyzer | 3–5 | Shortest paths, betweenness centrality per region |
| ε-5 Graph Exporter | 3–5 | GEXF, GraphML for Gephi / Neo4j import |

**Key Tool:** `build_voxel_network()` — 3D voxel graph with network stats

---

### Team Zeta: Quality Assurance & Safety (ζ)
**ზომა:** 15–25 აგენტი
**MCP:** `panic_stop`, `hello_brain`, `prism-mcp`
**მიზანი:** ყველაფრის ვალიდაცია და უსაფრთხოება

| როლი | რაოდენობა | აღწერა |
|------|----------|--------|
| ζ-1 Citation Verifier | 3–5 | ყველა სამედიცინო claim-ის წყაროს შემოწმება |
| ζ-2 Fabrication Detector | 3–5 | სინთეზირებული შედეგების პოვნა (≥99% rejection) |
| ζ-3 Tone Checker | 3–5 | Imperative verb lint, prognostic language filter |
| ζ-4 Privacy Auditor | 3–5 | ამოწმებს რომ PHI არ გადის ლოკალურ მანქანას |
| ζ-5 Budget Gate | 3–5 | $1.50/day spend cap enforcement |

---

### Team Eta: Infrastructure & Orchestration (η)
**ზომა:** 10–20 აგენტი
**MCP:** `hello_brain`, `panic_stop`
**მიზანი:** სისტემის მუშაობა და მასშტაბირება

| როლი | რაოდენობა | აღწერა |
|------|----------|--------|
| η-1 Load Balancer | 3–5 | Celery worker scaling, queue depth monitoring |
| η-2 Health Monitor | 3–5 | Neo4j, Qdrant, Supabase, Redis connectivity checks |
| η-3 Error Recovery | 3–5 | Failed chunk retry, dead-letter queue |
| η-4 Run Ledger | 1–3 | Every agent run → Supabase `runs` table |

---

### Team Theta: Family Communication (θ)
**ზომა:** 10–20 აგენტი
**MCP:** Communicator tools, Telegram, Gmail MCP
**მიზანი:** შედეგების ოჯახისთვის მიწოდება

| როლი | რაოდენობა | აღწერა |
|------|----------|--------|
| θ-1 Digest Compiler | 3–5 | ყოველდღიური/ყოველკვირეული შეჯამება |
| θ-2 Georgian Translator | 3–5 | ქართულად თარგმნა ოჯახისთვის |
| θ-3 Telegram Formatter | 3–5 | Telegram message formatting, quiet hours respect |
| θ-4 Clinician PDF Generator | 3–5 | PDF with full provenance, citations, agent run IDs |
| θ-5 Notion Archivist | 3–5 | Notion page append with structured findings |

---

## 5. Swarm Execution Model

### 5.1 MapReduce Workflow (Detailed)

```
Phase: MAP
──────────
Coordinator (β-0) calls load_nifti(file_path)
  → Gets shape [256, 256, 256], dtype float64, total_voxels 16,777,216

Coordinator calls distribute_brain_processing(file_path, num_agents=500, chunk_size=10)
  → Generates 16,777 chunks (ceil(256/10)³ = 26³)
  → Assigns chunk_ids round-robin to 500 agents
  → Each agent gets ~33-34 chunks

Phase: PROCESS (parallel)
─────────────────────────
For each agent in parallel (max 500 concurrent):
  For each assigned chunk:
    1. Extract chunk data: data[x0:x1, y0:y1, z0:z1]
    2. Compute local statistics
    3. Run anomaly detection vs. neonatal atlas
    4. Detect lesions (if intensity pattern matches cyst)
    5. Return: {chunk_id, stats, anomalies, lesions, gradient}

Phase: REDUCE
─────────────
Reducer agents (β-3) collect all chunk results:
  1. Merge intensity maps into full volume
  2. Merge lesion masks
  3. Compute global statistics
  4. Generate full-volume report

Boundary Merger (β-4):
  1. Blend overlapping regions
  2. Smooth seams
  3. Validate continuity at chunk borders
```

### 5.2 Agent Lifecycle

```
[Spawn] → [Load MCP Allowlist] → [Receive Chunk Assignment]
   ↓
[Process Chunks] → [Return Results] → [Self-Terminate or Sleep]
   ↓
If failed → [Retry × 3] → [Dead Letter Queue] → [η-3 Error Recovery]
```

### 5.3 Communication Patterns

| Pattern | გამოყენება | ტექნოლოგია |
|---------|-----------|-----------|
| Request-Reply | Coordinator → Worker chunk assignment | Redis RPUSH / BLPOP |
| Pub-Sub | Kill-switch broadcast (panic_stop) | Redis PUBLISH |
| Stream | Real-time progress updates to family | Redis Streams |
| Direct Call | MCP tool invocation | FastMCP JSON-RPC |

---

## 6. Privacy & Security Architecture

### 6.1 PHI Handling Rules

| წესი | რეალიზაცია |
|------|-----------|
| MRI data never leaves local machine | All agents run in local Docker; no cloud storage of NIfTI |
| Prism MCP audit | Every file access logged to Prism (HIPAA-hardened) |
| No network from viewer | family_html is fully offline; no CDN, no external fetch |
| Agent memory isolation | Each agent only sees its assigned chunks |
| kill-switch always reachable | `panic_stop` terminates all workers within 60s |

### 6.2 Agent Permission Matrix

| Team | load_nifti | segment | export_mesh | distribute | panic_stop | prism |
|------|:----------:|:-------:|:-----------:|:----------:|:----------:|:-----:|
| Alpha (Ingestion) | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Beta (Chunk) | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ |
| Gamma (Segment) | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Delta (Viz) | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Epsilon (Graph) | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Zeta (QA) | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Eta (Infra) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Theta (Comm) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 7. Scaling Strategy

### 7.1 Chunk Size Tuning

| ტვინის ზომა | Chunk Size | Chunk-ების რაოდენობა | Agents | მეხსიერება/agent |
|------------|:----------:|:--------------------:|:------:|:----------------:|
| 128³ | 10×10×10 | ~2,100 | 100 | ~8 KB |
| 256³ | 10×10×10 | ~17,000 | 500 | ~8 KB |
| 512³ | 10×10×10 | ~140,000 | 1000 | ~8 KB |
| 256³ | 20×20×20 | ~2,200 | 100 | ~64 KB |

### 7.2 Dynamic Scaling

- **Queue depth > 1000:** Auto-scale +50 workers
- **Queue depth < 100:** Scale down -25 workers
- **Memory per worker > 500MB:** Reduce chunk size
- **CPU idle > 60%:** Increase concurrency

---

## 8. Implementation Roadmap

### Swarm Phase 1: Foundation (2 weeks)
- [ ] Chunk coordinator implementation (`distribute_brain_processing` finalize)
- [ ] Redis + Celery task queue setup
- [ ] Team Alpha: NIfTI loader agents (5 agents)
- [ ] Team Beta: 10 chunk worker agents (pilot)
- [ ] Team Zeta: Privacy auditor + budget gate

### Swarm Phase 2: Scale (2 weeks)
- [ ] Team Beta: Scale to 100 workers
- [ ] Team Gamma: FastSurfer + BONBID-HIE integration
- [ ] Team Delta: Mesh export pipeline
- [ ] Team Eta: Auto-scaling + health monitoring

### Swarm Phase 3: Full Swarm (2 weeks)
- [ ] Team Beta: 300 workers, full MapReduce
- [ ] Team Gamma: Full segmentation QA pipeline
- [ ] Team Delta: Family HTML viewer (offline)
- [ ] Team Theta: Digest → Telegram → PDF pipeline
- [ ] End-to-end test: DICOM → NIfTI → Chunks → Segments → HTML

### Swarm Phase 4: Hardening (1 week)
- [ ] Load test: 500 concurrent agents
- [ ] Kill-switch stress test: < 60s termination
- [ ] PHI leak audit: Prism MCP verification
- [ ] Cost audit: <$30/month at full load

---

## 9. Success Criteria

1. **Functional:** 256³ NIfTI file processes through 500 agents in < 5 minutes on a 16-core machine.
2. **Accuracy:** Segmentation Dice overlap ≥ 0.85 vs. manual expert annotation (if available).
3. **Privacy:** Zero NIfTI bytes transmitted over network (verified by packet capture).
4. **Safety:** `panic_stop` terminates all 500 agents within 60 seconds.
5. **Family Value:** Family receives offline HTML viewer with Georgian labels within 30 seconds of segmentation completion.
6. **Clinician Value:** PDF digest contains full citation tuples, agent run IDs, and is verifiable by Dr. Hien.

---

## 10. Dependencies

### Python Packages
```
nibabel>=5.0
numpy>=1.24
scipy>=1.10
scikit-image>=0.20
pyvista>=0.40
trimesh>=3.20
networkx>=3.0
redis>=5.0
celery>=5.3
fastmcp>=0.4
httpx>=0.25
```

### External Tools (Docker)
- FastSurfer-LIT (GPU optional)
- BONBID-HIE (Docker container)
- BIBSnet (Docker container)
- dcm2niix (DICOM converter)
- nii2mesh (surface extraction)

### Infrastructure
- Redis (task queue + pub-sub)
- Local filesystem (NIfTI storage)
- Prism MCP (HIPAA audit log)

---

*შედგენილი: 2026-05-16*
*შემდეგი ნაბიჯი: Swarm Phase 1 — Chunk coordinator + Celery task queue*
