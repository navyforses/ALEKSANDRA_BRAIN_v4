"""Phase 2 sub-phase 2D — minimal drug repurposing pipeline.

Scope per plan (mossy-stargazing-creek):
  - candidate extraction from validated hypotheses (Sonnet 4.5)
  - PubMed literature pass over (drug AND (HIE OR neonatal brain injury))
  - dossier write to the existing `therapies` Supabase table
    with status='evaluating'

Out of scope (deferred to Phase 2.5 / Phase 3): full 6-MCP pipeline over
Open Targets, DrugBank, PubChem, Reactome, KEGG, Enrichr — each is a
custom FastMCP server (4-5 day mini-phase each).
"""
