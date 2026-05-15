-- RFC 0046 / Layer 1: Striatum projection generation and exact-reference index.

CREATE TABLE striatum_projection_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    corpus_id TEXT NOT NULL,
    parent_kind TEXT NOT NULL CHECK (parent_kind IN ('bundle', 'capture', 'corpus')),
    parent_id TEXT NOT NULL,
    bundle_id TEXT NOT NULL,
    contract_version TEXT NOT NULL,
    projection_schema_version TEXT NOT NULL,
    projection_code_version TEXT NOT NULL,
    input_manifest_sha256 TEXT NOT NULL,
    input_item_count INT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'pending',
            'building',
            'ready',
            'activated',
            'superseded',
            'failed',
            'abandoned'
        )
    ),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    activated_at TIMESTAMPTZ NULL,
    superseded_at TIMESTAMPTZ NULL,
    error_count INT NOT NULL DEFAULT 0,
    last_error TEXT NULL,
    parent_generation_id UUID NULL REFERENCES striatum_projection_generations(id),
    required_embedding_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(parent_id) <> ''),
    CHECK (btrim(bundle_id) <> ''),
    CHECK (btrim(contract_version) <> ''),
    CHECK (btrim(projection_schema_version) <> ''),
    CHECK (btrim(projection_code_version) <> ''),
    CHECK (input_manifest_sha256 ~ '^[0-9a-f]{64}$'),
    CHECK (input_item_count >= 0),
    CHECK (error_count >= 0),
    CHECK (jsonb_typeof(required_embedding_profile) = 'object'),
    CHECK (jsonb_typeof(raw_payload) = 'object'),
    CHECK (status <> 'activated' OR activated_at IS NOT NULL),
    CHECK (status <> 'superseded' OR superseded_at IS NOT NULL)
);

CREATE UNIQUE INDEX striatum_projection_generations_idempotency_idx
    ON striatum_projection_generations (
        tenant_id,
        corpus_id,
        bundle_id,
        projection_schema_version,
        projection_code_version,
        input_manifest_sha256
    );

CREATE UNIQUE INDEX striatum_projection_generations_active_parent_idx
    ON striatum_projection_generations (tenant_id, corpus_id, parent_kind, parent_id)
    WHERE status = 'activated' AND superseded_at IS NULL;

CREATE INDEX striatum_projection_generations_tenant_corpus_status_idx
    ON striatum_projection_generations (tenant_id, corpus_id, status);

CREATE INDEX striatum_projection_generations_parent_generation_idx
    ON striatum_projection_generations (parent_generation_id)
    WHERE parent_generation_id IS NOT NULL;

CREATE TABLE striatum_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capture_id UUID NOT NULL REFERENCES captures(id),
    tenant_id TEXT NOT NULL,
    corpus_id TEXT NOT NULL,
    ref_kind TEXT NOT NULL CHECK (
        ref_kind IN (
            'item_id',
            'logical_id',
            'version_id',
            'path',
            'logical_path',
            'rfc_id',
            'decision_id',
            'review_id',
            'run_id',
            'workflow_id',
            'workflow_job_id',
            'job_id',
            'agent_process_id',
            'artifact_id',
            'issue_id',
            'blocker_id',
            'commit_sha',
            'branch',
            'tag',
            'source_hash',
            'bundle_id'
        )
    ),
    ref_value TEXT NOT NULL,
    ref_value_normalized TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    generation_id UUID NOT NULL REFERENCES striatum_projection_generations(id),
    is_active BOOLEAN NOT NULL DEFAULT false,
    observed_at TIMESTAMPTZ NOT NULL,
    privacy_tier INT NOT NULL DEFAULT 1,
    source_sub_kind TEXT NULL,
    ref_scope TEXT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(ref_value) <> ''),
    CHECK (btrim(ref_value_normalized) <> ''),
    CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    CHECK (privacy_tier >= 0),
    CHECK (source_sub_kind IS NULL OR btrim(source_sub_kind) <> ''),
    CHECK (ref_scope IS NULL OR btrim(ref_scope) <> ''),
    CHECK (jsonb_typeof(raw_payload) = 'object')
);

CREATE UNIQUE INDEX striatum_references_generation_ref_idx
    ON striatum_references (
        generation_id,
        capture_id,
        ref_kind,
        ref_value_normalized
    );

CREATE INDEX striatum_references_exact_lookup_idx
    ON striatum_references (tenant_id, corpus_id, ref_kind, ref_value_normalized);

CREATE INDEX striatum_references_generation_active_idx
    ON striatum_references (tenant_id, corpus_id, generation_id, is_active);

CREATE INDEX striatum_references_capture_idx
    ON striatum_references (capture_id);

CREATE OR REPLACE FUNCTION fn_striatum_references_validate_parent()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    generation_row striatum_projection_generations%ROWTYPE;
    capture_tenant_id TEXT;
    capture_corpus_id TEXT;
    capture_source_kind source_kind;
BEGIN
    SELECT *
    INTO generation_row
    FROM striatum_projection_generations
    WHERE id = NEW.generation_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'striatum_references.generation_id does not exist: %',
            NEW.generation_id
            USING ERRCODE = '23503';
    END IF;

    IF (
        generation_row.tenant_id IS DISTINCT FROM NEW.tenant_id
        OR generation_row.corpus_id IS DISTINCT FROM NEW.corpus_id
    ) THEN
        RAISE EXCEPTION
            'striatum reference tenant/corpus must match its generation'
            USING ERRCODE = '23514';
    END IF;

    IF (
        NEW.is_active
        AND (
            generation_row.status <> 'activated'
            OR generation_row.superseded_at IS NOT NULL
            OR generation_row.activated_at IS NULL
        )
    ) THEN
        RAISE EXCEPTION
            'active striatum references require the current activated generation'
            USING ERRCODE = '23514';
    END IF;

    SELECT c.tenant_id, c.corpus_id, c.source_kind
    INTO capture_tenant_id, capture_corpus_id, capture_source_kind
    FROM captures c
    WHERE c.id = NEW.capture_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'striatum_references.capture_id does not exist: %',
            NEW.capture_id
            USING ERRCODE = '23503';
    END IF;

    IF capture_source_kind <> 'striatum'::source_kind THEN
        RAISE EXCEPTION
            'striatum references must cite source_kind=striatum captures'
            USING ERRCODE = '23514';
    END IF;

    IF (
        capture_tenant_id IS DISTINCT FROM NEW.tenant_id
        OR capture_corpus_id IS DISTINCT FROM NEW.corpus_id
    ) THEN
        RAISE EXCEPTION
            'striatum reference tenant/corpus must match its capture'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER striatum_references_validate_parent
    BEFORE INSERT OR UPDATE ON striatum_references
    FOR EACH ROW EXECUTE FUNCTION fn_striatum_references_validate_parent();
