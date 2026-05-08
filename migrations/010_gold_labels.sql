-- RFC 0021: Gold-Set Interview Curation
-- Decision refs: D044, D052, D057, D069, D073, D077, D078, D079
--
-- Forward-only migration. Adds the parent gold-label session table, the
-- append-only gold_labels table, the strata and verdict vocabularies, the
-- four named triggers (append-only, target validation, privacy-tier carry),
-- the per-target-kind partial indexes, and the current_gold_label view.

CREATE TABLE gold_label_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seed BIGINT NOT NULL,
    sampler_id TEXT NOT NULL,
    sampler_version TEXT NOT NULL,
    strata_weights JSONB NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    operator_note TEXT NULL
);

CREATE INDEX gold_label_sessions_started_at_idx
    ON gold_label_sessions (started_at DESC);
CREATE INDEX gold_label_sessions_open_idx
    ON gold_label_sessions (started_at DESC)
    WHERE completed_at IS NULL;


CREATE TABLE gold_label_strata_vocabulary (
    stratum_kind TEXT NOT NULL,
    key TEXT NOT NULL,
    display TEXT NOT NULL,
    PRIMARY KEY (stratum_kind, key)
);

INSERT INTO gold_label_strata_vocabulary (stratum_kind, key, display)
VALUES
    ('stability_class', 'identity', 'identity'),
    ('stability_class', 'preference', 'preference'),
    ('stability_class', 'project_status', 'project_status'),
    ('stability_class', 'goal', 'goal'),
    ('stability_class', 'task', 'task'),
    ('stability_class', 'mood', 'mood'),
    ('stability_class', 'relationship', 'relationship'),
    ('conf_band', '0.0-0.2', 'confidence in [0.0, 0.2)'),
    ('conf_band', '0.2-0.4', 'confidence in [0.2, 0.4)'),
    ('conf_band', '0.4-0.6', 'confidence in [0.4, 0.6)'),
    ('conf_band', '0.6-0.8', 'confidence in [0.6, 0.8)'),
    ('conf_band', '0.8-1.0', 'confidence in [0.8, 1.0]'),
    ('recency_band', '<7d', 'observed within the last 7 days'),
    ('recency_band', '<30d', 'observed within the last 30 days'),
    ('recency_band', '<90d', 'observed within the last 90 days'),
    ('recency_band', '<365d', 'observed within the last 365 days'),
    ('recency_band', '>=365d', 'observed at least 365 days ago'),
    ('belief_status', 'candidate', 'belief is a candidate'),
    ('belief_status', 'provisional', 'belief is provisional'),
    ('belief_status', 'accepted', 'belief is accepted');


CREATE TABLE gold_label_verdict_vocabulary (
    verdict TEXT PRIMARY KEY,
    gloss TEXT NOT NULL,
    ordinal INT NOT NULL
);

INSERT INTO gold_label_verdict_vocabulary (verdict, gloss, ordinal)
VALUES
    ('true', 'claim/belief is correct about the world', 1),
    ('false', 'claim/belief is wrong about the world', 2),
    ('stale', 'was true at evidence time, no longer true', 3),
    ('unsupported', 'evidence does not establish claim, regardless of world truth', 4),
    ('unsure', 'user cannot rule', 5),
    ('skip', 'user advances without ruling (cooldown-free)', 6);


