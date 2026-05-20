-- RFC 0052 / A9: local-only entity grounding evidence and review substrate.

ALTER TYPE source_kind ADD VALUE IF NOT EXISTS 'entity_grounding';

CREATE TABLE IF NOT EXISTS entity_grounding_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NULL REFERENCES sources(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    query_text TEXT NOT NULL,
    entity_kind TEXT NOT NULL DEFAULT 'unknown'
        CHECK (entity_kind IN (
            'person',
            'product',
            'place',
            'organization',
            'media_work',
            'tool',
            'concept',
            'unknown'
        )),
    source_url TEXT NULL,
    source_label TEXT NULL,
    content_hash TEXT NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    content_excerpt TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NULL,
    fetch_tool_version TEXT NOT NULL DEFAULT 'manual.local.v1',
    extractor_version TEXT NOT NULL DEFAULT 'none',
    privacy_tier INT NOT NULL DEFAULT 1 CHECK (privacy_tier >= 0),
    sensitivity_class TEXT NOT NULL DEFAULT 'routine_project'
        CHECK (sensitivity_class IN
            ('routine_project','personal_private','third_party_communication',
             'calendar_contact','behavioral_activity','raw_media','exact_location',
             'health','biometric','finance','credential_or_secret_reference')),
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(raw_payload) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(query_text) <> ''),
    CHECK (btrim(content_excerpt) <> ''),
    CHECK (btrim(fetch_tool_version) <> ''),
    CHECK (btrim(extractor_version) <> ''),
    CHECK (source_url IS NULL OR btrim(source_url) <> ''),
    CHECK (source_label IS NULL OR btrim(source_label) <> '')
);

CREATE INDEX IF NOT EXISTS entity_grounding_evidence_lookup_idx
    ON entity_grounding_evidence (tenant_id, corpus_id, entity_kind, created_at DESC);

CREATE INDEX IF NOT EXISTS entity_grounding_evidence_hash_idx
    ON entity_grounding_evidence (content_hash);

CREATE TABLE IF NOT EXISTS entity_identity_review_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    action_kind TEXT NOT NULL CHECK (
        action_kind IN (
            'alias_attach',
            'entity_merge',
            'entity_split',
            'not_same_entity',
            'external_id_attach',
            'grounding_evidence_attach'
        )
    ),
    entity_id UUID NULL REFERENCES entities(id),
    related_entity_id UUID NULL REFERENCES entities(id),
    grounding_evidence_id UUID NULL REFERENCES entity_grounding_evidence(id),
    alias_text TEXT NULL,
    external_id_kind TEXT NULL,
    external_id_value TEXT NULL,
    actor TEXT NOT NULL,
    rationale TEXT NULL,
    privacy_tier INT NOT NULL DEFAULT 1 CHECK (privacy_tier >= 0),
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(raw_payload) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(actor) <> ''),
    CHECK (alias_text IS NULL OR btrim(alias_text) <> ''),
    CHECK (external_id_kind IS NULL OR btrim(external_id_kind) <> ''),
    CHECK (external_id_value IS NULL OR btrim(external_id_value) <> '')
);

CREATE INDEX IF NOT EXISTS entity_identity_review_actions_entity_idx
    ON entity_identity_review_actions (entity_id, created_at DESC)
    WHERE entity_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS entity_identity_review_actions_grounding_idx
    ON entity_identity_review_actions (grounding_evidence_id)
    WHERE grounding_evidence_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS entity_identity_review_actions_kind_idx
    ON entity_identity_review_actions (tenant_id, corpus_id, action_kind, created_at DESC);

CREATE OR REPLACE FUNCTION fn_entity_grounding_append_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'entity grounding table "%" is append-only; % is not allowed',
        TG_TABLE_NAME,
        TG_OP
        USING ERRCODE = 'P0001';
END;
$$;

DROP TRIGGER IF EXISTS entity_grounding_evidence_append_only ON entity_grounding_evidence;
CREATE TRIGGER entity_grounding_evidence_append_only
    BEFORE UPDATE OR DELETE ON entity_grounding_evidence
    FOR EACH ROW EXECUTE FUNCTION fn_entity_grounding_append_only();

DROP TRIGGER IF EXISTS entity_identity_review_actions_append_only ON entity_identity_review_actions;
CREATE TRIGGER entity_identity_review_actions_append_only
    BEFORE UPDATE OR DELETE ON entity_identity_review_actions
    FOR EACH ROW EXECUTE FUNCTION fn_entity_grounding_append_only();
