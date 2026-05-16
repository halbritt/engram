-- RFC 0050 Layer 6: operational family `source_audit`.
--
-- Every importer invocation records one row capturing the input signature
-- (root path + hash), outcome, and counts. The audit table is append-only;
-- audit reconstruction reads from it without touching raw_payload bodies on
-- the importer-specific tables.

CREATE TABLE IF NOT EXISTS source_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    source_kind source_kind NOT NULL,
    source_id UUID NULL REFERENCES sources(id),
    adapter_version TEXT NOT NULL,
    input_signature TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('ok','partial','failed','dry_run')),
    rows_inserted INT NOT NULL DEFAULT 0 CHECK (rows_inserted >= 0),
    rows_skipped INT NOT NULL DEFAULT 0 CHECK (rows_skipped >= 0),
    rows_tombstoned INT NOT NULL DEFAULT 0 CHECK (rows_tombstoned >= 0),
    coverage_gap_count INT NOT NULL DEFAULT 0 CHECK (coverage_gap_count >= 0),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(raw_payload) = 'object'),
    CONSTRAINT source_audits_tenant_nonempty CHECK (btrim(tenant_id) <> ''),
    CONSTRAINT source_audits_corpus_nonempty CHECK (btrim(corpus_id) <> ''),
    CONSTRAINT source_audits_signature_nonempty CHECK (btrim(input_signature) <> '')
);

CREATE INDEX IF NOT EXISTS source_audits_kind_completed_idx
    ON source_audits (tenant_id, corpus_id, source_kind, completed_at DESC);

CREATE INDEX IF NOT EXISTS source_audits_source_idx
    ON source_audits (source_id)
    WHERE source_id IS NOT NULL;

CREATE OR REPLACE FUNCTION prevent_source_audits_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'source_audits rows are append-only (RFC 0050 Layer 6)';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS source_audits_no_update ON source_audits;
CREATE TRIGGER source_audits_no_update
    BEFORE UPDATE ON source_audits
    FOR EACH ROW
    EXECUTE FUNCTION prevent_source_audits_mutation();

DROP TRIGGER IF EXISTS source_audits_no_delete ON source_audits;
CREATE TRIGGER source_audits_no_delete
    BEFORE DELETE ON source_audits
    FOR EACH ROW
    EXECUTE FUNCTION prevent_source_audits_mutation();
