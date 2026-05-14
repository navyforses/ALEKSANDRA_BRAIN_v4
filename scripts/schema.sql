-- ═══════════════════════════════════════════════════════════
-- ALEKSANDRA_BRAIN v3.0 — Unified Memory Architecture
-- "ერთი ტვინი, სამი საცავი"
--
-- ARCHITECTURE NOTE (updated 2026-05-12):
-- This schema covers the SUPABASE layer only.
-- The full system uses THREE databases:
--
-- 1. NEO4J (Graphiti) — knowledge graph: entities, relationships,
--    temporal decay, graph traversal. The `relationships` table
--    below is a FALLBACK/SYNC copy; Neo4j is the primary store.
--
-- 2. QDRANT — vector search: paper/therapy/hypothesis embeddings.
--    The `embedding vector(1536)` columns below are OPTIONAL
--    pgvector fallback; Qdrant with fastembed is the primary
--    vector store for HIPAA-compliant local embeddings.
--
-- 3. SUPABASE (this schema) — structured metadata, operational
--    state, user-facing data, logs, and reports.
--
-- The pgvector columns and functions (search_papers_semantic,
-- find_connections, find_cross_disease_opportunities) are kept
-- as fallback for environments without Neo4j/Qdrant access,
-- but in production the primary path is:
--   Semantic search → Qdrant
--   Graph traversal → Neo4j Cypher
--   Structured queries → Supabase PostgreSQL
--
-- UI scaffold: fork of freesurfer/freebrowse (React+NiiVue+Vite)
-- ═══════════════════════════════════════════════════════════

-- Step 0: Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- fuzzy text search
CREATE EXTENSION IF NOT EXISTS btree_gin;     -- fast GIN indexes

-- ═══════════════════════════════════════════════════════════
-- 📚 LAYER 1: PAPERS — ყველა კვლევა რაც ვიცით
-- ═══════════════════════════════════════════════════════════

