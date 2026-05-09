-- 011_gold_label_session_targets.sql
-- RFC 0027 § Persistent target order. Materializes the sampled order at
-- session creation so the web UI can index into it by URL idx without
-- re-sampling on every request (F004 / F009 / F010 / F016).

CREATE TABLE gold_label_session_targets (
    session_id UUID NOT NULL
        REFERENCES gold_label_sessions(session_id) ON DELETE CASCADE,
    idx INT NOT NULL CHECK (idx >= 0),  -- 0-indexed in the table; URL is 1-indexed
    target_kind TEXT NOT NULL CHECK (target_kind IN ('claim', 'belief')),
    target_id UUID NOT NULL,
    candidate_pool_snapshot_id UUID NOT NULL,
    -- Typed version triple stamped at session creation (F010 / O002).
    -- Same shape as gold_labels: extraction triple iff target_kind=claim,
    -- consolidation triple iff target_kind=belief, request_profile_version always.
    extraction_prompt_version TEXT NULL,
    extraction_model_version TEXT NULL,
    consolidation_prompt_version TEXT NULL,
    consolidation_model_version TEXT NULL,
    request_profile_version TEXT NOT NULL,
    stability_class TEXT NOT NULL,
    conf_band TEXT NOT NULL,
    recency_band TEXT NOT NULL,
    belief_status TEXT NULL,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, idx),
    CONSTRAINT chk_session_targets_version_triple CHECK (
        (target_kind = 'claim'
            AND extraction_prompt_version IS NOT NULL
            AND extraction_model_version IS NOT NULL
            AND consolidation_prompt_version IS NULL
            AND consolidation_model_version IS NULL)
        OR
        (target_kind = 'belief'
            AND consolidation_prompt_version IS NOT NULL
            AND consolidation_model_version IS NOT NULL
            AND extraction_prompt_version IS NULL
            AND extraction_model_version IS NULL)
    )
);

CREATE INDEX idx_session_targets_session_id
    ON gold_label_session_targets (session_id);
CREATE INDEX idx_session_targets_target
    ON gold_label_session_targets (target_kind, target_id);

-- Append-only at the schema layer (mirrors gold_labels pattern from migration 010).
CREATE OR REPLACE FUNCTION fn_gold_label_session_targets_append_only()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'gold_label_session_targets is append-only; % is not allowed', TG_OP
        USING ERRCODE = 'P0001';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER gold_label_session_targets_00_append_only
    BEFORE UPDATE OR DELETE ON gold_label_session_targets
    FOR EACH ROW EXECUTE FUNCTION fn_gold_label_session_targets_append_only();
