// viewer/lib/api/causal.ts — Phase 7.6 typed API client for the Causal layer.
//
// Mirrors brain/causal/scm.py SCM model + brain/causal/graph_loader.py
// CausalNode/CausalEdge shapes. MOCK_MODE returns the reference SCM from
// build_reference_scm() so the UI renders the Vigabatrin -> Seizure
// frequency 5-node / 6-edge pattern without a live Neo4j instance.

const MOCK_MODE: boolean =
  !process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_MOCK_MODE === "true";

const API_BASE: string = process.env.NEXT_PUBLIC_API_URL ?? "";

// ---------------------------------------------------------------------------
// Types — mirror brain/causal/scm.py + graph_loader.py
// ---------------------------------------------------------------------------
export type CausalEdgeType =
  | "CAUSES"
  | "INHIBITS"
  | "MEDIATES"
  | "CONFOUNDS"
  | "MODERATES";

export interface CausalNode {
  id: number;
  name: string;
  dimension_ref: string | null;
  labels: string[];
}

export interface CausalEdge {
  source: number;
  target: number;
  edge_type: CausalEdgeType;
  confidence: number;
  citation: string;
  mechanism: string | null;
  time_lag_days: number | null;
}

export interface CausalGraphResponse {
  nodes: CausalNode[];
  edges: CausalEdge[];
}

export interface SCMRecord {
  id: string;
  name: string;
  description: string;
  treatment: string;
  outcome: string;
  confounders: string[];
  mediators: string[];
  created_at: string;
}

// ---------------------------------------------------------------------------
// Mock reference SCM — values taken directly from build_reference_scm()
// in brain/causal/scm.py. PMID citations are the real 3 cited in that file.
// ---------------------------------------------------------------------------
const MOCK_GRAPH: CausalGraphResponse = {
  nodes: [
    {
      id: 1,
      name: "Vigabatrin",
      dimension_ref: null,
      labels: ["CausalNode"],
    },
    {
      id: 2,
      name: "Seizure frequency",
      dimension_ref: "seizure_freq_per_day",
      labels: ["CausalNode"],
    },
    {
      id: 3,
      name: "Age (months)",
      dimension_ref: null,
      labels: ["CausalNode"],
    },
    {
      id: 4,
      name: "GABA-T enzyme",
      dimension_ref: null,
      labels: ["CausalNode"],
    },
    {
      id: 5,
      name: "Neuroplasticity window",
      dimension_ref: "neuroplasticity_resource",
      labels: ["CausalNode"],
    },
  ],
  edges: [
    {
      source: 1,
      target: 4,
      edge_type: "INHIBITS",
      confidence: 0.85,
      citation: "PMID:7686614",
      mechanism: "irreversible GABA-T inhibition",
      time_lag_days: null,
    },
    {
      source: 4,
      target: 2,
      edge_type: "CAUSES",
      confidence: 0.85,
      citation: "PMID:7686614",
      mechanism: "GABA inhibition reduces hyperexcitability",
      time_lag_days: null,
    },
    {
      source: 3,
      target: 1,
      edge_type: "CAUSES",
      confidence: 0.85,
      citation: "PMID:32713850",
      mechanism: "age gates treatment eligibility",
      time_lag_days: null,
    },
    {
      source: 3,
      target: 2,
      edge_type: "CAUSES",
      confidence: 0.85,
      citation: "PMID:32713850",
      mechanism: "age-related seizure phenotype",
      time_lag_days: null,
    },
    {
      source: 3,
      target: 5,
      edge_type: "CAUSES",
      confidence: 0.85,
      citation: "PMID:19489084",
      mechanism: "neuroplasticity opens at birth",
      time_lag_days: null,
    },
    {
      source: 5,
      target: 2,
      edge_type: "CAUSES",
      confidence: 0.85,
      citation: "PMID:19489084",
      mechanism: "plasticity moderates seizure recovery",
      time_lag_days: null,
    },
  ],
};

const MOCK_SCM_LIST: SCMRecord[] = [
  {
    id: "reference_vigabatrin_seizure",
    name: "reference_vigabatrin_seizure",
    description:
      "Synthetic reference SCM (Vigabatrin -> Seizure frequency) per ARCHITECTURE 6.2. PHI-free.",
    treatment: "Vigabatrin",
    outcome: "Seizure frequency",
    confounders: ["Age (months)"],
    mediators: ["GABA-T enzyme", "Neuroplasticity window"],
    created_at: "2026-11-15T12:00:00Z",
  },
];

// ---------------------------------------------------------------------------
// Public API surface
// ---------------------------------------------------------------------------
export async function fetchCausalGraph(): Promise<CausalGraphResponse> {
  if (MOCK_MODE) {
    return MOCK_GRAPH;
  }
  try {
    // FND-02: Phase 7.2 causal graph is the SCM topology + edge weights.
    // No MRI / DICOM / PHI ever traverses this path.
    const res = await fetch(`${API_BASE}/api/causal/graph`, /* allow-remote */ {
      cache: "no-store",
    });
    if (!res.ok) {
      return MOCK_GRAPH;
    }
    return (await res.json()) as CausalGraphResponse;
  } catch {
    return MOCK_GRAPH;
  }
}

export async function fetchSCMList(): Promise<SCMRecord[]> {
  if (MOCK_MODE) {
    return MOCK_SCM_LIST;
  }
  try {
    // FND-02: Phase 7.2 SCM list is the SCM registry metadata.
    // No MRI / DICOM / PHI ever traverses this path.
    const res = await fetch(`${API_BASE}/api/causal/scms`, /* allow-remote */ {
      cache: "no-store",
    });
    if (!res.ok) {
      return MOCK_SCM_LIST;
    }
    return (await res.json()) as SCMRecord[];
  } catch {
    return MOCK_SCM_LIST;
  }
}

export const __MOCK_MODE__ = MOCK_MODE;
