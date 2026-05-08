-- Phase 4 Tier 0: entity scaffolding, status-aware current beliefs,
-- and append-only review action provenance.

CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_kind TEXT NOT NULL CHECK (
        entity_kind IN ('person', 'project', 'organization', 'place', 'tool', 'concept', 'unknown')
    ),
    canonical_text TEXT NOT NULL CHECK (btrim(canonical_text) <> ''),
    canonical_key TEXT NOT NULL CHECK (btrim(canonical_key) <> ''),
    status TEXT NOT NULL CHECK (status IN ('active', 'merged', 'rejected')),
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    source_belief_ids UUID[] NOT NULL CHECK (cardinality(source_belief_ids) > 0),
    source_claim_ids UUID[] NOT NULL DEFAULT '{}'::uuid[],
    evidence_ids UUID[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    privacy_tier INT NOT NULL,
    resolution_method TEXT NOT NULL CHECK (
        resolution_method IN ('deterministic', 'local_llm_tiebreak', 'human')
    ),
    resolution_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    superseded_at TIMESTAMPTZ NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX entities_active_key_idx
    ON entities (entity_kind, canonical_key)
    WHERE status = 'active';
CREATE INDEX entities_status_kind_idx ON entities (status, entity_kind);
CREATE INDEX entities_source_belief_ids_gin_idx ON entities USING gin (source_belief_ids);
CREATE INDEX entities_evidence_ids_gin_idx ON entities USING gin (evidence_ids);

CREATE TABLE entity_resolution_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES entities(id),
    related_entity_id UUID NULL REFERENCES entities(id),
    event_kind TEXT NOT NULL CHECK (
        event_kind IN ('create', 'alias', 'merge', 'split', 'tiebreak', 'reject')
    ),
    source_belief_ids UUID[] NOT NULL CHECK (cardinality(source_belief_ids) > 0),
    source_claim_ids UUID[] NOT NULL DEFAULT '{}'::uuid[],
    evidence_ids UUID[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    resolution_method TEXT NOT NULL CHECK (
        resolution_method IN ('deterministic', 'local_llm_tiebreak', 'human')
    ),
    resolution_version TEXT NOT NULL,
    actor TEXT NOT NULL,
    privacy_tier INT NOT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX entity_resolution_events_entity_idx
    ON entity_resolution_events (entity_id, created_at DESC);
CREATE INDEX entity_resolution_events_related_idx
    ON entity_resolution_events (related_entity_id)
    WHERE related_entity_id IS NOT NULL;
CREATE INDEX entity_resolution_events_belief_ids_gin_idx
    ON entity_resolution_events USING gin (source_belief_ids);

CREATE TABLE entity_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID NOT NULL REFERENCES entities(id),
    target_entity_id UUID NOT NULL REFERENCES entities(id),
    edge_kind TEXT NOT NULL CHECK (btrim(edge_kind) <> ''),
    status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'rejected')),
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    source_belief_ids UUID[] NOT NULL CHECK (cardinality(source_belief_ids) > 0),
    source_claim_ids UUID[] NOT NULL DEFAULT '{}'::uuid[],
    evidence_ids UUID[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    privacy_tier INT NOT NULL,
    resolution_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    superseded_at TIMESTAMPTZ NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (source_entity_id <> target_entity_id)
);

CREATE UNIQUE INDEX entity_edges_active_unique_idx
    ON entity_edges (source_entity_id, target_entity_id, edge_kind)
    WHERE status = 'active';
CREATE INDEX entity_edges_source_idx ON entity_edges (source_entity_id, status, edge_kind);
CREATE INDEX entity_edges_target_idx ON entity_edges (target_entity_id, status, edge_kind);
CREATE INDEX entity_edges_belief_ids_gin_idx ON entity_edges USING gin (source_belief_ids);

CREATE TABLE belief_review_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    belief_id UUID NOT NULL REFERENCES beliefs(id),
    action_kind TEXT NOT NULL CHECK (
        action_kind IN ('accept', 'reject', 'correct', 'promote_to_pinned')
    ),
    action_status TEXT NOT NULL CHECK (
        action_status IN ('applied', 'recorded', 'queued_reprocessing')
    ),
    capture_id UUID NULL REFERENCES captures(id),
    request_uuid UUID NOT NULL,
    actor TEXT NOT NULL,
    note TEXT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX belief_review_actions_request_uuid_idx
    ON belief_review_actions (request_uuid);