CREATE TABLE papers (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Identity
  pmid TEXT UNIQUE,                           -- PubMed ID
  doi TEXT UNIQUE,                            -- Digital Object Identifier
  pmc_id TEXT,                                -- PubMed Central ID
  ct_id TEXT,                                 -- ClinicalTrials.gov NCT number

  -- Content
  title TEXT NOT NULL,
  abstract TEXT,
  authors TEXT[],                             -- array of author names
  journal TEXT,
  publication_date DATE,
  publication_year INTEGER,

  -- Classification
  paper_type TEXT CHECK (paper_type IN (
    'rct', 'cohort', 'case_control', 'case_report',
    'case_series', 'review', 'meta_analysis', 'systematic_review',
    'preclinical', 'in_vitro', 'animal', 'editorial',
    'letter', 'preprint', 'clinical_trial', 'guideline'
  )),
  evidence_level INTEGER CHECK (evidence_level BETWEEN 1 AND 7),
  -- 1=systematic review/meta, 2=RCT, 3=cohort, 4=case-control,
  -- 5=case series, 6=case report, 7=expert opinion

  -- Relevance to Aleksandra
  relevance_score FLOAT CHECK (relevance_score BETWEEN 0 AND 1),
  relevance_tags TEXT[],                      -- e.g. ['hie', 'cord_blood', 'neuroprotection']
  direct_relevance BOOLEAN DEFAULT false,     -- directly about HIE
  cross_disease_relevance BOOLEAN DEFAULT false, -- metformin pattern
  cross_disease_source TEXT,                  -- "originally studied in: diabetes"

  -- AI Analysis
  ai_summary TEXT,                            -- Claude-generated summary
  ai_key_findings TEXT[],                     -- key findings array
  ai_limitations TEXT[],                      -- noted limitations
  ai_aleksandra_implications TEXT,            -- specific implications for Aleksandra
  confidence_level TEXT CHECK (confidence_level IN ('high', 'moderate', 'low', 'very_low')),

  -- Vector embedding for semantic search
  embedding vector(1536),                     -- OpenAI ada-002 or similar

  -- Source tracking
  source TEXT CHECK (source IN (
    'pubmed', 'biorxiv', 'medrxiv', 'scholar', 'clinical_trials',
    'consensus', 'manual_upload', 'scite', 'web_search', 'citation_chain'
  )),
  source_url TEXT,
  pdf_storage_path TEXT,                      -- Cloudflare R2 path

  -- Status
  ingested_at TIMESTAMPTZ DEFAULT NOW(),
  analyzed_at TIMESTAMPTZ,                    -- when Claude analyzed it
  reviewed_by_human BOOLEAN DEFAULT false,    -- შაკომ გადახედა?
  is_archived BOOLEAN DEFAULT false,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_papers_embedding ON papers USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_papers_relevance ON papers (relevance_score DESC NULLS LAST);
CREATE INDEX idx_papers_date ON papers (publication_date DESC);
CREATE INDEX idx_papers_type ON papers (paper_type);
CREATE INDEX idx_papers_tags ON papers USING GIN (relevance_tags);
CREATE INDEX idx_papers_title_trgm ON papers USING GIN (title gin_trgm_ops);
CREATE INDEX idx_papers_abstract_trgm ON papers USING GIN (abstract gin_trgm_ops);


-- ═══════════════════════════════════════════════════════════
-- 💊 LAYER 2: THERAPIES — ყველა მკურნალობა/ინტერვენცია
-- ═══════════════════════════════════════════════════════════

CREATE TABLE therapies (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Identity
  name TEXT NOT NULL,
  name_aliases TEXT[],                        -- e.g. ['EPO', 'erythropoietin', 'Procrit']
  therapy_type TEXT CHECK (therapy_type IN (
    'pharmacological', 'cell_therapy', 'gene_therapy',
    'rehabilitation', 'neuromodulation', 'surgical',
    'nutritional', 'device', 'combination', 'other'
  )),

  -- Mechanism
  mechanism_of_action TEXT,                   -- how it works
  target_pathways UUID[],                     -- FK to pathways table
  target_brain_regions UUID[],                -- FK to brain_regions table

  -- Evidence for HIE
  evidence_in_hie TEXT CHECK (evidence_in_hie IN (
    'proven', 'promising', 'experimental', 'preclinical',
    'theoretical', 'disproven', 'unknown'
  )),
  evidence_summary TEXT,
  best_evidence_paper_id UUID REFERENCES papers(id),

  -- Clinical availability
  clinical_status TEXT CHECK (clinical_status IN (
    'standard_of_care', 'off_label', 'clinical_trial',
    'compassionate_use', 'preclinical', 'discontinued'
  )),
  available_locations TEXT[],                 -- where can you get it
  approximate_cost TEXT,                      -- e.g. "$15,000" or "trial-funded"

  -- Aleksandra-specific
  aleksandra_eligible BOOLEAN,
  aleksandra_status TEXT CHECK (aleksandra_status IN (
    'receiving', 'planned', 'applied', 'evaluating',
    'ineligible', 'declined', 'completed', 'not_considered'
  )),
  aleksandra_notes TEXT,

  -- Timing
  optimal_age_window TEXT,                    -- e.g. "0-24 months"
  time_sensitivity TEXT CHECK (time_sensitivity IN ('critical', 'important', 'flexible', 'any_age')),

  -- AI Analysis
  ai_assessment TEXT,
  confidence_level TEXT CHECK (confidence_level IN ('high', 'moderate', 'low', 'very_low')),
  embedding vector(1536),

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_therapies_embedding ON therapies USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX idx_therapies_type ON therapies (therapy_type);
CREATE INDEX idx_therapies_evidence ON therapies (evidence_in_hie);
CREATE INDEX idx_therapies_status ON therapies (aleksandra_status);


-- ═══════════════════════════════════════════════════════════
-- 🔗 LAYER 3: PATHWAYS — ბიოლოგიური გზები/მექანიზმები
-- ═══════════════════════════════════════════════════════════

CREATE TABLE pathways (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  name TEXT NOT NULL,                         -- e.g. "BDNF/TrkB signaling"
  name_aliases TEXT[],
  pathway_type TEXT CHECK (pathway_type IN (
    'neuroprotection', 'neuroinflammation', 'apoptosis',
    'neuroplasticity', 'myelination', 'angiogenesis',
    'oxidative_stress', 'excitotoxicity', 'mitochondrial',
    'immune_modulation', 'epigenetic', 'neurotrophic', 'other'
  )),

  -- Biology
  description TEXT,
  involved_genes TEXT[],                      -- gene symbols
  involved_proteins TEXT[],

  -- Relevance to HIE
  role_in_hie TEXT,                           -- how this pathway is involved in HIE
  role_in_damage TEXT CHECK (role_in_damage IN (
    'causative', 'protective', 'repair', 'dual_role', 'unknown'
  )),

  -- Therapeutic potential
  druggable BOOLEAN,                          -- can we target this?
  known_modulators TEXT[],                    -- drugs that affect this pathway

  -- Aleksandra-specific
  status_in_aleksandra TEXT,                  -- what we know about this pathway in her case

  embedding vector(1536),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);


-- ═══════════════════════════════════════════════════════════
-- 🧠 LAYER 4: BRAIN REGIONS — ტვინის რეგიონები
-- ═══════════════════════════════════════════════════════════

CREATE TABLE brain_regions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Identity
  name TEXT NOT NULL,                         -- e.g. "Primary Motor Cortex"
  name_ka TEXT,                               -- ქართული სახელი
  anatomical_code TEXT,                       -- e.g. "BA4" (Brodmann area)
  hemisphere TEXT CHECK (hemisphere IN ('left', 'right', 'bilateral', 'midline')),

  -- Structure
  parent_region_id UUID REFERENCES brain_regions(id), -- hierarchy
  region_type TEXT CHECK (region_type IN (
    'cortex', 'white_matter', 'deep_gray', 'brainstem',
    'cerebellum', 'ventricular', 'meninges'
  )),

  -- Function
  primary_functions TEXT[],                   -- e.g. ['voluntary movement', 'motor planning']
  functional_networks TEXT[],                 -- e.g. ['motor network', 'salience network']

  -- Aleksandra's damage map (FROM MRI)
  damage_status TEXT CHECK (damage_status IN (
    'destroyed', 'severely_damaged', 'moderately_damaged',
    'mildly_damaged', 'preserved', 'unknown'
  )),
  damage_description TEXT,                    -- specific MRI findings
  cystic_changes BOOLEAN DEFAULT false,
  gliosis BOOLEAN DEFAULT false,

  -- Plasticity potential
  plasticity_potential TEXT CHECK (plasticity_potential IN (
    'high', 'moderate', 'low', 'minimal', 'unknown'
  )),
  plasticity_notes TEXT,                      -- why this rating
  alternative_pathways TEXT[],                -- what might compensate

  -- 3D Visualization data
  atlas_coordinates JSONB,                    -- MNI coordinates for 3D rendering
  -- e.g. {"x": -38, "y": -22, "z": 52, "radius": 15}
  mesh_file_path TEXT,                        -- path to 3D mesh file
  color_code TEXT,                            -- hex color for visualization
  -- red=destroyed, orange=severe, yellow=moderate, green=preserved

  embedding vector(1536),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);


-- ═══════════════════════════════════════════════════════════
-- 💡 LAYER 5: HYPOTHESES — AI-generated ჰიპოთეზები
-- ═══════════════════════════════════════════════════════════

CREATE TABLE hypotheses (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Content
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  hypothesis_type TEXT CHECK (hypothesis_type IN (
    'drug_repurposing',          -- metformin pattern
    'pathway_target',            -- new pathway to target
    'combination_therapy',       -- A+B together
    'timing_optimization',       -- when to intervene
    'cross_disease_inference',   -- from other condition
    'plasticity_mechanism',      -- new rewiring possibility
    'biomarker_discovery',       -- new way to measure progress
    'technology_application',    -- new tech (BCI, ultrasound, etc.)
    'rehabilitation_innovation', -- new rehab approach
    'other'
  )),

  -- Evidence
  supporting_papers UUID[],                   -- papers that support this
  contradicting_papers UUID[],                -- papers that argue against
  related_therapies UUID[],                   -- connected therapies
  related_pathways UUID[],                    -- connected pathways
  related_brain_regions UUID[],               -- connected regions

  -- Assessment
  confidence_level TEXT CHECK (confidence_level IN ('high', 'moderate', 'low', 'very_low')),
  novelty_score FLOAT CHECK (novelty_score BETWEEN 0 AND 1),
  feasibility_score FLOAT CHECK (feasibility_score BETWEEN 0 AND 1),
  urgency TEXT CHECK (urgency IN ('immediate', 'short_term', 'medium_term', 'long_term')),

  -- AI reasoning
  ai_reasoning TEXT,                          -- Claude's chain of thought
  discovery_method TEXT,                      -- how was this found
  -- e.g. "cross-disease inference: lithium neuroprotection in TBI → potential in HIE"

  -- Action
  recommended_action TEXT,                    -- what to do about this
  contact_researcher TEXT,                    -- who to reach out to
  contact_email TEXT,

  -- Status
  status TEXT CHECK (status IN (
    'new', 'under_review', 'promising', 'pursuing',
    'tested', 'confirmed', 'rejected', 'archived'
  )) DEFAULT 'new',
  reviewed_at TIMESTAMPTZ,
  outcome TEXT,                               -- what happened when we pursued it

  -- Generation metadata
  generated_by TEXT DEFAULT 'claude',
  generation_batch TEXT,                      -- e.g. "weekly_sweep_2026-05-12"

  embedding vector(1536),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hypotheses_status ON hypotheses (status);
CREATE INDEX idx_hypotheses_confidence ON hypotheses (confidence_level);
CREATE INDEX idx_hypotheses_type ON hypotheses (hypothesis_type);


-- ═══════════════════════════════════════════════════════════
-- 👥 LAYER 6: CONTACTS — მკვლევარები, ექიმები, ინსტიტუციები
-- ═══════════════════════════════════════════════════════════

CREATE TABLE contacts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Identity
  full_name TEXT NOT NULL,
  short_name TEXT,                            -- decoder ring: "Sydney" = Sydney Crane
  title TEXT,                                 -- Dr., Prof., etc.
  role TEXT,                                  -- e.g. "Duke EAP coordinator"

  -- Affiliation
  institution TEXT,
  department TEXT,
  city TEXT,
  country TEXT,

  -- Contact
  email TEXT,
  phone TEXT,
  website TEXT,

  -- Research (for researchers)
  research_focus TEXT[],                       -- e.g. ['cord blood', 'HIE', 'neonatal']
  orcid TEXT,
  h_index INTEGER,
  key_publications UUID[],                    -- their papers in our DB

  -- Relationship
  contact_type TEXT CHECK (contact_type IN (
    'researcher', 'clinician', 'coordinator', 'social_worker',
    'navigator', 'funder', 'mentor', 'family_support',
    'institution', 'other'
  )),
  relationship_status TEXT CHECK (relationship_status IN (
    'active', 'pending_response', 'cold', 'warm', 'hot',
    'lost_contact', 'declined', 'completed'
  )),

  -- Communication history
  first_contact_date DATE,
  last_contact_date DATE,
  next_followup_date DATE,
  communication_notes TEXT,

  -- Aleksandra connection
  aleksandra_relevance TEXT,                  -- why this person matters

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contacts_followup ON contacts (next_followup_date) WHERE next_followup_date IS NOT NULL;
CREATE INDEX idx_contacts_status ON contacts (relationship_status);


-- ═══════════════════════════════════════════════════════════
-- 🕸️ LAYER 7: RELATIONSHIPS — ყველაფრის კავშირები (Graph)
-- ═══════════════════════════════════════════════════════════
-- NOTE: PRIMARY store is Neo4j/Graphiti. This table is a
-- SYNC COPY for SQL joins and as fallback when Neo4j is
-- unavailable. In production, graph traversal uses Cypher.

CREATE TABLE relationships (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Source node
  source_type TEXT NOT NULL CHECK (source_type IN (
    'paper', 'therapy', 'pathway', 'brain_region', 'hypothesis', 'contact'
  )),
  source_id UUID NOT NULL,

  -- Target node
  target_type TEXT NOT NULL CHECK (target_type IN (
    'paper', 'therapy', 'pathway', 'brain_region', 'hypothesis', 'contact'
  )),
  target_id UUID NOT NULL,

  -- Relationship type
  relationship TEXT NOT NULL,
  -- paper→therapy: 'studies', 'supports', 'contradicts', 'reviews'
  -- paper→pathway: 'investigates', 'discovers', 'modulates'
  -- therapy→pathway: 'targets', 'activates', 'inhibits', 'modulates'
  -- therapy→brain_region: 'treats', 'affects', 'targets'
  -- pathway→brain_region: 'active_in', 'damaged_in', 'protective_in'
  -- hypothesis→paper: 'based_on', 'supported_by', 'contradicted_by'
  -- contact→paper: 'authored', 'cited'
  -- contact→therapy: 'researches', 'provides', 'coordinates'

  -- Strength & Direction
  strength FLOAT CHECK (strength BETWEEN 0 AND 1),  -- how strong is this connection
  direction TEXT CHECK (direction IN ('directed', 'bidirectional')),

  -- Evidence
  evidence_source TEXT,                       -- where did we learn this connection

  -- AI-discovered?
  discovered_by TEXT CHECK (discovered_by IN ('manual', 'ai_ingestion', 'ai_correlation', 'citation_chain')),

  created_at TIMESTAMPTZ DEFAULT NOW(),

  -- Prevent duplicates
  UNIQUE (source_type, source_id, target_type, target_id, relationship)
);

CREATE INDEX idx_rel_source ON relationships (source_type, source_id);
CREATE INDEX idx_rel_target ON relationships (target_type, target_id);
CREATE INDEX idx_rel_type ON relationships (relationship);


-- ═══════════════════════════════════════════════════════════
-- 📊 LAYER 8: CLINICAL TRIALS TRACKER
-- ═══════════════════════════════════════════════════════════

CREATE TABLE clinical_trials (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  nct_id TEXT UNIQUE,                         -- NCT number
  eu_ctr_id TEXT,                             -- EU Clinical Trial Register

  title TEXT NOT NULL,
  brief_summary TEXT,

  -- Status
  overall_status TEXT,                        -- recruiting, active, completed, etc.
  phase TEXT,                                 -- Phase 1, 2, 3, 4
  study_type TEXT,                            -- interventional, observational

  -- Intervention
  intervention_type TEXT,
  intervention_name TEXT,
  therapy_id UUID REFERENCES therapies(id),

  -- Eligibility
  min_age TEXT,
  max_age TEXT,
  eligibility_criteria TEXT,

  -- Location
  locations JSONB,                            -- array of {facility, city, country}

  -- Aleksandra assessment
  aleksandra_eligible BOOLEAN,
  eligibility_issues TEXT[],                  -- why might not be eligible
  aleksandra_status TEXT CHECK (aleksandra_status IN (
    'identified', 'evaluating', 'applied', 'enrolled',
    'ineligible', 'declined', 'waitlisted', 'completed'
  )),

  -- Contacts
  pi_name TEXT,
  pi_email TEXT,
  coordinator_name TEXT,
  coordinator_email TEXT,

  -- Timeline
  start_date DATE,
  estimated_completion DATE,
  last_updated DATE,

  -- Monitoring
  last_checked TIMESTAMPTZ DEFAULT NOW(),
  status_changed BOOLEAN DEFAULT false,       -- flag when status changes

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);


-- ═══════════════════════════════════════════════════════════
-- 📋 LAYER 9: INGESTION LOG — რა შემოვიტანეთ, როდის
-- ═══════════════════════════════════════════════════════════

CREATE TABLE ingestion_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  batch_id TEXT NOT NULL,                     -- e.g. "sweep_2026-05-12_06:00"

  source TEXT NOT NULL,                       -- pubmed, biorxiv, etc.
  query_used TEXT,                            -- search query
  results_found INTEGER,
  new_papers_added INTEGER,
  duplicates_skipped INTEGER,

  -- Analysis
  papers_analyzed INTEGER,
  hypotheses_generated INTEGER,
  high_relevance_count INTEGER,

  -- Status
  status TEXT CHECK (status IN ('running', 'completed', 'failed', 'partial')),
  error_message TEXT,

  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  duration_seconds INTEGER
);


-- ═══════════════════════════════════════════════════════════
-- 📆 LAYER 10: DISCOVERY REPORTS — ყოველკვირეული ანგარიშები
-- ═══════════════════════════════════════════════════════════

CREATE TABLE discovery_reports (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  report_date DATE NOT NULL,
  report_type TEXT CHECK (report_type IN ('weekly', 'monthly', 'special', 'alert')),

  -- Content
  title TEXT NOT NULL,
  executive_summary TEXT,                     -- 3-sentence summary

  -- Sections (JSONB for flexibility)
  new_papers_section JSONB,                   -- top papers this period
  new_hypotheses_section JSONB,               -- AI-generated hypotheses
  trial_updates_section JSONB,                -- trial status changes
  cross_disease_insights JSONB,               -- metformin patterns found
  action_items JSONB,                         -- recommended next steps

  -- Stats
  papers_ingested INTEGER,
  papers_analyzed INTEGER,
  hypotheses_generated INTEGER,
  trials_updated INTEGER,

  -- Delivery
  delivered_to TEXT[],                        -- email, notion, etc.
  delivered_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ DEFAULT NOW()
);


-- ═══════════════════════════════════════════════════════════
-- 🔍 HELPER FUNCTIONS — "ტვინის ძიება"
-- ═══════════════════════════════════════════════════════════
-- NOTE: These functions are FALLBACK for environments without
-- Neo4j (graph) and Qdrant (vectors). In production:
--   search_papers_semantic → Qdrant MCP semantic search
--   find_connections → Neo4j Cypher MATCH traversal
--   find_cross_disease_opportunities → Neo4j Cypher query
--   get_pending_followups → stays in Supabase (operational data)

-- Semantic search: "იპოვე მსგავსი papers"
CREATE OR REPLACE FUNCTION search_papers_semantic(
  query_embedding vector(1536),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INTEGER DEFAULT 20
)
RETURNS TABLE (
  id UUID,
  title TEXT,
  abstract TEXT,
  relevance_score FLOAT,
  confidence_level TEXT,
  similarity FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    p.id,
    p.title,
    p.abstract,
    p.relevance_score,
    p.confidence_level,
    1 - (p.embedding <=> query_embedding) AS similarity
  FROM papers p
  WHERE 1 - (p.embedding <=> query_embedding) > match_threshold
    AND p.is_archived = false
  ORDER BY p.embedding <=> query_embedding
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql;


-- Graph traversal: "რა უკავშირდება X-ს?"
CREATE OR REPLACE FUNCTION find_connections(
  node_type TEXT,
  node_id UUID,
  max_depth INTEGER DEFAULT 2
)
RETURNS TABLE (
  depth INTEGER,
  path TEXT[],
  connected_type TEXT,
  connected_id UUID,
  relationship TEXT,
  strength FLOAT
) AS $$
WITH RECURSIVE graph_walk AS (
  -- Base case: direct connections
  SELECT
    1 AS depth,
    ARRAY[node_type || ':' || node_id::TEXT, r.relationship, r.target_type || ':' || r.target_id::TEXT] AS path,
    r.target_type AS connected_type,
    r.target_id AS connected_id,
    r.relationship,
    r.strength
  FROM relationships r
  WHERE r.source_type = node_type AND r.source_id = node_id

  UNION ALL

  -- Recursive: follow connections
  SELECT
    gw.depth + 1,
    gw.path || r.relationship || (r.target_type || ':' || r.target_id::TEXT),
    r.target_type,
    r.target_id,
    r.relationship,
    r.strength
  FROM graph_walk gw
  JOIN relationships r ON r.source_type = gw.connected_type AND r.source_id = gw.connected_id
  WHERE gw.depth < max_depth
    AND NOT (r.target_type || ':' || r.target_id::TEXT) = ANY(gw.path) -- prevent cycles
)
SELECT * FROM graph_walk
ORDER BY depth, strength DESC;
$$ LANGUAGE sql;


-- Cross-disease inference: "რა თერაპია მუშაობს სხვაგან იმავე pathway-ით?"
CREATE OR REPLACE FUNCTION find_cross_disease_opportunities()
RETURNS TABLE (
  therapy_name TEXT,
  therapy_id UUID,
  original_condition TEXT,
  shared_pathway TEXT,
  pathway_role_in_hie TEXT,
  supporting_paper_count BIGINT,
  confidence TEXT
) AS $$
SELECT
  t.name AS therapy_name,
  t.id AS therapy_id,
  p_paper.cross_disease_source AS original_condition,
  pw.name AS shared_pathway,
  pw.role_in_hie AS pathway_role_in_hie,
  COUNT(DISTINCT p_paper.id) AS supporting_paper_count,
  CASE
    WHEN COUNT(DISTINCT p_paper.id) >= 5 THEN 'moderate'
    WHEN COUNT(DISTINCT p_paper.id) >= 2 THEN 'low'
    ELSE 'very_low'
  END AS confidence
FROM therapies t
JOIN relationships r1 ON r1.source_type = 'therapy' AND r1.source_id = t.id
  AND r1.relationship IN ('targets', 'modulates')
JOIN pathways pw ON r1.target_type = 'pathway' AND r1.target_id = pw.id
  AND pw.role_in_hie IS NOT NULL
JOIN relationships r2 ON r2.target_type = 'therapy' AND r2.target_id = t.id
  AND r2.source_type = 'paper'
JOIN papers p_paper ON r2.source_id = p_paper.id
  AND p_paper.cross_disease_relevance = true
WHERE t.evidence_in_hie IN ('unknown', 'theoretical', 'preclinical')
  AND t.aleksandra_status IS DISTINCT FROM 'ineligible'
GROUP BY t.name, t.id, p_paper.cross_disease_source, pw.name, pw.role_in_hie
ORDER BY supporting_paper_count DESC;
$$ LANGUAGE sql;


-- Upcoming follow-ups: "ვის უნდა დავურეკო?"
CREATE OR REPLACE FUNCTION get_pending_followups(days_ahead INTEGER DEFAULT 7)
RETURNS TABLE (
  contact_name TEXT,
  email TEXT,
  role TEXT,
  institution TEXT,
  followup_date DATE,
  days_until INTEGER,
  last_contact DATE,
  notes TEXT
) AS $$
SELECT
  c.full_name,
  c.email,
  c.role,
  c.institution,
  c.next_followup_date,
  (c.next_followup_date - CURRENT_DATE) AS days_until,
  c.last_contact_date,
  c.communication_notes
FROM contacts c
WHERE c.next_followup_date <= CURRENT_DATE + days_ahead
  AND c.relationship_status NOT IN ('declined', 'completed', 'lost_contact')
ORDER BY c.next_followup_date ASC;
$$ LANGUAGE sql;


-- ═══════════════════════════════════════════════════════════
-- 🔐 ROW LEVEL SECURITY — დაცვა
-- ═══════════════════════════════════════════════════════════

-- For now, all tables are accessible to authenticated users
-- (single-user system: შაკო)
-- In future with Med&გზური: per-family RLS

ALTER TABLE papers ENABLE ROW LEVEL SECURITY;
ALTER TABLE therapies ENABLE ROW LEVEL SECURITY;
ALTER TABLE pathways ENABLE ROW LEVEL SECURITY;
ALTER TABLE brain_regions ENABLE ROW LEVEL SECURITY;
ALTER TABLE hypotheses ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical_trials ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_reports ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (for n8n/automation)
CREATE POLICY "Service role full access" ON papers FOR ALL USING (true);
CREATE POLICY "Service role full access" ON therapies FOR ALL USING (true);
CREATE POLICY "Service role full access" ON pathways FOR ALL USING (true);
CREATE POLICY "Service role full access" ON brain_regions FOR ALL USING (true);
CREATE POLICY "Service role full access" ON hypotheses FOR ALL USING (true);
CREATE POLICY "Service role full access" ON contacts FOR ALL USING (true);
CREATE POLICY "Service role full access" ON relationships FOR ALL USING (true);
CREATE POLICY "Service role full access" ON clinical_trials FOR ALL USING (true);
CREATE POLICY "Service role full access" ON ingestion_log FOR ALL USING (true);
CREATE POLICY "Service role full access" ON discovery_reports FOR ALL USING (true);


-- ═══════════════════════════════════════════════════════════
-- 📊 VIEWS — მზა ანალიტიკა
-- ═══════════════════════════════════════════════════════════

-- Dashboard overview
CREATE OR REPLACE VIEW brain_stats AS
SELECT
  (SELECT COUNT(*) FROM papers WHERE NOT is_archived) AS total_papers,
  (SELECT COUNT(*) FROM papers WHERE relevance_score > 0.7) AS high_relevance_papers,
  (SELECT COUNT(*) FROM papers WHERE ingested_at > NOW() - INTERVAL '7 days') AS papers_this_week,
  (SELECT COUNT(*) FROM therapies) AS total_therapies,
  (SELECT COUNT(*) FROM therapies WHERE aleksandra_status = 'receiving') AS active_therapies,
  (SELECT COUNT(*) FROM hypotheses WHERE status = 'new') AS new_hypotheses,
  (SELECT COUNT(*) FROM hypotheses WHERE status = 'pursuing') AS pursuing_hypotheses,
  (SELECT COUNT(*) FROM clinical_trials WHERE aleksandra_eligible = true) AS eligible_trials,
  (SELECT COUNT(*) FROM contacts WHERE next_followup_date <= CURRENT_DATE) AS overdue_followups,
  (SELECT COUNT(*) FROM relationships) AS total_connections;

-- Therapy pipeline
CREATE OR REPLACE VIEW therapy_pipeline AS
SELECT
  t.name,
  t.therapy_type,
  t.evidence_in_hie,
  t.clinical_status,
  t.aleksandra_status,
  t.optimal_age_window,
  t.time_sensitivity,
  t.confidence_level,
  COUNT(DISTINCT r.source_id) FILTER (WHERE r.source_type = 'paper') AS paper_count,
  COUNT(DISTINCT h.id) AS related_hypotheses
FROM therapies t
LEFT JOIN relationships r ON r.target_type = 'therapy' AND r.target_id = t.id
LEFT JOIN hypotheses h ON t.id = ANY(h.related_therapies)
GROUP BY t.id
ORDER BY
  CASE t.aleksandra_status
    WHEN 'receiving' THEN 1
    WHEN 'planned' THEN 2
    WHEN 'applied' THEN 3
    WHEN 'evaluating' THEN 4
    ELSE 5
  END;