CREATE TABLE gold_labels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES gold_label_sessions(session_id),
    target_kind TEXT NOT NULL CHECK (target_kind IN ('claim', 'belief')),
    target_id UUID NOT NULL,

    -- Typed version triple. Exactly one of the two triples is populated,
    -- selected by target_kind. request_profile_version is required in both
    -- shapes.
    extraction_prompt_version TEXT NULL,
    extraction_model_version TEXT NULL,
    consolidation_prompt_version TEXT NULL,
    consolidation_model_version TEXT NULL,
    request_profile_version TEXT NOT NULL,

    prompt_template_version TEXT NOT NULL,
    prompt_template_path TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    evidence_excerpt TEXT NULL,

    verdict TEXT NOT NULL REFERENCES gold_label_verdict_vocabulary(verdict),
    rationale TEXT NULL CHECK (rationale IS NULL OR length(rationale) <= 2000),

    sampler_id TEXT NOT NULL,
    sampler_version TEXT NOT NULL,
    candidate_pool_snapshot_id UUID NOT NULL,
    active_learning_signal_version TEXT NULL,

    stability_class TEXT NOT NULL,
    conf_band TEXT NOT NULL,
    recency_band TEXT NOT NULL,
    belief_status TEXT NULL,
    strata_extra JSONB NOT NULL DEFAULT '{}'::jsonb,

    asked_at TIMESTAMPTZ NOT NULL,
    answered_at TIMESTAMPTZ NOT NULL,
    privacy_tier INT NOT NULL,

    CONSTRAINT chk_gold_labels_version_triple CHECK (
        (
            target_kind = 'claim'
            AND extraction_prompt_version IS NOT NULL
            AND extraction_model_version IS NOT NULL
            AND consolidation_prompt_version IS NULL
            AND consolidation_model_version IS NULL
        )
        OR (
            target_kind = 'belief'
            AND consolidation_prompt_version IS NOT NULL
            AND consolidation_model_version IS NOT NULL
            AND extraction_prompt_version IS NULL
            AND extraction_model_version IS NULL
        )
    ),
    CONSTRAINT chk_gold_labels_template_path_matches_version CHECK (
        position(
            split_part(prompt_template_version, '.', 3) IN prompt_template_path
        ) > 0
        OR position(prompt_template_version IN prompt_template_path) > 0
        OR position(
            replace(prompt_template_version, '.', '_') IN prompt_template_path
        ) > 0
    )
);

CREATE INDEX idx_gold_labels_claim_triple
    ON gold_labels (
        target_id,
        extraction_prompt_version,
        extraction_model_version,
        request_profile_version
    )
    WHERE target_kind = 'claim';

CREATE INDEX idx_gold_labels_belief_triple
    ON gold_labels (
        target_id,
        consolidation_prompt_version,
        consolidation_model_version,
        request_profile_version
    )
    WHERE target_kind = 'belief';

CREATE INDEX idx_gold_labels_session_id ON gold_labels (session_id);
CREATE INDEX idx_gold_labels_asked_at ON gold_labels (asked_at);
CREATE INDEX idx_gold_labels_target ON gold_labels (target_kind, target_id);


CREATE OR REPLACE FUNCTION fn_gold_labels_append_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'gold_labels is append-only; % is not allowed', TG_OP
        USING ERRCODE = 'P0001';
END;
$$;

CREATE TRIGGER gold_labels_append_only
    BEFORE UPDATE OR DELETE ON gold_labels
    FOR EACH ROW EXECUTE FUNCTION fn_gold_labels_append_only();


CREATE OR REPLACE FUNCTION fn_gold_labels_validate_target()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_exists BOOLEAN;
BEGIN
    IF NEW.target_kind = 'claim' THEN
        IF NEW.extraction_prompt_version IS NULL
            OR NEW.extraction_model_version IS NULL
            OR NEW.consolidation_prompt_version IS NOT NULL
            OR NEW.consolidation_model_version IS NOT NULL
        THEN
            RAISE EXCEPTION
                'gold_labels target_kind=claim requires the extraction triple and NULL consolidation columns'
                USING ERRCODE = 'P0001';
        END IF;
        SELECT EXISTS (SELECT 1 FROM claims WHERE id = NEW.target_id) INTO target_exists;
        IF NOT target_exists THEN
            RAISE EXCEPTION
                'gold_labels target_id % not found in claims', NEW.target_id
                USING ERRCODE = 'P0001';
        END IF;
    ELSIF NEW.target_kind = 'belief' THEN
        IF NEW.consolidation_prompt_version IS NULL
            OR NEW.consolidation_model_version IS NULL
            OR NEW.extraction_prompt_version IS NOT NULL
            OR NEW.extraction_model_version IS NOT NULL
        THEN
            RAISE EXCEPTION
                'gold_labels target_kind=belief requires the consolidation triple and NULL extraction columns'
                USING ERRCODE = 'P0001';
        END IF;
        SELECT EXISTS (SELECT 1 FROM beliefs WHERE id = NEW.target_id) INTO target_exists;
        IF NOT target_exists THEN
            RAISE EXCEPTION
                'gold_labels target_id % not found in beliefs', NEW.target_id
                USING ERRCODE = 'P0001';
        END IF;
    ELSE
        RAISE EXCEPTION 'gold_labels unknown target_kind: %', NEW.target_kind
            USING ERRCODE = 'P0001';
    END IF;

    RETURN NEW;
