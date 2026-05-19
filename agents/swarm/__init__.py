"""
agents/swarm — ALEKSANDRA_BRAIN Neuroimaging Swarm Agents.

Competency teams for distributed brain volume processing via MapReduce.
Each module defines a team of agents with specific roles, MCP servers, and constraints.
"""

from .team_registry import TEAM_REGISTRY, get_team, list_teams
from .chunk_worker import ChunkWorkerAgent

__all__ = [
    "TEAM_REGISTRY",
    "get_team",
    "list_teams",
    "ChunkWorkerAgent",
    "celery_app",
    "celery_tasks",
]
