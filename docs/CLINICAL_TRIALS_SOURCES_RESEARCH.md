# Clinical-Trial Sources — Beyond ClinicalTrials.gov (Perception Layer Expansion)

**Researched:** 2026-06-15
**Domain:** Multi-registry clinical-trial ingestion for ALEKSANDRA_BRAIN PERCEPTION layer
**Confidence:** HIGH (every external API claim below was hit with a real request — curl or WebFetch — and the HTTP status + response sample are recorded)

> Core Value alignment: "never miss a sound treatment lead for Aleksandra." Adding EU + UK
> registries directly closes a real gap — the single best HIE lead found during this research
> (UCL's **ACUMEN** IV-melatonin Phase I in HIE babies) lives in **CTIS / ISRCTN**, and is
> **not** a US ClinicalTrials.gov record. We were missing it.

---

## Summary

ClinicalTrials.gov is US-centric. The trials Aleksandra could realistically reach (HIE /
neonatal encephalopathy / infantile spasms / cerebral palsy cell-and-gene therapy) are also
registered in the **EU CTIS portal**, the **UK ISRCTN registry**, and several national
registries (ANZCTR, JPRN, ChiCTR, CTRI, DRKS, jRCT) that are only aggregated by **WHO ICTRP**.

The two highest-value, lowest-effort additions are both **free, JSON/XML, no-key, working APIs**
that I verified live:

1. **EU CTIS** (`euclinicaltrials.eu/ctis-public-api`) — the new EU register (replaced EudraCT
   for new trials from Jan 2023). Free public JSON API. **VERIFIED**: a POST search for
   `medicalCondition: "encephalopathy"` returned the UCL ACUMEN melatonin-for-HIE Phase I trial.
2. **UK ISRCTN** (`isrctn.com/api/query`) — free XML query API, no key. **VERIFIED**: returns
   neonatal HIE trials with countries, age range, and dates.

The meta-registry **WHO ICTRP** is the *theoretical* one-stop shop (~17 national registries) but
its real-time web service is **paid + partner-agreement only**; its only free channels are a
monthly bulk CSV on WHO OneDrive (10-day expiring link, MS-account-gated) and per-search XML
download. Not suitable for an unattended 6h cron. **Legacy EudraCT** (clinicaltrialsregister.eu)
has **no API** — HTML + plain-text export + RSS only.

**Primary recommendation:** Implement **CTIS first, ISRCTN second**, as two new pluggable
fetchers under `scripts/perception/sources/`, each writing the existing ledger shape with a
distinct `source_type` (`ctis`, `isrctn`). Defer ICTRP. Use the existing Crawl4AI→Firecrawl
stack for the "arbitrary future website" case via an LLM-extraction fetcher.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fetch trials from a registry API | PERCEPTION (new `sources/<reg>.py`) | — | Mirrors `fetch_ctgov.py`; each registry = one fetcher |
| Raw artifact storage | MEMORY (CF R2 via `ledger.upload_artifact`) | — | Already the convention; just a new `source_type` prefix |
| Provenance row | MEMORY (Supabase `evidence_ledger` via `ledger.insert_ledger_row`) | — | Unchanged; new `source_type` value |
| Cross-registry dedup | COGNITION/MEMORY (`eligibility_matcher`) | PERCEPTION (cheap pre-check) | Same trial appears in CTIS + ISRCTN + ICTRP; resolve at normalize time |
| Normalize → `clinical_trials` | COGNITION (`eligibility_matcher` per-source normalizer) | — | One normalizer fn per source_type; shared eligibility decision |
| Scrape arbitrary trial websites | PERCEPTION (Crawl4AI→Firecrawl, `gap_filler` pattern) + COGNITION (LLM extract) | — | Reuse existing stack; LLM maps HTML→normalized shape |

---

## Per-Registry Verification Table

| Registry | VERIFIED? | API base + endpoint | Format | Key fields available | Pagination | Rate-limit | Auth | Feasibility |
|----------|-----------|---------------------|--------|----------------------|-----------|-----------|------|-------------|
| **ClinicalTrials.gov v2** (baseline) | ✅ live | `GET clinicaltrials.gov/api/v2/studies` | JSON | full protocol | `nextPageToken` | none documented | none | already done |
| **EU CTIS** | ✅ live (curl POST 200) | `POST euclinicaltrials.eu/ctis-public-api/search` + `GET .../retrieve/{ctNumber}` | JSON | ctNumber, ctTitle, conditions, ctStatus, ageRanges (coded), countries+ISO, sponsor, dates, eligibilityCriteria, products | `pagination{page,size}` → `totalPages/nextPage` | none observed (be polite) | none | **EASY API** ✅ |
| **UK ISRCTN** | ✅ live (WebFetch 200) | `GET isrctn.com/api/query/format/default?q=...&limit=&offset=` | XML | isrctn id, title, condition, ageRange + lower/upperAgeLimit, recruitmentCountries, recruitmentStart/End, parties/contacts, externalRefs (EudraCT/DOI) | `limit`+`offset` (honored) | none observed | none | **EASY API** ✅ |
| **WHO ICTRP** (meta) | ✅ confirmed *paid* | Web service = partner/paid; bulk CSV on WHO OneDrive monthly (expiring); per-search XML download | XML/CSV | aggregated subset of member registries | n/a (bulk) | n/a | **partner agreement + fee** | **HARD / NOT FEASIBLE for cron** ⚠️ |
| **Legacy EudraCT** (clinicaltrialsregister.eu) | ✅ confirmed *no API* | HTML search only; plain-text export; RSS feed (7-day window) | HTML / text / RSS | trial summary | HTML pages | n/a | none | **HARD scrape** (only for legacy/closed trials; new EU trials → CTIS) |
| **ANZCTR** (AU/NZ) | ⚠️ UNVERIFIED here | reported XML/SOAP web service | XML | — | — | — | — | via ICTRP, or its own WS (verify before building) |
| **JPRN / jRCT** (Japan) | ⚠️ UNVERIFIED here | jRCT has a site; JPRN feeds ICTRP | — | — | — | — | — | via ICTRP |
| **ChiCTR** (China) | ⚠️ UNVERIFIED here | feeds ICTRP; site scraping reported brittle | — | — | — | — | — | via ICTRP |
| **CTRI** (India) | ⚠️ UNVERIFIED here | feeds ICTRP | — | — | — | — | — | via ICTRP |
| **DRKS** (Germany) | ⚠️ UNVERIFIED here | DRKS has a documented REST/search API + feeds ICTRP | — | — | — | — | — | own API likely (verify) or via ICTRP |

> The bottom block (ANZCTR/JPRN/ChiCTR/CTRI/DRKS) was **not hit with a live request** in this
> session and is marked **UNVERIFIED**. Do not build against any of them until a real request
> confirms the endpoint and format. Most are reachable only as members of WHO ICTRP.

---

## Evidence — actual responses captured

**EU CTIS — POST search (curl, HTTP 200):**
Request body that worked:
```json
{"pagination":{"page":1,"size":2},
 "sort":{"property":"decisionDate","direction":"DESC"},
 "searchCriteria":{"medicalCondition":"encephalopathy"}}
```
Response (trimmed) — note this is a **real HIE-in-babies trial we currently miss**:
```json
{"showWarning":false,
 "pagination":{"totalRecords":12,"currentPage":1,"totalPages":6,"nextPage":true,"prevPage":false},
 "data":[{"ctNumber":"2025-520538-49-00","ctStatus":2,
   "ctTitle":"ACUMEN: Phase I ... intravenous melatonin in babies with hypoxic-ischaemic encephalopathy (HIE) to augment therapeutic hypothermia ...",
   "conditions":"Moderate-Severe Hypoxic-Ischaemic Encephalopathy (HIE)",
   "trialCountries":["Ireland:2"],
   "decisionDateOverall":"12/09/2025",
   "therapeuticAreas":["Diseases [C] - Nervous System Diseases [C10]"],
   "sponsor":"University College London","trialPhase":"Human Pharmacology (Phase I)..."}]}
```

**EU CTIS — GET retrieve (curl, HTTP 200), top-level keys:**
```
['ctNumber','ctStatus','decisionDate','publishDate','ctPublicStatusCode',
 'authorizedApplication','events','results','documents','trialRegion',
 'trialRegionCode','correctiveMeasures']
```
Nested detail path (verified live):
`authorizedApplication.authorizedPartI` → `rowCountriesInfo[]` (name + isoAlpha2/3),
`medicalConditions`, `sponsors`, `therapeuticAreas`, `products[]` (name, activeSubstance,
`isPaediatricFormulation`, orphan designation), and
`trialDetails.trialInformation` →
`{medicalCondition, eligibilityCriteria, trialDuration, populationOfTrialSubjects}`.
`populationOfTrialSubjects` = `{ageRanges:[{ageRangeCategoryCode}], isFemaleSubjects,
isMaleSubjects, isVulnerablePopulationSelected, clinicalTrialGroups}`.
⚠️ **Age is a CODE, not a string** (`ageRangeCategoryCode:"2"`) — needs a small lookup table.

**UK ISRCTN — GET query (WebFetch, HTTP 200):**
`GET isrctn.com/api/query/format/default?q=condition:encephalopathy&limit=2`
→ `<allTrials totalCount="275"><fullTrial><trial ...>`
Verified element paths for a neonatal trial (ISRCTN61218504 "ACUMEN"):
```xml
<ageRange>Neonate</ageRange>
<recruitmentStart>2025-04-30T...</recruitmentStart>
<recruitmentEnd>2026-11-30T...</recruitmentEnd>
<recruitmentCountries><country>United Kingdom</country><country>Australia</country>...</recruitmentCountries>
```
⚠️ **ISRCTN has NO explicit recruiting-status element** in the query API. Status is **inferred
from `recruitmentStart`/`recruitmentEnd` vs. today**. The `trialStatus:"Recruiting"` filter on
the query endpoint returns `totalCount=0` (does not work). Filter by `condition:` only; compute
recruiting locally.

ISRCTN field-scoped query syntax **does** work (verified):
- `condition:cerebral palsy` → totalCount=65 ✅
- `primaryStudyDesign:Interventional` → totalCount=24460 ✅
- `limit` is honored (limit=2 → 2 `fullTrial` elements; totalCount stays full) ✅
- Combining with `AND` across `condition:` + `trialStatus:`/`overallStatus:` returned 0 in every
  variant tested → **do not rely on server-side status filtering**; use single-field `condition:`
  queries (+ optional `recruitmentCountry:`/`ageRange:`) and filter status in code.

**WHO ICTRP (WebFetch):** web service "available to the public for research purposes only";
"The cost charged by ICTRP for accessing the ICTRP web service can be provided upon request";
requires a "WHO ICTRP Web Service – conditions of use" agreement. Free alternatives: monthly
bulk CSV (zip) on WHO **OneDrive**, link valid **10 days**, needs a Microsoft account; and
per-search XML download from the portal. `Trial2.aspx?TrialID=...` is **HTML-only**.

**Legacy EudraCT (WebFetch):** `clinicaltrialsregister.eu/ctr-search/search` is HTML; offers
plain-text export + a 7-day RSS feed; **no JSON/XML API**.

---

## RECOMMENDATION — what to implement, in order

### 1st: EU CTIS — `scripts/perception/sources/ctis.py` (source_type `ctis`)  ⭐ highest value
Best coverage-to-effort: free JSON, no key, pagination, and it **directly carries the kind of
trial Aleksandra needs** (proven by the live ACUMEN HIE result). Two-call pattern mirrors ctgov
(search → per-trial full retrieve → R2 + ledger).

**Exact query to use** (one POST per condition facet, same facet set as `fetch_ctgov`):
```python
CTIS_SEARCH = "https://euclinicaltrials.eu/ctis-public-api/search"
CTIS_RETRIEVE = "https://euclinicaltrials.eu/ctis-public-api/retrieve/{ct}"
def body(condition, page=1, size=20):
    return {"pagination": {"page": page, "size": size},
            "sort": {"property": "decisionDate", "direction": "DESC"},
            "searchCriteria": {"medicalCondition": condition}}
# Facets: "Hypoxic Ischemic Encephalopathy", "Neonatal Encephalopathy",
#         "Infantile Spasms", "Cerebral Palsy", "epilepsy" (broad infant net)
# Recruiting filter: CTIS status is in ctStatus / mscStatus; safest is to fetch all
# and treat ctStatus in {Authorised, Ongoing, recruiting-equivalents} as open, the
# rest as ineligible — mirror the conservative "evaluating on ambiguity" rule.
```
Loop pages while `pagination.nextPage` is true. For each `ctNumber`, dedup against
`known_sources([...], "ctis")`, then `GET retrieve/{ctNumber}`, upload full JSON to R2, insert
ledger row `source_type="ctis"`, `retrieval_method="ctis_public_api"`.

### 2nd: UK ISRCTN — `scripts/perception/sources/isrctn.py` (source_type `isrctn`)
Free XML, no key, neonatal coverage confirmed. Single GET per condition facet; parse XML;
**compute recruiting from dates** (no status field). Good complement to CTIS (UK/AU/IE sites
that CTIS, an EU-only register, won't have).

**Exact query to use:**
```python
ISRCTN = "https://www.isrctn.com/api/query/format/default"
# params: q="condition:<facet>", limit=100, offset=0  (page via offset)
# e.g. q=condition:cerebral palsy   /   q=condition:encephalopathy
# Optional narrowing (verified field names): recruitmentCountry, ageRange, conditionCategory
# DO NOT use trialStatus: in q — it returns 0. Infer status from recruitmentStart/End.
```

### Defer: WHO ICTRP, EudraCT, and individual national registries
- **ICTRP:** paid web service; the free monthly OneDrive CSV is expiring + MS-gated → not
  cron-friendly. Revisit only if EU+UK+US coverage proves insufficient (e.g. need ChiCTR/JPRN
  for an Asia-only cell-therapy trial). A future manual quarterly bulk-CSV import is the cheap
  fallback, not an automated source.
- **EudraCT:** legacy; new EU trials are in CTIS. Only worth scraping for a *specific known*
  old trial — handle via the generic scrape pattern below, not a dedicated fetcher.
- **ANZCTR/JPRN/ChiCTR/CTRI/DRKS:** verify each endpoint live before any build. DRKS most likely
  to have a usable own-API; the rest are practically ICTRP-only.

### Which registries actually carry Aleksandra's trial types
| Condition area | Best registries (realistic) |
|----------------|------------------------------|
| HIE / neonatal encephalopathy (cooling, melatonin, EPO, cell therapy) | **CTGOV + CTIS + ISRCTN** (ACUMEN confirmed in CTIS+ISRCTN) |
| Infantile spasms (vigabatrin, ACTH, hormonal) | CTGOV + CTIS + ISRCTN |
| Cerebral palsy — cord blood / MSC / stem cell | CTGOV (Duke), CTIS, ANZCTR (AU strong here → via ICTRP), ISRCTN |
| Cell & gene therapy, neonatal | CTGOV + CTIS (orphan/ATMP designations surfaced in CTIS `products`) |

---

## Proposed Pluggable Architecture

```
scripts/
  ledger.py                      # unchanged — shared R2 + evidence_ledger I/O
  fetch_ctgov.py                 # existing (could later move under sources/ as ctgov.py)
  perception/
    sources/
      __init__.py
      base.py                    # SourceFetcher protocol + run_source() driver
      ctis.py                    # source_type="ctis"   (POST search + GET retrieve)
      isrctn.py                  # source_type="isrctn" (GET XML query)
      website.py                 # generic Crawl4AI→Firecrawl→LLM-extract fetcher
  trials/
    eligibility_matcher.py       # extend: read source_type in (ctgov, ctis, isrctn);
                                 # dispatch to per-source normalizer → shared decision
    normalizers/
      __init__.py
      ctgov.py                   # = current extract_full_fields (move here)
      ctis.py                    # CTIS JSON   → NormalizedTrial
      isrctn.py                  # ISRCTN XML  → NormalizedTrial
```

### `base.py` — the contract every fetcher honors (matches `fetch_ctgov` exactly)
Each fetcher must, per trial:
1. derive a stable `source_id` (registry-native id: ctNumber for CTIS, ISRCTN number for ISRCTN);
2. `known_sources([...], source_type)` batch dedup (fail-open, like ctgov);
3. produce a thin `payload_metadata` dict in the **same shape `fetch_ctgov` writes** (see below);
4. `upload_artifact(source_type, source_id, raw_bytes, ext)` — raw JSON (`json`) or raw XML (`xml`);
5. `insert_ledger_row(source_id, source_type, retrieval_method, content_hash, raw_artifact_url, query, payload_metadata)`.

This means **no new `ledger.py` code is needed** — the existing helpers already take
`source_type` as a parameter. The only new code is per-source fetch+parse.

### Shared `payload_metadata` shape (the planner must enforce this — it is the contract)
`eligibility_matcher` currently reads these ctgov keys; new sources MUST emit the same keys so the
matcher's `map_and_evaluate` works with minimal branching:
```python
{
  "nct_id":            <native id or "">,   # CTIS/ISRCTN have no NCT → put native id here
  "registry":          "ctis" | "isrctn",   # NEW — disambiguates the id namespace
  "registry_id":       <ctNumber|ISRCTN>,   # NEW — native id, explicit
  "title":             str,
  "official_title":    str,
  "overall_status":    <normalized to ctgov vocab: RECRUITING/ACTIVE_NOT_RECRUITING/.../UNKNOWN>,
  "start_date":        str|None,            # ISO; CTIS decisionDate/startDateEU, ISRCTN recruitmentStart
  "completion_date":   str|None,
  "phases":            [str],               # map CTIS trialPhase / ISRCTN phase → ["PHASE1"...]
  "study_type":        str,
  "interventions":     [str],               # CTIS product names / ISRCTN intervention
  "min_age":           str|None,            # ctgov-style "N Months/Years" so parse_age_to_months works
  "max_age":           str|None,
  "sex":               str|None,
  "healthy_volunteers": bool|None,
  "locations_sample":  ["facility (country)", ...],  # so location_flags() works unchanged
  "has_full_text":     True,
}
```
Key insight: by re-using `overall_status` in **ctgov vocabulary** and `min_age/max_age` as
**ctgov-style strings**, the matcher's `parse_age_to_months`, `OPEN_STATUSES`, and `location_flags`
all keep working without change. Each source's job is to *translate into ctgov's vocabulary*.

### Eligibility-matcher change (per-source normalizer dispatch)
`fetch_ctgov_rows()` becomes `fetch_ledger_rows(source_types=("ctgov","ctis","isrctn"))`. For each
row, pick the normalizer by `source_type`, read the R2 raw artifact, produce the rich fields
(`extract_full_fields`-equivalent), then call the **shared** `map_and_evaluate` (unchanged
eligibility logic, bilingual {en,ka}, status diffing). The conservative decision rules
(ineligible only on clear disqualifier; ambiguous → evaluating; location never disqualifies)
stay identical — Core Value preserved across all registries.

---

## Schema change (one small migration)

The `clinical_trials.nct_id` UNIQUE column is the current conflict target for upsert. CTIS/ISRCTN
trials have **no NCT id**. Two viable options — recommend **Option A**:

**Option A (recommended) — add registry columns, keep upsert working:**
```sql
ALTER TABLE clinical_trials ADD COLUMN registry    TEXT;     -- 'ctgov' | 'ctis' | 'isrctn'
ALTER TABLE clinical_trials ADD COLUMN registry_id TEXT;     -- native id (ctNumber / ISRCTN)
-- cross-registry secondary ids for dedup (a CTIS trial often lists its EudraCT/NCT/ISRCTN)
ALTER TABLE clinical_trials ADD COLUMN secondary_ids TEXT[]; -- e.g. {'NCT06...','ISRCTN61218504'}
-- new natural key for non-NCT registries; keep nct_id for ctgov rows
CREATE UNIQUE INDEX clinical_trials_registry_uk ON clinical_trials (registry, registry_id)
  WHERE registry IS NOT NULL;
```
- ctgov rows keep upserting on `nct_id` (unchanged path).
- ctis/isrctn rows upsert on `on_conflict=registry,registry_id`.
- `eu_ctr_id` (already in schema) is the natural home for the CTIS `ctNumber` / legacy EudraCT id.

**Option B (cheaper, hackier):** reuse `nct_id` as a generic "primary id" and stuff `CTIS-...` /
`ISRCTN...` strings into it. Works with zero migration but pollutes the NCT namespace and breaks
any consumer that assumes `nct_id` is a real NCT. **Not recommended.**

### Cross-registry dedup (the same trial in CTIS *and* ISRCTN *and* ctgov)
ACUMEN proved this is real (it is in both CTIS and ISRCTN). Strategy:
1. **Primary:** match on any shared secondary id. CTIS `references`/`associatedClinicalTrials`
   and ISRCTN `externalRefs` both carry sibling registry ids (EudraCT, NCT, ISRCTN). On ingest,
   collect every id you can see into `secondary_ids`.
2. At normalize time, before upsert, query `clinical_trials` for any existing row whose
   `nct_id`/`registry_id`/`secondary_ids` intersects this trial's id set. If found → **merge**
   (prefer the richest source; keep all `secondary_ids`; do not create a duplicate row).
3. **Fallback (no shared id):** fuzzy title + condition + sponsor + start-year match flagged for
   `evaluating` (human review) — never silently auto-merge on title alone (Core Value: don't drop
   a lead by over-merging).
4. **Source precedence when merging the displayed record:** CTGOV (richest structured) > CTIS
   (rich) > ISRCTN. But always union locations/countries across all sources (Aleksandra cares
   about *where* she can enroll — a US site from ctgov + an EU site from CTIS is strictly better).

---

## Field → `clinical_trials` Normalization Mapping

### EU CTIS (`source_type="ctis"`) — from `GET /retrieve/{ctNumber}` JSON
| clinical_trials column | CTIS JSON path | Notes |
|------------------------|----------------|-------|
| `registry` | literal `"ctis"` | new col |
| `registry_id` / `eu_ctr_id` | `ctNumber` | e.g. `2025-520538-49-00` |
| `nct_id` | NULL (unless a sibling NCT found in `references`) | |
| `secondary_ids` | `authorizedApplication.authorizedPartI.trialDetails.references` + `associatedClinicalTrials` + `eudraCtCode` | collect NCT/EudraCT/ISRCTN |
| `title` | search `ctTitle` / retrieve `...clinicalTrialIdentifiers.fullTitle` | bilingual {en,ka} |
| `brief_summary` | `...trialInformation.trialObjective` (or endPoint) | bilingual |
| `eligibility_criteria` | `...trialInformation.eligibilityCriteria` | bilingual |
| `conditions` | `authorizedPartI.medicalConditions` (+ search `conditions`) | EN array |
| `overall_status` | map `ctStatus` (e.g. "Authorised"/"Ongoing"/code in `ctPublicStatusCode`) → ctgov vocab | see status map below |
| `phase` | `trialPhase` ("Human Pharmacology (Phase I)...") → "PHASE1" | |
| `study_type` | "INTERVENTIONAL" (CTIS = interventional drug trials only) | constant |
| `intervention_name` | `authorizedPartI.products[].productName` / `activeSubstanceName` | join |
| `min_age` / `max_age` | `populationOfTrialSubjects.ageRanges[].ageRangeCategoryCode` → string via **code table** | code "2" etc. — build lookup |
| `locations` (JSONB) | `authorizedPartI.rowCountriesInfo[]` → `{country, iso}` (CTIS = countries, not facilities) | |
| `locations_sample` | `["(<country>)" for each]` so `location_flags` works | CTIS rarely has facility names |
| `sex` | `isFemaleSubjects` / `isMaleSubjects` → "ALL"/"FEMALE"/"MALE" | |
| `start_date` | `startDateEU` / `decisionDate` | ISO |
| `last_updated` | `publishDate` / `events[]` last | |
| `pi_name`/contacts | `sponsors[]` (CTIS exposes sponsor, not always PI email) | often sponsor-only |

> Age codes: CTIS `ageRangeCategoryCode` is an enum (e.g. 1=in utero/preterm, 2=newborn/infants,
> 3=children, …). Build a small `CTIS_AGE_CODE → (min_months, max_months)` table from the CTIS
> data dictionary and emit ctgov-style strings (e.g. code "2" → `min_age="0 Days"`, a generous
> upper bound) so `parse_age_to_months` + the conservative age rule keep working. Until the table
> is verified, emit `None`/`None` → matcher routes to `evaluating` (never silently drops).

### UK ISRCTN (`source_type="isrctn"`) — from query XML (`<fullTrial><trial>`)
| clinical_trials column | ISRCTN XML element | Notes |
|------------------------|--------------------|-------|
| `registry` | literal `"isrctn"` | |
| `registry_id` | `isrctn` (the number) | e.g. `61218504` |
| `secondary_ids` | `externalRefs` (EudraCT/DOI/NCT) | for dedup |
| `title` | `trialDescription/title` (+ `scientificTitle`) | bilingual |
| `brief_summary` | `plainEnglishSummary` / `studyHypothesis` | bilingual |
| `eligibility_criteria` | `participants/inclusion` + `participants/exclusion` | concat, bilingual |
| `conditions` | `conditions/.../condition` | EN array |
| `overall_status` | **computed**: `recruitmentStart <= today <= recruitmentEnd` → RECRUITING; before → NOT_YET_RECRUITING; after → COMPLETED/UNKNOWN | **no status field** |
| `phase` | `trialDesign/phase` if present | |
| `study_type` | `trialDesign/primaryStudyDesign` ("Interventional"/"Observational") | |
| `intervention_name` | `interventions/.../intervention` | |
| `min_age`/`max_age` | `participants/ageRange` ("Neonate") + `lowerAgeLimit`/`upperAgeLimit` (unit+value) | map "Neonate" → 0; use limits when present |
| `locations` | `participants/recruitmentCountries/country[]` | countries (facility list rarely present) |
| `locations_sample` | `["(<country>)"]` | for `location_flags` |
| `contacts` | `parties/contact` (name, email, address) | PI/coordinator |
| `start_date` | `recruitmentStart` | |
| `estimated_completion` | `recruitmentEnd` / `overallEndDate` | |
| `last_updated` | `trial/@lastUpdated` | |

---

## Generic Future-Website Pattern (`sources/website.py`)

For hospital/foundation pages where trials are posted as prose (not a registry), **reuse the
existing scrape stack** — do not invent a new one. `scripts/gap_filler.py` already implements the
exact pattern: Crawl4AI primary → Firecrawl fallback (budget-gated via `firecrawl_spend:<month>`
kv_state, `FIRECRAWL_MONTHLY_CAP_USD`), content-addressed R2 storage, new ledger row per fetch.

Recommended flow for `website.py`:
1. Input: a list of watch URLs (config/table). Fetch markdown via the **same** Crawl4AI→Firecrawl
   logic factored out of `gap_filler._process_candidates` (lift it into a shared
   `scripts/perception/scrape.py` helper so both gap_filler and website.py call it).
2. Store raw markdown in R2 (`source_type="website"`, content-hash id — same as gap_filler).
3. **LLM-extract** the markdown → the shared `payload_metadata` shape using an existing model
   (Sonnet 4.6 default; budget-gated via the same `check_daily_budget()` already wired before
   Anthropic calls). Prompt: "extract any clinical trial as {title, conditions, status, min_age,
   max_age, locations[], intervention, contacts, dates}; if none, return []." Emit one ledger row
   per extracted trial with `source_type="website_trial"` so the matcher's normalizer can pick it
   up. **Provenance rule (inviolable):** keep the source URL + extraction model in
   `payload_metadata`; if the LLM is unsure, set status `evaluating`, never fabricate.
4. Dedup against registries via the same `secondary_ids` mechanism (a foundation page often names
   the NCT/EudraCT id — extract it).

Existing repo assets to reuse (verified present): `scripts/gap_filler.py` (Crawl4AI+Firecrawl),
`scripts/ledger.py` (R2 + ledger + kv budget state), `scripts/extraction/` (translate +
gemini_translator helpers the matcher already imports), `scripts/perception_tick.py` (the 6h
driver that should also invoke the new fetchers).

---

## Status vocabulary map (normalize every source → ctgov vocab the matcher already knows)

`eligibility_matcher.OPEN_STATUSES = {RECRUITING, NOT_YET_RECRUITING, ENROLLING_BY_INVITATION, ACTIVE_NOT_RECRUITING}`

| Source value | → ctgov vocab |
|--------------|----------------|
| CTIS "Authorised" / "Ongoing, recruiting" | RECRUITING (treat authorised+recent as open; ambiguous → evaluating) |
| CTIS "Ended" / "Suspended" / "Revoked" | (closed) → ineligible |
| ISRCTN dates: start ≤ today ≤ end | RECRUITING |
| ISRCTN: today < start | NOT_YET_RECRUITING |
| ISRCTN: today > end | COMPLETED (→ ineligible) |
| anything unmappable | UNKNOWN → routes to `evaluating` (never silently dropped) |

---

## Honest Gaps / Risks

- **CTIS status semantics are coarse.** `ctStatus`/`ctPublicStatusCode` describe the
  *application/authorisation* lifecycle, not site-level recruiting like ctgov. Risk: we surface an
  authorised-but-not-yet-recruiting trial as open. Mitigation: conservative mapping + the existing
  `evaluating` bucket; the family/clinician confirms. Acceptable under Core Value (over-surface,
  never drop). **[VERIFIED structure; status→recruiting mapping is ASSUMED until validated against
  several known-recruiting CTIS trials.]**
- **CTIS age is coded, not free text.** Need a verified `ageRangeCategoryCode` lookup table before
  age-based eligibility is trustworthy; until then emit None→`evaluating`. **[ASSUMED]** the code
  meanings — confirm against the CTIS data dictionary.
- **ISRCTN has no recruiting field.** Date-inferred status can be stale (a trial may pause without
  changing its planned `recruitmentEnd`). Mitigation: surface generously; re-check each tick.
  **[VERIFIED no status field via live response.]**
- **WHO ICTRP is effectively closed** for automation (paid web service; expiring OneDrive CSV).
  We accept reduced Asia/AU coverage for now; ANZCTR/JPRN/ChiCTR/CTRI trials may be missed unless
  they also appear in CTIS/ctgov. **[VERIFIED paid via WHO page.]**
- **Cross-registry dedup is the main correctness risk.** ACUMEN appears in ≥2 registries.
  Over-merge → lose a location; under-merge → duplicate noise. Recommend id-based merge only, with
  union-of-locations, and `evaluating` for fuzzy-only matches. **[design recommendation]**
- **Rate limits unknown for CTIS/ISRCTN** (none observed, none documented). Be polite: reuse the
  `time.sleep(0.5)` between queries from `fetch_ctgov`, set a descriptive User-Agent, cap page
  fan-out. **[VERIFIED: no limit hit in this session; absence of a documented limit is not a
  guarantee.]**
- **Terms of use:** CTIS data is EMA public register data (intended for public reuse); ISRCTN data
  is openly searchable. Neither required auth. Still, attribute provenance (we already do via the
  ledger) and don't hammer. ICTRP web service explicitly forbids non-partner programmatic use →
  **do not scrape it.** **[VERIFIED ICTRP terms; CTIS/ISRCTN reuse ASSUMED-permissive — worth a
  one-line ToU confirmation before production.]**
- **CTIS is drug-trials-only** (interventional medicinal products). Device/behavioral/cell-therapy
  trials that aren't "medicinal products" may not appear in CTIS → ISRCTN + ctgov cover those.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | CTIS `ctStatus`/`ctPublicStatusCode` "Authorised"/"Ongoing" ≈ recruiting | Status map | Surface a not-yet-open trial (mitigated by `evaluating`) |
| A2 | CTIS `ageRangeCategoryCode` enum meanings (1=preterm, 2=newborn/infant, …) | CTIS mapping | Wrong age eligibility → use None→evaluating until table verified |
| A3 | CTIS & ISRCTN public data are reuse-permissive (no auth ≠ no ToU) | Risks | Possible ToU constraint; confirm before prod |
| A4 | DRKS has its own usable API | Per-registry table | Only if we ever build DRKS; unverified |
| A5 | ANZCTR/JPRN/ChiCTR/CTRI reachable only via ICTRP | Per-registry table | Some may have own APIs; verify before building |
| A6 | Crawl4AI→Firecrawl helper can be factored out of gap_filler cleanly | Website pattern | Minor refactor risk only |

---

## Sources

### Primary (HIGH — hit with a live request this session)
- **EU CTIS** `POST euclinicaltrials.eu/ctis-public-api/search` → HTTP 200, JSON (curl) — returned ACUMEN HIE trial
- **EU CTIS** `GET euclinicaltrials.eu/ctis-public-api/retrieve/2025-520538-49-00` → HTTP 200, JSON (curl) — full nested detail keys verified
- **UK ISRCTN** `GET isrctn.com/api/query/format/default?q=condition:encephalopathy` → HTTP 200, XML, totalCount=275 (WebFetch); `condition:cerebral palsy`=65; `primaryStudyDesign:Interventional`=24460
- **ClinicalTrials.gov v2** `GET clinicaltrials.gov/api/v2/studies` → HTTP 200, JSON (baseline, re-confirmed)
- **WHO ICTRP web service page** (WebFetch) — "cost … upon request", partner agreement → paid/closed
- **Legacy EudraCT** `clinicaltrialsregister.eu/ctr-search/search` (WebFetch) — HTML + text export + RSS, no API

### Secondary (MEDIUM — community docs corroborating the verified endpoints)
- hendrik.codes "Scraping the Clinical Trials Information System" — CTIS POST body `searchCriteria` field list (corroborated by live curl)
- R package **ctrdata** (rfhb/ctrdata, CRAN) — multi-register aggregation incl. CTIS, ISRCTN, ICTRP
- JulHeg/euclinicaltrials.py — CTIS scraping reference
- WHO "Downloading records from the ICTRP database" / "ICTRP dataset in CSV format" — monthly OneDrive CSV (expiring, MS-account)

### Tertiary (LOW — UNVERIFIED, flagged for validation before any build)
- ANZCTR / JPRN / jRCT / ChiCTR / CTRI / DRKS endpoints (no live request made this session)

---

## Metadata

- **Standard stack:** HIGH — endpoints verified live; reuse existing `httpx` + `ledger.py`.
- **Architecture:** HIGH — directly mirrors `fetch_ctgov` + `eligibility_matcher` conventions read from the repo.
- **Schema change:** MEDIUM — Option A is clean but unapplied; PostgREST upsert conflict-target change needs testing.
- **Status/age normalization:** MEDIUM/LOW — CTIS status+age codes are ASSUMED until validated against known trials.
- **Research date:** 2026-06-15 · **Valid until:** ~2026-07-15 (public registry APIs are stable but CTIS is young and evolving).
