-- 013_interview_active_learning_state.sql
-- Phase 3 interview follow-on: persist active-learning enablement locally and
-- carry active-learning/confidence metadata through materialized session rows.

CREATE TABLE gold_label_active_learning_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_version TEXT NOT NULL CHECK (length(btrim(signal_version)) > 0),
    enabled_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_gold_label_active_learning_events_enabled_at
    ON gold_label_active_learning_events (enabled_at DESC);

CREATE OR REPLACE FUNCTION fn_gold_label_active_learning_events_append_only()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'gold_label_active_learning_events is append-only; % is not allowed', TG_OP
        USING ERRCODE = 'P0001';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER gold_label_active_learning_events_00_append_only
    BEFORE UPDATE OR DELETE ON gold_label_active_learning_events
    FOR EACH ROW EXECUTE FUNCTION fn_gold_label_active_learning_events_append_only();

ALTER TABLE gold_label_session_targets
    ADD COLUMN active_learning_signal_version TEXT NULL,
    ADD COLUMN confidence DOUBLE PRECISION NULL CHECK (
        confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)
    ),
    ADD COLUMN observed_at TIMESTAMPTZ NULL;

ALTER TABLE gold_label_session_targets
    DISABLE TRIGGER gold_label_session_targets_00_append_only;

UPDATE gold_label_session_targets t
SET confidence = c.confidence,
    observed_at = c.extracted_at
FROM claims c
WHERE t.target_kind = 'claim'
  AND t.target_id = c.id;

UPDATE gold_label_session_targets t
SET confidence = b.confidence,
    observed_at = b.observed_at
FROM beliefs b
WHERE t.target_kind = 'belief'
  AND t.target_id = b.id;

ALTER TABLE gold_label_session_targets
    ENABLE TRIGGER gold_label_session_targets_00_append_only;
