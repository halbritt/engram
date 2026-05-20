-- Architecture follow-up A6: context serving event, snapshot, and feedback
-- foundation. These rows are insert-only; derived snapshot state is
-- superseded by newer rows rather than rewritten in place.

CREATE SEQUENCE memory_epoch_seq AS BIGINT START WITH 1 INCREMENT BY 1;

CREATE TABLE memory_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'belief_changed',
            'source_import_completed',
            'projection_generation_activated',
            'entity_resolution_changed',
            'context_feedback_captured',
            'context_snapshot_refreshed',
            'context_snapshot_invalidated',
            'gold_feedback_captured'
        )
    ),
    aggregate_type TEXT NOT NULL CHECK (
        aggregate_type IN (
            'belief',
            'capture',
            'source',
            'source_audit',
            'projection_generation',
            'entity',
            'segment_generation',
            'context_snapshot',
            'context_feedback',
            'gold_label'
        )
    ),
    aggregate_id UUID NULL,
    scope_type TEXT NOT NULL CHECK (
        scope_type IN (
            'global',
            'tenant',
            'corpus',
            'user',
            'project',
            'session',
            'conversation',
            'eval'
        )
    ),
    scope_key TEXT NOT NULL,
    memory_epoch BIGINT NOT NULL DEFAULT nextval('memory_epoch_seq')
        CHECK (memory_epoch > 0),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(payload) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(scope_key) <> '')
);

CREATE UNIQUE INDEX memory_events_epoch_idx
    ON memory_events (memory_epoch);

CREATE INDEX memory_events_scope_epoch_idx
    ON memory_events (tenant_id, corpus_id, scope_type, scope_key, memory_epoch DESC);

CREATE INDEX memory_events_aggregate_idx
    ON memory_events (aggregate_type, aggregate_id, memory_epoch DESC)
    WHERE aggregate_id IS NOT NULL;

CREATE INDEX memory_events_type_created_idx
    ON memory_events (event_type, created_at DESC);

CREATE TABLE context_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    scope_type TEXT NOT NULL CHECK (
        scope_type IN (
            'user',
            'project',
            'session',
            'conversation',
            'eval'
        )
    ),
    scope_key TEXT NOT NULL,
    memory_epoch BIGINT NOT NULL CHECK (memory_epoch > 0),
    compiler_version TEXT NOT NULL,
    package_json JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(package_json) = 'object'),
    rendered_text TEXT NOT NULL DEFAULT '',
    source_belief_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    source_segment_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    source_reference_ids TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    omissions JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(omissions) = 'array'),
    is_dirty BOOLEAN NOT NULL DEFAULT false,
    request_uuid UUID NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(scope_key) <> ''),
    CHECK (btrim(compiler_version) <> '')
);

CREATE INDEX context_snapshots_scope_epoch_idx
    ON context_snapshots (tenant_id, corpus_id, scope_type, scope_key, memory_epoch DESC);

CREATE INDEX context_snapshots_dirty_idx
    ON context_snapshots (tenant_id, corpus_id, scope_type, scope_key, created_at DESC)
    WHERE is_dirty;

CREATE INDEX context_snapshots_source_beliefs_idx
    ON context_snapshots USING GIN (source_belief_ids);

CREATE INDEX context_snapshots_source_segments_idx
    ON context_snapshots USING GIN (source_segment_ids);

CREATE INDEX context_snapshots_source_references_idx
    ON context_snapshots USING GIN (source_reference_ids);

CREATE INDEX context_snapshots_omissions_idx
    ON context_snapshots USING GIN (omissions jsonb_path_ops);

CREATE TABLE context_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_id UUID NOT NULL REFERENCES context_snapshots(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    feedback_kind TEXT NOT NULL CHECK (
        feedback_kind IN (
            'useful',
            'wrong',
            'stale',
            'irrelevant'
        )
    ),
    source_belief_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    source_segment_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    source_reference_ids TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    correction_note TEXT NULL,
    actor TEXT NOT NULL DEFAULT 'operator',
    request_uuid UUID NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(payload) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(actor) <> ''),
    CHECK (correction_note IS NULL OR btrim(correction_note) <> '')
);

CREATE INDEX context_feedback_snapshot_idx
    ON context_feedback (snapshot_id, created_at DESC);

CREATE INDEX context_feedback_kind_created_idx
    ON context_feedback (tenant_id, corpus_id, feedback_kind, created_at DESC);

CREATE INDEX context_feedback_source_beliefs_idx
    ON context_feedback USING GIN (source_belief_ids);

CREATE INDEX context_feedback_source_segments_idx
    ON context_feedback USING GIN (source_segment_ids);

CREATE INDEX context_feedback_source_references_idx
    ON context_feedback USING GIN (source_reference_ids);

CREATE OR REPLACE FUNCTION fn_context_serving_append_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        '% is append-only; % is not allowed',
        TG_TABLE_NAME,
        TG_OP
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER memory_events_append_only
    BEFORE UPDATE OR DELETE ON memory_events
    FOR EACH ROW EXECUTE FUNCTION fn_context_serving_append_only();

CREATE TRIGGER context_snapshots_append_only
    BEFORE UPDATE OR DELETE ON context_snapshots
    FOR EACH ROW EXECUTE FUNCTION fn_context_serving_append_only();

CREATE TRIGGER context_feedback_append_only
    BEFORE UPDATE OR DELETE ON context_feedback
    FOR EACH ROW EXECUTE FUNCTION fn_context_serving_append_only();
