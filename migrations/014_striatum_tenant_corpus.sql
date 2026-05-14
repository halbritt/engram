-- RFC 0044 Phase 1: local tenant/corpus isolation and Striatum source kind.

ALTER TYPE source_kind ADD VALUE IF NOT EXISTS 'striatum';

ALTER TABLE sources
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS bundle_id TEXT NULL,
    ADD CONSTRAINT sources_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT sources_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT conversations_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT conversations_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT messages_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT messages_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE notes
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT notes_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT notes_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE captures
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS bundle_id TEXT NULL,
    ADD CONSTRAINT captures_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT captures_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE segment_generations
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT segment_generations_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT segment_generations_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE segments
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT segments_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT segments_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE segment_embeddings
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT segment_embeddings_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT segment_embeddings_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE claim_extractions
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT claim_extractions_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT claim_extractions_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE claims
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT claims_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT claims_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE beliefs
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT beliefs_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT beliefs_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE belief_audit
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT belief_audit_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT belief_audit_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE contradictions
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT contradictions_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT contradictions_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE entities
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT entities_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT entities_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE entity_edges
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT entity_edges_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT entity_edges_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

ALTER TABLE entity_resolution_events
    ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS corpus_id TEXT NOT NULL DEFAULT 'personal',
    ADD CONSTRAINT entity_resolution_events_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT entity_resolution_events_corpus_id_nonempty CHECK (btrim(corpus_id) <> '');

CREATE INDEX IF NOT EXISTS sources_tenant_corpus_idx
    ON sources (tenant_id, corpus_id, source_kind);

CREATE INDEX IF NOT EXISTS captures_tenant_corpus_source_idx
    ON captures (tenant_id, corpus_id, source_kind);

CREATE UNIQUE INDEX IF NOT EXISTS captures_striatum_external_idx
    ON captures (tenant_id, corpus_id, source_kind, external_id)
    WHERE tenant_id = 'striatum' AND corpus_id = 'striatum';

CREATE INDEX IF NOT EXISTS segments_tenant_corpus_active_idx
    ON segments (tenant_id, corpus_id, source_kind, is_active);

CREATE INDEX IF NOT EXISTS claims_tenant_corpus_idx
    ON claims (tenant_id, corpus_id, predicate);

CREATE INDEX IF NOT EXISTS beliefs_tenant_corpus_idx
    ON beliefs (tenant_id, corpus_id, status, stability_class);

CREATE OR REPLACE FUNCTION prevent_segment_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'segments are immutable; DELETE is not allowed'
            USING ERRCODE = 'P0001';
    END IF;

    IF (
        NEW.id IS NOT DISTINCT FROM OLD.id
        AND NEW.generation_id IS NOT DISTINCT FROM OLD.generation_id
        AND NEW.source_id IS NOT DISTINCT FROM OLD.source_id
        AND NEW.source_kind IS NOT DISTINCT FROM OLD.source_kind
        AND NEW.conversation_id IS NOT DISTINCT FROM OLD.conversation_id
        AND NEW.note_id IS NOT DISTINCT FROM OLD.note_id
        AND NEW.capture_id IS NOT DISTINCT FROM OLD.capture_id
        AND NEW.message_ids IS NOT DISTINCT FROM OLD.message_ids
        AND NEW.sequence_index IS NOT DISTINCT FROM OLD.sequence_index
        AND NEW.content_text IS NOT DISTINCT FROM OLD.content_text
        AND NEW.summary_text IS NOT DISTINCT FROM OLD.summary_text
        AND NEW.window_strategy IS NOT DISTINCT FROM OLD.window_strategy
        AND NEW.window_index IS NOT DISTINCT FROM OLD.window_index
        AND NEW.segmenter_prompt_version IS NOT DISTINCT FROM OLD.segmenter_prompt_version
        AND NEW.segmenter_model_version IS NOT DISTINCT FROM OLD.segmenter_model_version
        AND NEW.privacy_tier IS NOT DISTINCT FROM OLD.privacy_tier
        AND NEW.tenant_id IS NOT DISTINCT FROM OLD.tenant_id
        AND NEW.corpus_id IS NOT DISTINCT FROM OLD.corpus_id
        AND NEW.created_at IS NOT DISTINCT FROM OLD.created_at
        AND NEW.raw_payload IS NOT DISTINCT FROM OLD.raw_payload
    ) THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION
        'segments are immutable except activation and invalidation metadata'
        USING ERRCODE = 'P0001';
