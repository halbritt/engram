CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE source_kind AS ENUM (
    'chatgpt',
    'obsidian',
    'capture',
    'future'
);

CREATE TYPE capture_type AS ENUM (
    'observation',
    'task',
    'idea',
    'reference',
    'person_note',
    'user_correction'
);

CREATE TYPE consolidation_status AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'failed'
);

CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_kind source_kind NOT NULL,
    external_id TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    filesystem_path TEXT,
    content_hash TEXT,
    raw_payload JSONB NOT NULL,
    UNIQUE (source_kind, external_id)
);

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id),
    source_kind source_kind NOT NULL,
    external_id TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload JSONB NOT NULL,
    privacy_tier INT NOT NULL DEFAULT 1,
    title TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    UNIQUE (source_id, external_id)
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id),
    source_kind source_kind NOT NULL,
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    external_id TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload JSONB NOT NULL,
    privacy_tier INT NOT NULL DEFAULT 1,
    role TEXT,
    content_text TEXT,
    created_at TIMESTAMPTZ,
    sequence_index INT NOT NULL,
    UNIQUE (source_id, external_id)
);

CREATE INDEX messages_conversation_sequence_idx
    ON messages (conversation_id, sequence_index);

CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id),
    source_kind source_kind NOT NULL,
    external_id TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload JSONB NOT NULL,
    title TEXT,
    content_text TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    UNIQUE (source_id, external_id)
);

CREATE TABLE captures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id),
    source_kind source_kind NOT NULL,
    external_id TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload JSONB NOT NULL,
    privacy_tier INT NOT NULL DEFAULT 1,
    capture_type capture_type NOT NULL,
    corrects_belief_id UUID NULL,
    content_text TEXT,
    observed_at TIMESTAMPTZ,
    UNIQUE (source_id, external_id)
);

CREATE TABLE consolidation_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stage TEXT NOT NULL,
    scope TEXT NOT NULL,
    status consolidation_status NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    position JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX consolidation_progress_stage_scope_idx
    ON consolidation_progress (stage, scope);

CREATE OR REPLACE FUNCTION prevent_raw_evidence_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'raw evidence table "%" is immutable; % is not allowed',
        TG_TABLE_NAME,
        TG_OP
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER sources_immutable
    BEFORE UPDATE OR DELETE ON sources
    FOR EACH ROW EXECUTE FUNCTION prevent_raw_evidence_mutation();

CREATE TRIGGER conversations_immutable
    BEFORE UPDATE OR DELETE ON conversations
    FOR EACH ROW EXECUTE FUNCTION prevent_raw_evidence_mutation();

CREATE TRIGGER messages_immutable
    BEFORE UPDATE OR DELETE ON messages
    FOR EACH ROW EXECUTE FUNCTION prevent_raw_evidence_mutation();

CREATE TRIGGER notes_immutable
    BEFORE UPDATE OR DELETE ON notes
    FOR EACH ROW EXECUTE FUNCTION prevent_raw_evidence_mutation();

CREATE TRIGGER captures_immutable
    BEFORE UPDATE OR DELETE ON captures
    FOR EACH ROW EXECUTE FUNCTION prevent_raw_evidence_mutation();
