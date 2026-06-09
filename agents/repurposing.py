"""
Repurposing Agent — Drug Discovery Specialist

Runs monthly. Queries Open Targets for HIE-associated targets, DrugBank for
approved drugs hitting those targets, PubChem for BBB penetration + pediatric
safety, and L1000 for reverse transcriptomic signatures.

No institution operates this pipeline integrated and continuously for neonatal HIE.
"""

from __future__ import annotations

from crewai import Agent

from scripts.cognition import models

TOOLS: list = []

BACKSTORY = """
You operate the drug repurposing pipeline. Your search space is not "drugs
for HIE" — it is "approved drugs that target the molecular pathways HIE
damages". The difference matters: there are 17,430 known drugs and only
a handful labeled for HIE.

You score every candidate on three axes:
  1. Mechanism: does it hit a relevant target?
  2. BBB penetration: can it reach the brain?
  3. Pediatric safety: known profile in neonates/infants?

You output ranked, sourced, and clearly-flagged candidates — never a black box.
""".strip()


def build_repurposing(llm_model: str | None = None) -> Agent:
    llm_model = llm_model or models.crew_llm("thinker")  # 🧠 thinker tier (Opus)
    return Agent(
        role="Drug Repurposing Specialist",
        goal=(
            "Identify approved or investigational drugs that could be "
            "repurposed for neonatal HIE based on target overlap, BBB "
            "penetration, and pediatric safety."
        ),
        backstory=BACKSTORY,
        tools=TOOLS,
        llm=llm_model,
        verbose=True,
        allow_delegation=False,
        max_iter=15,
    )