END;
$$;

CREATE OR REPLACE FUNCTION prevent_segment_embedding_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'segment_embeddings are immutable; DELETE is not allowed'
            USING ERRCODE = 'P0001';
    END IF;

    IF (
        NEW.segment_id IS NOT DISTINCT FROM OLD.segment_id
        AND NEW.generation_id IS NOT DISTINCT FROM OLD.generation_id
        AND NEW.embedding_cache_id IS NOT DISTINCT FROM OLD.embedding_cache_id
        AND NEW.embedding IS NOT DISTINCT FROM OLD.embedding
        AND NEW.embedding_model_version IS NOT DISTINCT FROM OLD.embedding_model_version
        AND NEW.embedding_dimension IS NOT DISTINCT FROM OLD.embedding_dimension
        AND NEW.privacy_tier IS NOT DISTINCT FROM OLD.privacy_tier
        AND NEW.tenant_id IS NOT DISTINCT FROM OLD.tenant_id
        AND NEW.corpus_id IS NOT DISTINCT FROM OLD.corpus_id
        AND NEW.created_at IS NOT DISTINCT FROM OLD.created_at
    ) THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION
        'segment_embeddings are immutable except activation metadata'
        USING ERRCODE = 'P0001';
END;
$$;

CREATE OR REPLACE FUNCTION fn_claim_extractions_mutation_guard()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'claim_extractions rows cannot be deleted'
            USING ERRCODE = 'P0001';
    END IF;

    IF (
        NEW.id IS NOT DISTINCT FROM OLD.id
        AND NEW.segment_id IS NOT DISTINCT FROM OLD.segment_id
        AND NEW.generation_id IS NOT DISTINCT FROM OLD.generation_id
        AND NEW.extraction_prompt_version IS NOT DISTINCT FROM OLD.extraction_prompt_version
        AND NEW.extraction_model_version IS NOT DISTINCT FROM OLD.extraction_model_version
        AND NEW.request_profile_version IS NOT DISTINCT FROM OLD.request_profile_version
        AND NEW.tenant_id IS NOT DISTINCT FROM OLD.tenant_id
        AND NEW.corpus_id IS NOT DISTINCT FROM OLD.corpus_id
        AND NEW.created_at IS NOT DISTINCT FROM OLD.created_at
    ) THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION
        'claim_extractions updates are limited to status, claim_count, completed_at, and raw_payload'
        USING ERRCODE = 'P0001';
END;
$$;

CREATE OR REPLACE FUNCTION fn_beliefs_prepare_validate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    transition_request TEXT;
    vocab predicate_vocabulary%ROWTYPE;
    key_name TEXT;
    key_parts TEXT[] := '{}'::text[];
    key_value TEXT;
