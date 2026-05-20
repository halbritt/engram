-- RFC 0051 / A8: generic rebuildable evidence item and exact-reference index.

CREATE TABLE IF NOT EXISTS evidence_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    corpus_id TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_table TEXT NOT NULL,
    source_id UUID NOT NULL,
    source_external_id TEXT NULL,
    source_sub_kind TEXT NULL,
    content_hash TEXT NULL CHECK (content_hash IS NULL OR content_hash ~ '^[0-9a-f]{64}$'),
    privacy_tier INT NOT NULL DEFAULT 1 CHECK (privacy_tier >= 0),
    sensitivity_class TEXT NOT NULL DEFAULT 'routine_project'
        CHECK (sensitivity_class IN
            ('routine_project','personal_private','third_party_communication',
             'calendar_contact','behavioral_activity','raw_media','exact_location',
             'health','biometric','finance','credential_or_secret_reference')),
    observed_at TIMESTAMPTZ NULL,
    imported_at TIMESTAMPTZ NULL,
    provenance JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(provenance) = 'object'),
    lifecycle_state TEXT NOT NULL DEFAULT 'active'
        CHECK (lifecycle_state IN ('active','stale','tombstoned')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(source_kind) <> ''),
    CHECK (btrim(source_table) <> ''),
    UNIQUE (tenant_id, corpus_id, source_table, source_id)
);

CREATE INDEX IF NOT EXISTS evidence_items_source_idx
    ON evidence_items (tenant_id, corpus_id, source_table, source_id);

CREATE INDEX IF NOT EXISTS evidence_items_kind_idx
    ON evidence_items (tenant_id, corpus_id, source_kind, lifecycle_state);

CREATE TABLE IF NOT EXISTS evidence_refs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_item_id UUID NOT NULL REFERENCES evidence_items(id) ON DELETE CASCADE,
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
    source_table TEXT NOT NULL,
    source_id UUID NOT NULL,
    freshness TEXT NOT NULL DEFAULT 'unknown'
        CHECK (freshness IN ('fresh','stale','dirty_working_tree','unknown')),
    dirty_working_tree BOOLEAN NOT NULL DEFAULT false,
    observed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(raw_payload) = 'object'),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(ref_value) <> ''),
    CHECK (btrim(ref_value_normalized) <> ''),
    CHECK (btrim(source_table) <> ''),
    UNIQUE (evidence_item_id, ref_kind, ref_value_normalized)
);

CREATE INDEX IF NOT EXISTS evidence_refs_exact_lookup_idx
    ON evidence_refs (tenant_id, corpus_id, ref_kind, ref_value_normalized);

CREATE INDEX IF NOT EXISTS evidence_refs_source_idx
    ON evidence_refs (tenant_id, corpus_id, source_table, source_id);

CREATE INDEX IF NOT EXISTS evidence_refs_item_idx
    ON evidence_refs (evidence_item_id);
