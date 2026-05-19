"""
team_registry — Competency team definitions for the neuroimaging swarm.

Each team has:
  - team_id: unique identifier
  - name: human-readable name
  - size_range: (min, max) number of agents
  - mcp_servers: list of MCP servers this team can call
  - roles: list of agent roles with responsibilities
  - constraints: privacy, budget, time limits
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentRole:
    role_id: str
    name: str
    description: str
    count: int
    primary_tools: list[str]
    max_runtime_sec: int = 30
    max_tokens: int = 8000


@dataclass
class CompetencyTeam:
    team_id: str
    name: str
    name_ka: str  # Georgian name
    size_range: tuple[int, int]
    mcp_servers: list[str]
    roles: list[AgentRole]
    constraints: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# TEAM REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

TEAM_REGISTRY: dict[str, CompetencyTeam] = {
    "alpha": CompetencyTeam(
        team_id="alpha",
        name="NIfTI Ingestion & Preprocessing",
        name_ka="NIfTI-ის ჩატვირთვა და წინასამუშაოები",
        size_range=(20, 50),
        mcp_servers=["aleksandra-niivue-mcp", "prism-mcp"],
        roles=[
            AgentRole(
                "α-1",
                "NIfTI Loader",
                "ტვირთავს .nii/.nii.gz ფაილებს",
                8,
                ["load_nifti"],
            ),
            AgentRole(
                "α-2",
                "Header Validator",
                "ამოწმებს affine, dim, zooms",
                4,
                ["load_nifti"],
            ),
            AgentRole(
                "α-3", "Orientation Normalizer", "RAS+ reorientation", 4, ["load_nifti"]
            ),
            AgentRole(
                "α-4",
                "Intensity Normalizer",
                "Z-score, histogram matching",
                8,
                ["load_nifti"],
            ),
            AgentRole(
                "α-5",
                "Quality Control",
                "Motion, ghosting detection",
                5,
                ["load_nifti"],
            ),
            AgentRole("α-6", "DICOM Converter", "dcm2niix wrapper", 2, ["load_nifti"]),
            AgentRole(
                "α-7",
                "Metadata Enricher",
                "Scanner info, TE/TR extraction",
                2,
                ["load_nifti"],
            ),
        ],
        constraints={
            "phi_handling": "local_only",
            "max_file_size_mb": 512,
            "allowed_formats": [".nii", ".nii.gz", ".dcm"],
        },
    ),
    "beta": CompetencyTeam(
        team_id="beta",
        name="MapReduce Chunk Processing",
        name_ka="MapReduce Chunk-ების დამუშავება",
        size_range=(100, 300),
        mcp_servers=["aleksandra-niivue-mcp", "prism-mcp"],
        roles=[
            AgentRole(
                "β-0",
                "MapReduce Coordinator",
                "Chunking + distribution + reduce",
                1,
                ["distribute_brain_processing", "load_nifti"],
                max_runtime_sec=120,
            ),
            AgentRole(
                "β-1",
                "Chunk Mapper",
                "Chunk list + overlap generation",
                8,
                ["distribute_brain_processing"],
            ),
            AgentRole(
                "β-2",
                "Chunk Worker",
                "Parallel voxel processing per chunk",
                250,
                ["load_nifti"],
                max_runtime_sec=30,
            ),
            AgentRole(
                "β-3",
                "Chunk Reducer",
                "Result aggregation",
                8,
                ["distribute_brain_processing"],
                max_runtime_sec=60,
            ),
            AgentRole(
                "β-4",
                "Boundary Merger",
                "Seamless chunk boundary blending",
                4,
                ["distribute_brain_processing"],
                max_runtime_sec=60,
            ),
        ],
        constraints={
            "phi_handling": "chunk_local_only",
            "chunk_size_default": 10,
            "max_concurrent_workers": 500,
            "retry_policy": {"max_retries": 3, "backoff_sec": 2},
        },
    ),
    "gamma": CompetencyTeam(
        team_id="gamma",
        name="Segmentation Pipeline",
        name_ka="სეგმენტაციის პაიპლაინი",
        size_range=(30, 50),
        mcp_servers=["aleksandra-niivue-mcp", "bonbid-mcp", "prism-mcp"],
        roles=[
            AgentRole(
                "γ-1",
                "FastSurfer Agent",
                "Cortical surface segmentation",
                8,
                ["segment"],
                max_runtime_sec=300,
            ),
            AgentRole(
                "γ-2",
                "BONBID-HIE Agent",
                "HIE lesion segmentation",
                8,
                ["segment"],
                max_runtime_sec=300,
            ),
            AgentRole(
                "γ-3",
                "BIBSnet Agent",
                "Infant tissue segmentation",
                8,
                ["segment"],
                max_runtime_sec=300,
            ),
            AgentRole(
                "γ-4", "Lesion Detector", "Cyst detection + volume", 8, ["segment"]
            ),
            AgentRole("γ-5", "Atlas Registration", "MNI152 alignment", 4, ["segment"]),
            AgentRole(
                "γ-6", "Segmentation QA", "Dice overlap validation", 8, ["segment"]
            ),
            AgentRole(
                "γ-7", "Volume Calculator", "Region volumes, asymmetry", 4, ["segment"]
            ),
        ],
        constraints={
            "phi_handling": "local_only",
            "gpu_required": False,  # True for FastSurfer at scale
            "model_cache_gb": 10,
        },
    ),
    "delta": CompetencyTeam(
        team_id="delta",
        name="3D Mesh & Visualization",
        name_ka="3D მეში და ვიზუალიზაცია",
        size_range=(20, 40),
        mcp_servers=["aleksandra-niivue-mcp"],
        roles=[
            AgentRole(
                "δ-1", "Surface Extractor", "Marching cubes → mesh", 8, ["export_mesh"]
            ),
            AgentRole(
                "δ-2", "Mesh Optimizer", "Decimation, smoothing", 4, ["export_mesh"]
            ),
            AgentRole(
                "δ-3", "NiiVue Preparer", "WebGL volume data prep", 4, ["load_nifti"]
            ),
            AgentRole(
                "δ-4",
                "R3F Scene Builder",
                "React Three Fiber scenes",
                4,
                ["export_mesh"],
            ),
            AgentRole(
                "δ-5",
                "Family HTML Generator",
                "Offline Georgian HTML",
                5,
                ["family_html"],
            ),
            AgentRole(
                "δ-6", "Color Mapper", "Heatmaps, probability maps", 4, ["export_mesh"]
            ),
            AgentRole(
                "δ-7",
                "3D Print Exporter",
                "STL for physical models",
                2,
                ["export_mesh"],
            ),
        ],
        constraints={
            "phi_handling": "client_side_only",
            "viewer_offline": True,
            "supported_formats": [".glb", ".obj", ".stl", ".html"],
        },
    ),
    "epsilon": CompetencyTeam(
        team_id="epsilon",
        name="Voxel Network & Graph Analysis",
        name_ka="ვოქსელების ქსელი და გრაფული ანალიზი",
        size_range=(15, 25),
        mcp_servers=["aleksandra-niivue-mcp", "prism-mcp"],
        roles=[
            AgentRole(
                "ε-1",
                "Graph Builder",
                "Voxel → NetworkX graph",
                4,
                ["build_voxel_network"],
            ),
            AgentRole(
                "ε-2",
                "Tractography Agent",
                "DTI fiber tracking",
                4,
                ["build_voxel_network"],
            ),
            AgentRole(
                "ε-3",
                "Connectivity Mapper",
                "Structural connectivity",
                4,
                ["build_voxel_network"],
            ),
            AgentRole(
                "ε-4",
                "Path Analyzer",
                "Shortest paths, centrality",
                4,
                ["build_voxel_network"],
            ),
            AgentRole(
                "ε-5",
                "Graph Exporter",
                "GEXF, GraphML export",
                4,
                ["build_voxel_network"],
            ),
        ],
        constraints={
            "phi_handling": "local_only",
            "max_nodes": 50_000_000,
        },
    ),
    "zeta": CompetencyTeam(
        team_id="zeta",
        name="Quality Assurance & Safety",
        name_ka="ხარისხის უზრუნველყოფა და უსაფრთხოება",
        size_range=(15, 25),
        mcp_servers=["panic-stop", "hello_brain", "prism-mcp"],
        roles=[
            AgentRole(
                "ζ-1", "Citation Verifier", "Source verification", 4, ["hello_brain"]
            ),
            AgentRole(
                "ζ-2",
                "Fabrication Detector",
                "Synthetic result detection",
                4,
                ["hello_brain"],
            ),
            AgentRole(
                "ζ-3", "Tone Checker", "Imperative verb lint", 4, ["hello_brain"]
            ),
            AgentRole("ζ-4", "Privacy Auditor", "PHI leak detection", 4, ["prism-mcp"]),
            AgentRole(
                "ζ-5", "Budget Gate", "$1.50/day enforcement", 4, ["hello_brain"]
            ),
        ],
        constraints={
            "kill_switch_access": True,
            "fabrication_rejection_rate": 0.99,
        },
    ),
    "eta": CompetencyTeam(
        team_id="eta",
        name="Infrastructure & Orchestration",
        name_ka="ინფრასტრუქტურა და ორკესტრაცია",
        size_range=(10, 20),
        mcp_servers=["hello_brain", "panic-stop"],
        roles=[
            AgentRole(
                "η-1", "Load Balancer", "Celery worker scaling", 4, ["hello_brain"]
            ),
            AgentRole(
                "η-2",
                "Health Monitor",
                "System connectivity checks",
                4,
                ["hello_brain"],
            ),
            AgentRole(
                "η-3", "Error Recovery", "Retry + dead-letter queue", 4, ["hello_brain"]
            ),
            AgentRole("η-4", "Run Ledger", "Supabase runs logging", 2, ["hello_brain"]),
        ],
        constraints={
            "kill_switch_access": True,
            "monitoring_interval_sec": 30,
        },
    ),
    "theta": CompetencyTeam(
        team_id="theta",
        name="Family Communication",
        name_ka="ოჯახთან კომუნიკაცია",
        size_range=(10, 20),
        mcp_servers=["aleksandra-brain"],  # Communicator MCP
        roles=[
            AgentRole(
                "θ-1", "Digest Compiler", "Daily/weekly summaries", 4, ["hello_brain"]
            ),
            AgentRole(
                "θ-2", "Georgian Translator", "Georgian translation", 4, ["hello_brain"]
            ),
            AgentRole(
                "θ-3", "Telegram Formatter", "Telegram formatting", 4, ["hello_brain"]
            ),
            AgentRole(
                "θ-4",
                "Clinician PDF Generator",
                "PDF with provenance",
                4,
                ["hello_brain"],
            ),
            AgentRole(
                "θ-5", "Notion Archivist", "Notion page append", 4, ["hello_brain"]
            ),
        ],
        constraints={
            "quiet_hours": {
                "start": "22:00",
                "end": "07:00",
                "timezone": "America/New_York",
            },
            "urgent_override": True,
        },
    ),
}


def get_team(team_id: str) -> CompetencyTeam | None:
    """Lookup a competency team by ID."""
    return TEAM_REGISTRY.get(team_id)


def list_teams() -> list[dict[str, Any]]:
    """List all teams with summary info."""
    return [
        {
            "team_id": t.team_id,
            "name": t.name,
            "name_ka": t.name_ka,
            "size_range": t.size_range,
            "total_roles": len(t.roles),
            "total_agents_min": sum(r.count for r in t.roles),
        }
        for t in TEAM_REGISTRY.values()
    ]


if __name__ == "__main__":
    import sys

    # Force UTF-8 for Windows console compatibility
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("ALEKSANDRA_BRAIN — Swarm Competency Teams")
    print("=" * 60)
    for summary in list_teams():
        print(
            f"\n{summary['team_id'].upper()}: {summary['name']} / {summary['name_ka']}"
        )
        print(f"  Agents (min): {summary['total_agents_min']}")
        print(f"  Size range: {summary['size_range']}")
        print(f"  Roles: {summary['total_roles']}")

    total_agents = sum(sum(r.count for r in t.roles) for t in TEAM_REGISTRY.values())
    print(f"\n{'='*60}")
    print(f"TOTAL MINIMUM AGENTS: {total_agents}")
