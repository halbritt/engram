-- RFC 0048 / Layer 3: privacy-safe Striatum packet audit records.

CREATE TABLE striatum_packet_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    packet_id UUID NOT NULL,
    generation_id UUID NOT NULL REFERENCES striatum_projection_generations(id),
    tenant_id TEXT NOT NULL,
    corpus_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    packet_type TEXT NOT NULL DEFAULT 'memory_packet',
    purpose TEXT NOT NULL CHECK (
        purpose IN (
            'operator_startup',
            'workflow_scaffold',
            'packet_prepare',
            'review_prepare',
            'blocker_recovery',
            'ui_search',
            'manual_search'
        )
    ),
    status TEXT NOT NULL CHECK (
        status IN (
            'ok',
            'no_data',
            'disabled',
            'unavailable',
            'unauthorized',
            'timeout',
            'stale',
            'malformed',
            'error'
        )
    ),
    query TEXT NOT NULL,
    budget JSONB NOT NULL DEFAULT '{}'::jsonb,
    filters JSONB NOT NULL DEFAULT '{}'::jsonb,
    selected JSONB NOT NULL DEFAULT '[]'::jsonb,
    omitted JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(tenant_id) <> ''),
    CHECK (btrim(corpus_id) <> ''),
    CHECK (btrim(policy_version) <> ''),
    CHECK (btrim(packet_type) <> ''),
    CHECK (btrim(query) <> ''),
    CHECK (jsonb_typeof(budget) = 'object'),
    CHECK (jsonb_typeof(filters) = 'object'),
    CHECK (jsonb_typeof(selected) = 'array'),
    CHECK (jsonb_typeof(omitted) = 'array'),
    CHECK (jsonb_typeof(warnings) = 'array'),
    CHECK (jsonb_typeof(metadata) = 'object')
);

CREATE UNIQUE INDEX striatum_packet_audits_packet_id_idx
    ON striatum_packet_audits (packet_id);

CREATE INDEX striatum_packet_audits_tenant_corpus_created_idx
    ON striatum_packet_audits (tenant_id, corpus_id, created_at DESC);

CREATE INDEX striatum_packet_audits_generation_created_idx
    ON striatum_packet_audits (generation_id, created_at DESC);

CREATE INDEX striatum_packet_audits_status_created_idx
    ON striatum_packet_audits (status, created_at DESC);

CREATE INDEX striatum_packet_audits_selected_gin_idx
    ON striatum_packet_audits USING GIN (selected jsonb_path_ops);

CREATE INDEX striatum_packet_audits_omitted_gin_idx
    ON striatum_packet_audits USING GIN (omitted jsonb_path_ops);

CREATE OR REPLACE FUNCTION fn_striatum_packet_audit_has_payload_key(value JSONB)
RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    key TEXT;
    item JSONB;
BEGIN
    IF value IS NULL THEN
        RETURN false;
    END IF;

    IF jsonb_typeof(value) = 'object' THEN
        FOR key, item IN SELECT * FROM jsonb_each(value) LOOP
            IF key IN (
                'raw_payload',
                'payload',
                'content',
                'content_text',
                'excerpt',
                'summary',
                'body',
                'message_text',
                'transcript'
            ) THEN
                RETURN true;
            END IF;
            IF fn_striatum_packet_audit_has_payload_key(item) THEN
                RETURN true;
            END IF;
        END LOOP;
    ELSIF jsonb_typeof(value) = 'array' THEN
        FOR item IN SELECT * FROM jsonb_array_elements(value) LOOP
            IF fn_striatum_packet_audit_has_payload_key(item) THEN
                RETURN true;
            END IF;
        END LOOP;
    END IF;

    RETURN false;
END;
$$;

CREATE OR REPLACE FUNCTION fn_striatum_packet_audits_validate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    generation_row striatum_projection_generations%ROWTYPE;
    entry JSONB;
    reason TEXT;