END;
$$;

-- Rename trigger to fire BEFORE the privacy-tier carry trigger. PostgreSQL
-- runs same-event row triggers in alphabetical order by trigger name, so the
-- 00 prefix guarantees validate_target runs first and emits "not found in
-- claims/beliefs" before the carry trigger has a chance to complain about a
-- missing parent row.
CREATE TRIGGER gold_labels_00_validate_target
    BEFORE INSERT ON gold_labels
    FOR EACH ROW EXECUTE FUNCTION fn_gold_labels_validate_target();


CREATE OR REPLACE FUNCTION fn_gold_labels_carry_privacy_tier()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    parent_tier INT;
BEGIN
    IF NEW.target_kind = 'claim' THEN
        SELECT privacy_tier INTO parent_tier FROM claims WHERE id = NEW.target_id;
    ELSIF NEW.target_kind = 'belief' THEN
        SELECT privacy_tier INTO parent_tier FROM beliefs WHERE id = NEW.target_id;
    ELSE
        RAISE EXCEPTION 'gold_labels unknown target_kind: %', NEW.target_kind
            USING ERRCODE = 'P0001';
    END IF;

    IF parent_tier IS NULL THEN
        RAISE EXCEPTION
            'gold_labels could not resolve privacy_tier for %=%',
            NEW.target_kind,
            NEW.target_id
            USING ERRCODE = 'P0001';
    END IF;

    IF NEW.privacy_tier IS NOT NULL AND NEW.privacy_tier <> parent_tier THEN
        RAISE EXCEPTION
            'gold_labels privacy_tier % disagrees with parent %=% tier %',
            NEW.privacy_tier,
            NEW.target_kind,
            NEW.target_id,
            parent_tier
            USING ERRCODE = 'P0001';
    END IF;

    NEW.privacy_tier := parent_tier;
    RETURN NEW;
END;
$$;

CREATE TRIGGER gold_labels_01_carry_privacy_tier
    BEFORE INSERT ON gold_labels
    FOR EACH ROW EXECUTE FUNCTION fn_gold_labels_carry_privacy_tier();


-- current_gold_label: latest verdict per (target_kind, target_id, version_triple)
-- with verdict-rank tiebreak. true|false|stale|unsupported outrank unsure|skip.
CREATE VIEW current_gold_label AS
SELECT
    id,
    session_id,
    target_kind,
    target_id,
    extraction_prompt_version,
    extraction_model_version,
    consolidation_prompt_version,
    consolidation_model_version,
    request_profile_version,
    prompt_template_version,
    prompt_template_path,
    prompt_text,
    evidence_excerpt,
    verdict,
    rationale,
    sampler_id,
    sampler_version,
    candidate_pool_snapshot_id,
    active_learning_signal_version,
    stability_class,
    conf_band,
    recency_band,
    belief_status,
    strata_extra,
    asked_at,
    answered_at,
    privacy_tier
FROM (
    SELECT
        gl.*,
        ROW_NUMBER() OVER (
            PARTITION BY
                gl.target_kind,
                gl.target_id,
                COALESCE(gl.extraction_prompt_version, ''),
                COALESCE(gl.extraction_model_version, ''),
                COALESCE(gl.consolidation_prompt_version, ''),
                COALESCE(gl.consolidation_model_version, ''),
                gl.request_profile_version
            ORDER BY
                gl.answered_at DESC,
                CASE gl.verdict
                    WHEN 'true' THEN 0
                    WHEN 'false' THEN 0
                    WHEN 'stale' THEN 0
                    WHEN 'unsupported' THEN 0
                    ELSE 1
                END
        ) AS rn
    FROM gold_labels gl
) ranked
WHERE rn = 1;
