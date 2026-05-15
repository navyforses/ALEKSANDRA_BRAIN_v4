"""Phase 2 sub-phase 2-cross-cutting — CrewAI agent tools.

Each agent's tool module wraps a small set of existing Phase 1/2 scripts as
CrewAI @tool functions so the Spider / Analyzer / Hypothesis agents can
orchestrate the pipeline without re-implementing the workhorses. Tools are
intentionally thin — they delegate to scripts/* modules and return compact
JSON-serialisable counters that the agent's LLM can reason about.
"""
