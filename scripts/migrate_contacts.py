"""
Contacts migration — Phase 0 §6.2 placeholder

Extracts 80+ medical contacts from project knowledge into:
  1. Supabase contacts table
  2. Neo4j as Contact nodes with WORKS_AT → Institution
  3. follow_up_date = last_contact + 7 days

TODO: implement after §1.1 + §1.2 are green.
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError(
        "Phase 0 §6.2 — to be implemented after Supabase + Neo4j are live."
    )


if __name__ == "__main__":
    main()
