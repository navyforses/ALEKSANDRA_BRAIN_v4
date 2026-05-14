"""
setup_neo4j — seed local Neo4j with Aleksandra's baseline data.

Creates:
  - 9 entity-type constraints (Patient, BrainRegion, Drug, Gene, Pathway,
    Paper, Trial, Contact, Hypothesis)
  - Patient(Aleksandra) root node
  - BrainRegion seed nodes from the MRI damage map (preserved brainstem,
    destroyed motor cortex, etc.)
  - Relationships LOCATED_IN, DAMAGED_IN, PRESERVED_IN linking them

Idempotent — re-running merges instead of duplicating.

Usage:
    .venv/Scripts/python.exe -m scripts.setup_neo4j
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = ROOT / ".env"
    if not env_path.exists():
        return env
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENTITY_TYPES = [
    "Patient",
    "BrainRegion",
    "Drug",
    "Gene",
    "Pathway",
    "Paper",
    "Trial",
    "Contact",
    "Hypothesis",
]

# Aleksandra's MRI damage map summary. Source: BMC MRI report.
BRAIN_REGIONS = [
    # name, status, notes
    ("Brainstem", "preserved", "Preserved — basis for the unknown-potential stance"),
    ("Cerebellum", "preserved", "Largely preserved"),
    ("Thalamus", "partial", "Partial bilateral injury"),
    ("Basal_Ganglia", "damaged", "Bilateral involvement typical of HIE"),
    ("Motor_Cortex", "damaged", "Diffuse cystic encephalomalacia"),
    ("Sensory_Cortex", "damaged", "Diffuse cystic encephalomalacia"),
    ("Visual_Cortex", "partial", "Occipital — partial involvement"),
    ("Hippocampus", "partial", "Bilateral partial injury"),
    ("White_Matter", "damaged", "Extensive cystic change"),
]


def setup(driver) -> None:
    with driver.session() as s:
        # 1. Uniqueness constraints (newer Neo4j requires "FOR (n:Label) REQUIRE n.id IS UNIQUE")
        for label in ENTITY_TYPES:
            s.run(
                f"CREATE CONSTRAINT {label.lower()}_name_unique IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.name IS UNIQUE"
            )
            print(f"  [OK] constraint on {label}.name")

        # 2. Aleksandra root node
        s.run(
            """
            MERGE (p:Patient {name: 'Aleksandra'})
            SET p.full_name = 'Aleksandra Jincharadze',
                p.dob = date('2025-08-28'),
                p.diagnosis = 'severe HIE, diffuse cystic encephalomalacia, preserved brainstem',
                p.mrn = '7616818',
                p.location = 'Boston, MA (Philoxenia House, Jamaica Plain)'
            """
        )
        print("  [OK] Patient(Aleksandra) upserted")

        # 3. Brain regions + relationships
        for region, status, notes in BRAIN_REGIONS:
            s.run(
                """
                MERGE (b:BrainRegion {name: $name})
                SET b.status = $status, b.notes = $notes
                WITH b
                MATCH (p:Patient {name: 'Aleksandra'})
                MERGE (p)-[r:HAS_BRAIN_REGION]->(b)
                SET r.status = $status
                """,
                {"name": region, "status": status, "notes": notes},
            )
        print(f"  [OK] {len(BRAIN_REGIONS)} BrainRegion nodes + HAS_BRAIN_REGION rels")

        # Verification
        result = s.run(
            "MATCH (n) RETURN labels(n) AS lbl, count(n) AS c ORDER BY c DESC"
        ).data()
        print()
        print("=== node counts ===")
        for row in result:
            print(f"  {row['lbl']}: {row['c']}")

        rels = s.run(
            "MATCH ()-[r]->() RETURN type(r) AS t, count(r) AS c ORDER BY c DESC"
        ).data()
        print()
        print("=== relationship counts ===")
        for row in rels:
            print(f"  {row['t']}: {row['c']}")


def main() -> int:
    env = load_env()
    for k, v in env.items():
        os.environ.setdefault(k, v)

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    if not password:
        print("ERROR: NEO4J_PASSWORD missing from .env")
        return 1

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
        print(f"[OK] connected to {uri} as {user}")
        setup(driver)
        print("\n[OK] Neo4j seed complete")
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