BEGIN
    transition_request := current_setting('engram.transition_in_progress', true);
    IF transition_request IS NULL OR transition_request = '' THEN
        RAISE EXCEPTION
            'belief mutations require engram.transition_in_progress'
            USING ERRCODE = 'P0001';
    END IF;

    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'beliefs cannot be deleted'
            USING ERRCODE = 'P0001';
    END IF;

    IF TG_OP = 'UPDATE' THEN
        IF (
            NEW.id IS NOT DISTINCT FROM OLD.id
            AND NEW.subject_text IS NOT DISTINCT FROM OLD.subject_text
            AND NEW.subject_normalized IS NOT DISTINCT FROM OLD.subject_normalized
            AND NEW.predicate IS NOT DISTINCT FROM OLD.predicate
            AND NEW.cardinality_class IS NOT DISTINCT FROM OLD.cardinality_class
            AND NEW.object_text IS NOT DISTINCT FROM OLD.object_text
            AND NEW.object_json IS NOT DISTINCT FROM OLD.object_json
            AND NEW.group_object_key IS NOT DISTINCT FROM OLD.group_object_key
            AND NEW.valid_from IS NOT DISTINCT FROM OLD.valid_from
            AND NEW.observed_at IS NOT DISTINCT FROM OLD.observed_at
            AND NEW.recorded_at IS NOT DISTINCT FROM OLD.recorded_at
            AND NEW.extracted_at IS NOT DISTINCT FROM OLD.extracted_at
            AND NEW.stability_class IS NOT DISTINCT FROM OLD.stability_class
            AND NEW.confidence IS NOT DISTINCT FROM OLD.confidence
            AND NEW.evidence_ids IS NOT DISTINCT FROM OLD.evidence_ids
            AND NEW.claim_ids IS NOT DISTINCT FROM OLD.claim_ids
            AND NEW.prompt_version IS NOT DISTINCT FROM OLD.prompt_version
            AND NEW.model_version IS NOT DISTINCT FROM OLD.model_version
            AND NEW.privacy_tier IS NOT DISTINCT FROM OLD.privacy_tier
            AND NEW.tenant_id IS NOT DISTINCT FROM OLD.tenant_id
            AND NEW.corpus_id IS NOT DISTINCT FROM OLD.corpus_id
            AND NEW.raw_payload IS NOT DISTINCT FROM OLD.raw_payload
        ) THEN
            RETURN NEW;
        END IF;

        RAISE EXCEPTION
            'belief updates are limited to valid_to, closed_at, superseded_by, and status'
            USING ERRCODE = 'P0001';
    END IF;

    SELECT * INTO vocab
    FROM predicate_vocabulary
    WHERE predicate = NEW.predicate;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'unknown belief predicate: %',
            NEW.predicate
            USING ERRCODE = '23503';
    END IF;

    NEW.subject_normalized := engram_normalize_subject(NEW.subject_text);
    NEW.cardinality_class := vocab.cardinality_class;
    NEW.stability_class := vocab.stability_class;

    IF vocab.object_kind = 'text' AND NEW.object_text IS NULL THEN
        RAISE EXCEPTION
            'belief predicate % requires object_text',
            NEW.predicate
            USING ERRCODE = '23514';
    END IF;

    IF vocab.object_kind = 'json' AND NEW.object_json IS NULL THEN
        RAISE EXCEPTION
            'belief predicate % requires object_json',
            NEW.predicate
            USING ERRCODE = '23514';
    END IF;

    IF vocab.cardinality_class = 'single_current' THEN
        NEW.group_object_key := '';
    ELSIF vocab.object_kind = 'text' THEN
        NEW.group_object_key := engram_normalize_subject(NEW.object_text);
    ELSE
        FOREACH key_name IN ARRAY vocab.group_object_keys LOOP
            key_value := COALESCE(NEW.object_json ->> key_name, '');
            key_parts := array_append(
                key_parts,
                engram_normalize_group_object_value(key_value)
            );
        END LOOP;
        NEW.group_object_key := array_to_string(key_parts, U&'\001F');
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fn_contradictions_mutation_guard()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'contradictions cannot be deleted'
            USING ERRCODE = 'P0001';
    END IF;

    IF (
        NEW.id IS NOT DISTINCT FROM OLD.id
        AND NEW.belief_a_id IS NOT DISTINCT FROM OLD.belief_a_id
        AND NEW.belief_b_id IS NOT DISTINCT FROM OLD.belief_b_id
        AND NEW.detected_at IS NOT DISTINCT FROM OLD.detected_at
        AND NEW.detection_kind IS NOT DISTINCT FROM OLD.detection_kind
        AND NEW.privacy_tier IS NOT DISTINCT FROM OLD.privacy_tier
        AND NEW.tenant_id IS NOT DISTINCT FROM OLD.tenant_id
        AND NEW.corpus_id IS NOT DISTINCT FROM OLD.corpus_id
        AND NEW.raw_payload IS NOT DISTINCT FROM OLD.raw_payload
    ) THEN
        RETURN NEW;
    END IF;

    RAISE EXCEPTION
        'contradictions updates are limited to resolution fields'
        USING ERRCODE = 'P0001';
END;
$$;

DROP VIEW IF EXISTS belief_review_queue;
DROP MATERIALIZED VIEW IF EXISTS current_beliefs;

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
    tenant_id,
    corpus_id,
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
CREATE INDEX current_beliefs_tenant_corpus_idx
    ON current_beliefs (tenant_id, corpus_id, status, stability_class);

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
