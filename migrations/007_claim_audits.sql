-- RFC 0018: evidence-to-claim audit cascade.
-- Adds three append-only tables that record advisory audit verdicts over
-- already-extracted claims and over projection-level outputs. Strictly
-- additive: no changes to claims, beliefs, belief_audit, or
-- claim_extractions. Verdicts surface as joinable status, not column
-- updates on existing tables (D069). The reviewer/LLM-calling code is
-- out of scope for this migration; the schema simply gives the cascade
-- a place to write data when the reviewer is built post-Step-5.

CREATE TABLE IF NOT EXISTS audit_reason_vocabulary (
    reason TEXT PRIMARY KEY,
    stage SMALLINT NOT NULL CHECK (stage IN (1, 2, 3)),
    description TEXT NOT NULL,
    precludes_supported BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS audit_reason_vocabulary_stage_idx
    ON audit_reason_vocabulary (stage);

INSERT INTO audit_reason_vocabulary (reason, stage, description, precludes_supported)
VALUES
    ('trace_broken', 1, 'Cited evidence does not contain the claim.', TRUE),
    ('trace_partial', 1, 'Cited evidence partially supports the claim.', FALSE),
    ('class_overclaim', 1, 'stability_class overstates evidence span.', FALSE),
    ('class_underclaim', 1, 'stability_class understates evidence span.', FALSE),
    ('predicate_misrouted', 1, 'Predicate cardinality wrong for the fact.', TRUE),
    ('scope_inflated', 1, 'Claim generalizes beyond evidence temporal window.', FALSE),
    ('confidence_inflated', 1, 'High-confidence claim with weak trace.', FALSE),
    ('evidence_synthesized', 1, 'Cited evidence appears model-generated rather than corpus-derived.', TRUE),
    ('value_mismatch', 2, 'Claim value disagrees with evidence content.', FALSE),
    ('numerical_mismatch', 3, 'Projection number disagrees with claim.', FALSE),
    ('cite_invalid', 3, 'Projection cites a claim that does not exist or is invalidated.', FALSE),
    ('cite_misapplied', 3, 'Cited claim does not establish the projection assertion.', FALSE),
    ('privacy_tier_leak', 3, 'Projection surfaces evidence above the claimed tier.', FALSE)
ON CONFLICT (reason) DO NOTHING;

CREATE TABLE IF NOT EXISTS claim_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id),
    stage SMALLINT NOT NULL CHECK (stage IN (1, 2)),
    verdict TEXT NULL CHECK (
        verdict IS NULL
        OR verdict IN ('supported', 'partial', 'invalidated')
    ),
    audit_reasons TEXT[] NOT NULL DEFAULT '{}'::text[],
    auditor_model_version TEXT NOT NULL,
    auditor_prompt_version TEXT NOT NULL,
    audited_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (
        (stage = 1 AND verdict IS NULL)
        OR (stage = 2 AND verdict IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS claim_audits_claim_stage_idx
    ON claim_audits (claim_id, stage);
CREATE INDEX IF NOT EXISTS claim_audits_reasons_gin_idx
    ON claim_audits USING gin (audit_reasons);
CREATE INDEX IF NOT EXISTS claim_audits_auditor_version_idx
    ON claim_audits (auditor_model_version, auditor_prompt_version);

CREATE OR REPLACE FUNCTION fn_claim_audits_validate_reasons()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    reason_value TEXT;
    reason_stage SMALLINT;
BEGIN
    -- Stage 1 reasons must accompany stage=1 rows; Stage 2 reasons must
    -- accompany stage=2 rows. Stage 3 reasons are not valid on
    -- claim-level audits — they belong to projection_audits.
    FOREACH reason_value IN ARRAY NEW.audit_reasons LOOP
        SELECT stage INTO reason_stage
        FROM audit_reason_vocabulary
        WHERE reason = reason_value;

        IF NOT FOUND THEN
            RAISE EXCEPTION
                'unknown audit reason: %',
                reason_value
                USING ERRCODE = '23503';
        END IF;

        IF reason_stage <> NEW.stage THEN
            RAISE EXCEPTION
                'audit reason % belongs to stage %, not stage %',
                reason_value,
                reason_stage,
                NEW.stage
                USING ERRCODE = '23514';
        END IF;
    END LOOP;

    RETURN NEW;
END;
$$;

CREATE TRIGGER claim_audits_validate_reasons
    BEFORE INSERT ON claim_audits
    FOR EACH ROW EXECUTE FUNCTION fn_claim_audits_validate_reasons();

CREATE OR REPLACE FUNCTION fn_claim_audits_append_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'claim_audits is append-only; % is not allowed',
        TG_OP
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER claim_audits_append_only
    BEFORE UPDATE OR DELETE ON claim_audits
    FOR EACH ROW EXECUTE FUNCTION fn_claim_audits_append_only();

CREATE TABLE IF NOT EXISTS projection_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projection_kind TEXT NOT NULL,
    projection_ref TEXT NOT NULL,
    cited_claim_ids UUID[] NOT NULL CHECK (cardinality(cited_claim_ids) > 0),
    verdict TEXT NOT NULL CHECK (verdict IN ('clean', 'warnings', 'failed')),
    audit_reasons TEXT[] NOT NULL DEFAULT '{}'::text[],
    auditor_model_version TEXT NOT NULL,
    auditor_prompt_version TEXT NOT NULL,
    audited_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS projection_audits_kind_ref_idx
    ON projection_audits (projection_kind, projection_ref, audited_at DESC);
CREATE INDEX IF NOT EXISTS projection_audits_cited_claim_ids_gin_idx
    ON projection_audits USING gin (cited_claim_ids);

CREATE OR REPLACE FUNCTION fn_projection_audits_validate_reasons()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    reason_value TEXT;
BEGIN
    -- Projection-level reasons may draw from any stage in the
    -- vocabulary; the cascade's Stage 3 reasons are the typical case
    -- but Stage 1 / Stage 2 reasons can surface in projection findings
    -- when a projection inherits a claim-level defect.
    FOREACH reason_value IN ARRAY NEW.audit_reasons LOOP
        IF NOT EXISTS (
            SELECT 1 FROM audit_reason_vocabulary WHERE reason = reason_value
        ) THEN
            RAISE EXCEPTION
                'unknown audit reason: %',
                reason_value
                USING ERRCODE = '23503';
        END IF;
    END LOOP;

    RETURN NEW;
END;
$$;

CREATE TRIGGER projection_audits_validate_reasons
    BEFORE INSERT ON projection_audits
    FOR EACH ROW EXECUTE FUNCTION fn_projection_audits_validate_reasons();

CREATE OR REPLACE FUNCTION fn_projection_audits_append_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'projection_audits is append-only; % is not allowed',
        TG_OP
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER projection_audits_append_only
    BEFORE UPDATE OR DELETE ON projection_audits
    FOR EACH ROW EXECUTE FUNCTION fn_projection_audits_append_only();