BEGIN
    SELECT *
    INTO generation_row
    FROM striatum_projection_generations
    WHERE id = NEW.generation_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'striatum_packet_audits.generation_id does not exist: %',
            NEW.generation_id
            USING ERRCODE = '23503';
    END IF;

    IF (
        generation_row.tenant_id IS DISTINCT FROM NEW.tenant_id
        OR generation_row.corpus_id IS DISTINCT FROM NEW.corpus_id
    ) THEN
        RAISE EXCEPTION
            'striatum packet audit tenant/corpus must match its generation'
            USING ERRCODE = '23514';
    END IF;

    IF fn_striatum_packet_audit_has_payload_key(NEW.selected) THEN
        RAISE EXCEPTION
            'striatum packet audit selected entries must not store payload content'
            USING ERRCODE = '23514';
    END IF;

    IF fn_striatum_packet_audit_has_payload_key(NEW.omitted) THEN
        RAISE EXCEPTION
            'striatum packet audit omitted entries must not store payload content'
            USING ERRCODE = '23514';
    END IF;

    FOR entry IN SELECT * FROM jsonb_array_elements(NEW.selected) LOOP
        IF jsonb_typeof(entry) <> 'object' THEN
            RAISE EXCEPTION
                'striatum packet audit selected entries must be objects'
                USING ERRCODE = '23514';
        END IF;
        IF btrim(COALESCE(entry ->> 'candidate_id', '')) = '' THEN
            RAISE EXCEPTION
                'striatum packet audit selected entries require candidate_id'
                USING ERRCODE = '23514';
        END IF;
        IF entry ->> 'selected' IS DISTINCT FROM 'true' THEN
            RAISE EXCEPTION
                'striatum packet audit selected entries require selected=true'
                USING ERRCODE = '23514';
        END IF;
        IF btrim(COALESCE(entry ->> 'reason', '')) <> '' THEN
            RAISE EXCEPTION
                'striatum packet audit selected entries must not carry omission reasons'
                USING ERRCODE = '23514';
        END IF;
    END LOOP;

    FOR entry IN SELECT * FROM jsonb_array_elements(NEW.omitted) LOOP
        IF jsonb_typeof(entry) <> 'object' THEN
            RAISE EXCEPTION
                'striatum packet audit omitted entries must be objects'
                USING ERRCODE = '23514';
        END IF;
        IF btrim(COALESCE(entry ->> 'candidate_id', '')) = '' THEN
            RAISE EXCEPTION
                'striatum packet audit omitted entries require candidate_id'
                USING ERRCODE = '23514';
        END IF;
        IF entry ->> 'selected' IS DISTINCT FROM 'false' THEN
            RAISE EXCEPTION
                'striatum packet audit omitted entries require selected=false'
                USING ERRCODE = '23514';
        END IF;

        reason := entry ->> 'reason';
        IF reason NOT IN (
            'disabled',
            'unavailable',
            'unauthorized',
            'timeout',
            'malformed',
            'pair_mismatch',
            'privacy_tier_exceeded',
            'redaction_withheld',
            'missing_citation',
            'identity_leak',
            'citation_leak',
            'stale_rejected',
            'current_state_conflict',
            'low_score',
            'over_budget',
            'duplicate',
            'unsupported_surface',
            'generated_product_blocked'
        ) THEN
            RAISE EXCEPTION
                'striatum packet audit omitted reason is not in the closed vocabulary: %',
                reason
                USING ERRCODE = '23514';
        END IF;
    END LOOP;

    RETURN NEW;
END;
$$;

CREATE TRIGGER striatum_packet_audits_validate
    BEFORE INSERT OR UPDATE ON striatum_packet_audits
    FOR EACH ROW EXECUTE FUNCTION fn_striatum_packet_audits_validate();

CREATE OR REPLACE FUNCTION fn_striatum_packet_audits_append_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'striatum_packet_audits is append-only; % is not allowed',
        TG_OP
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER striatum_packet_audits_append_only
    BEFORE UPDATE OR DELETE ON striatum_packet_audits
    FOR EACH ROW EXECUTE FUNCTION fn_striatum_packet_audits_append_only();
