"""
seed_aleksandra_data — populate the patient-specific Supabase tables.

Idempotent inserts into:
  - brain_regions   (the same MRI damage map we already seeded into Neo4j)
  - therapies       (current + watching meds + research programs)
  - aleksandra_timeline (birth + diagnoses + key clinical events)

Skips rows that already exist (matched by natural keys: region name,
therapy name, event_date + title). Service-role insert bypasses RLS.

Usage:
    .venv/Scripts/python.exe -m scripts.seed_aleksandra_data
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    p = ROOT / ".env"
    if not p.exists():
        return env
    for raw in p.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


BRAIN_REGIONS = [
    # name, damage_status (CHECK: destroyed|severely_damaged|moderately_damaged|mildly_damaged|preserved|unknown),
    # region_type (CHECK: cortex|white_matter|deep_gray|brainstem|cerebellum|ventricular|meninges),
    # damage_description
    (
        "Brainstem",
        "preserved",
        "brainstem",
        "Preserved — basis for the unknown-potential stance",
    ),
    ("Cerebellum", "preserved", "cerebellum", "Largely preserved"),
    ("Thalamus", "moderately_damaged", "deep_gray", "Partial bilateral injury"),
    (
        "Basal_Ganglia",
        "severely_damaged",
        "deep_gray",
        "Bilateral involvement typical of HIE",
    ),
    ("Motor_Cortex", "destroyed", "cortex", "Diffuse cystic encephalomalacia"),
    ("Sensory_Cortex", "destroyed", "cortex", "Diffuse cystic encephalomalacia"),
    (
        "Visual_Cortex",
        "moderately_damaged",
        "cortex",
        "Occipital — partial involvement",
    ),
    ("Hippocampus", "moderately_damaged", "deep_gray", "Bilateral partial injury"),
    ("White_Matter", "severely_damaged", "white_matter", "Extensive cystic change"),
]

THERAPIES = [
    # name, therapy_type (CHECK: pharmacological|cell_therapy|gene_therapy|rehabilitation|...),
    # aleksandra_status (CHECK: receiving|planned|applied|evaluating|ineligible|declined|completed|not_considered),
    # mechanism_of_action, aleksandra_notes
    (
        "Keppra (levetiracetam)",
        "pharmacological",
        "receiving",
        "anticonvulsant",
        "Current seizure med",
    ),
    (
        "Vigabatrin (Sabril)",
        "pharmacological",
        "receiving",
        "GABA aminotransferase inhibitor",
        "Active anticonvulsant — washout required before Duke EAP cord blood",
    ),
    (
        "Duke EAP — cord blood",
        "cell_therapy",
        "planned",
        "autologous cord blood infusion",
        "~July 2026 target; requires vigabatrin washout",
    ),
    (
        "Wisconsin Virtual A2",
        "rehabilitation",
        "receiving",
        "telemedicine + home OT/PT planning",
        "Jeanette Heitman (program coordinator)",
    ),
    (
        "Metformin (cross-disease)",
        "pharmacological",
        "evaluating",
        "AMPK activation, neuroprotective signal",
        "Cross-disease repurposing candidate (per CLAUDE.md)",
    ),
    (
        "Erythropoietin (EPO)",
        "pharmacological",
        "evaluating",
        "anti-apoptotic, anti-inflammatory",
        "HIE neuroprotection candidate per literature",
    ),
]

TIMELINE = [
    # event_date (ISO), event_type, title, description, institution
    (
        "2025-08-28",
        "birth",
        "ალექსანდრა დაიბადა",
        "ALEKSANDRA Jincharadze; birth complicated by hypoxic-ischemic event",
        "Tbilisi maternity hospital",
    ),
    (
        "2025-08-29",
        "diagnosis",
        "მძიმე HIE დიაგნოზი",
        "Severe hypoxic-ischemic encephalopathy diagnosed within 24h of birth",
        "Tbilisi NICU",
    ),
    (
        "2025-09-15",
        "mri_scan",
        "პირველი MRI",
        "First brain MRI: diffuse cystic encephalomalacia, preserved brainstem",
        "Tbilisi",
    ),
    (
        "2026-01-15",
        "relocation",
        "Bostonში გადასახლება",
        "Family relocated to Boston, MA for treatment access",
        "Philoxenia House, Jamaica Plain",
    ),
    (
        "2026-02-01",
        "appointment",
        "BMC primary care intake",
        "Dr. Jack Maypole — primary care established",
        "Boston Medical Center",
    ),
    (
        "2026-02-15",
        "appointment",
        "BMC neurology intake",
        "Dr. Hien + Dr. August — neuro care team established",
        "Boston Medical Center",
    ),
    (
        "2026-03-01",
        "medication_change",
        "Vigabatrin დაიწყო",
        "Anticonvulsant trial; informs Duke EAP washout timeline",
        "BMC",
    ),
    (
        "2026-04-15",
        "program_enrollment",
        "Wisconsin Virtual A2 enrollment",
        "Joined Wisconsin Virtual A2 with Jeanette Heitman",
        "Wisconsin (remote)",
    ),
    (
        "2026-05-14",
        "system_milestone",
        "ALEKSANDRA_BRAIN Phase 0 closed",
        "AI research system foundation: kill-switch, budget gate, RLS, MCP allowlist all live",
        "navyforses/ALEKSANDRA_BRAIN_v4",
    ),
]


def supabase_upsert(
    url: str, key: str, table: str, rows: list[dict], on_conflict: str | None = None
) -> None:
    """POST rows to Supabase REST with merge-duplicates Prefer header."""
    params: dict[str, str] = {}
    if on_conflict:
        params["on_conflict"] = on_conflict
    r = httpx.post(
        f"{url}/rest/v1/{table}",
        json=rows,
        params=params,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal,resolution=merge-duplicates"
            if on_conflict
            else "return=minimal",
        },
        timeout=10,
    )
    if r.status_code in (200, 201, 204):
        print(f"  [OK] {table}: {len(rows)} row(s)")
    else:
        print(f"  [FAIL] {table}: HTTP {r.status_code} — {r.text[:200]}")


def supabase_delete_all(url: str, key: str, table: str) -> None:
    """Wipe a table (service-role bypasses RLS). Used for re-seeding."""
    r = httpx.delete(
        f"{url}/rest/v1/{table}",
        params={"id": "neq.00000000-0000-0000-0000-000000000000"},  # match-all
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Prefer": "return=minimal",
        },
        timeout=10,
    )
    if r.status_code in (200, 204):
        print(f"  [OK] {table}: wiped (pre-seed)")
    else:
        print(f"  [WARN] {table} wipe HTTP {r.status_code}: {r.text[:200]}")


def main() -> int:
    env = load_env()
    for k, v in env.items():
        os.environ.setdefault(k, v)

    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    # Wipe first to make this re-runnable idempotently
    for t in ("brain_regions", "therapies", "aleksandra_timeline"):
        supabase_delete_all(url, key, t)

    # brain_regions schema — match real columns from production
    # (no UNIQUE constraint on name in schema.sql; plain insert + dedup-by-select)
    print("=== brain_regions ===")
    supabase_upsert(
        url,
        key,
        "brain_regions",
        [
            {
                "name": n,
                "damage_status": s,
                "region_type": ag,
                "damage_description": nt,
            }
            for n, s, ag, nt in BRAIN_REGIONS
        ],
    )

    # therapies schema — match real columns from production
    print("=== therapies ===")
    supabase_upsert(
        url,
        key,
        "therapies",
        [
            {
                "name": n,
                "therapy_type": k,
                "aleksandra_status": s,
                "mechanism_of_action": m,
                "aleksandra_notes": nt,
            }
            for n, k, s, m, nt in THERAPIES
        ],
    )

    # aleksandra_timeline — composite on (event_date, title)
    print("=== aleksandra_timeline ===")
    supabase_upsert(
        url,
        key,
        "aleksandra_timeline",
        [
            {
                "event_date": d,
                "event_type": t,
                "title": ti,
                "description": de,
                "institution": ins,
            }
            for d, t, ti, de, ins in TIMELINE
        ],
    )  # no composite unique constraint, plain insert dedup by id

    # Verify counts
    print()
    print("=== counts ===")
    for table in ("brain_regions", "therapies", "aleksandra_timeline"):
        r = httpx.get(
            f"{url}/rest/v1/{table}",
            params={"select": "id", "limit": "1000"},
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Prefer": "count=exact",
            },
            timeout=5,
        )
        cnt = r.headers.get("content-range", "0-0/0").split("/")[-1]
        print(f"  {table:22} {cnt} rows")

    return 0


if __name__ == "__main__":
    sys.exit(main())