CREATE INDEX belief_review_actions_belief_idx
    ON belief_review_actions (belief_id, created_at DESC);
CREATE INDEX belief_review_actions_kind_status_idx
    ON belief_review_actions (action_kind, action_status);

CREATE TABLE pinned_beliefs (
    belief_id UUID PRIMARY KEY REFERENCES beliefs(id),
    pinned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_uuid UUID NOT NULL,
    actor TEXT NOT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE OR REPLACE FUNCTION fn_phase4_append_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'phase4 table "%" is append-only; % is not allowed',
        TG_TABLE_NAME,
        TG_OP
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER entity_resolution_events_append_only
    BEFORE UPDATE OR DELETE ON entity_resolution_events
    FOR EACH ROW EXECUTE FUNCTION fn_phase4_append_only();

CREATE TRIGGER belief_review_actions_append_only
    BEFORE UPDATE OR DELETE ON belief_review_actions
    FOR EACH ROW EXECUTE FUNCTION fn_phase4_append_only();

CREATE TRIGGER pinned_beliefs_append_only
    BEFORE UPDATE OR DELETE ON pinned_beliefs
    FOR EACH ROW EXECUTE FUNCTION fn_phase4_append_only();

CREATE MATERIALIZED VIEW current_beliefs AS
SELECT
    id,
    subject_text,
    subject_normalized,
    predicate,
    cardinality_class,
    object_text,
    object_json,
    group_object_key,
    valid_from,
    valid_to,
    closed_at,
    observed_at,
    recorded_at,
    extracted_at,
    superseded_by,
    status,
    stability_class,
    confidence,
    evidence_ids,
    claim_ids,
    prompt_version,
    model_version,
    privacy_tier,
    raw_payload
FROM beliefs
WHERE valid_to IS NULL
  AND closed_at IS NULL
  AND superseded_by IS NULL
  AND status IN ('candidate', 'provisional', 'accepted');

CREATE UNIQUE INDEX current_beliefs_id_idx ON current_beliefs (id);
CREATE INDEX current_beliefs_status_stability_idx
    ON current_beliefs (status, stability_class);
CREATE INDEX current_beliefs_subject_predicate_idx
    ON current_beliefs (subject_normalized, predicate, group_object_key);
CREATE INDEX current_beliefs_evidence_ids_gin_idx
    ON current_beliefs USING gin (evidence_ids);

CREATE VIEW belief_review_queue AS
SELECT
    cb.*,
    COALESCE(open_contradictions.count, 0) AS open_contradiction_count,
    COALESCE(invalidated_claims.count, 0) AS invalidated_claim_count,
    (
        CASE WHEN COALESCE(open_contradictions.count, 0) > 0 THEN 100 ELSE 0 END
        + CASE WHEN COALESCE(invalidated_claims.count, 0) > 0 THEN 50 ELSE 0 END
        + CASE WHEN cb.privacy_tier > 1 THEN 20 ELSE 0 END
        + CASE WHEN cb.stability_class IN ('identity', 'relationship') THEN 10 ELSE 0 END
        + ROUND(((1.0 - cb.confidence)::numeric * 10.0), 2)
    ) AS review_priority
FROM current_beliefs cb
LEFT JOIN LATERAL (
    SELECT count(*)::int AS count
    FROM contradictions c
    WHERE c.resolution_status = 'open'
      AND (c.belief_a_id = cb.id OR c.belief_b_id = cb.id)
) open_contradictions ON true
LEFT JOIN LATERAL (
    SELECT count(DISTINCT ca.claim_id)::int AS count
    FROM claim_audits ca
    WHERE ca.claim_id = ANY(cb.claim_ids)
      AND ca.stage = 2
      AND ca.verdict = 'invalidated'
) invalidated_claims ON true
WHERE cb.status IN ('candidate', 'provisional');
