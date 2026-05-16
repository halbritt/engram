-- RFC 0050 Layer 2: add source_kind='build_artifact' and build-artifact tables.

ALTER TYPE source_kind ADD VALUE IF NOT EXISTS 'build_artifact';

CREATE TABLE IF NOT EXISTS build_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    artifact_root_id TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    artifact_kind TEXT NOT NULL CHECK (artifact_kind IN
        ('junit_xml','coverage_report','benchmark_json','lint_report','log_file','other')),
    content_hash TEXT NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    artifact_mtime TIMESTAMPTZ NULL,
    run_id TEXT NULL,
    commit_sha TEXT NULL,
    adapter_version TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    privacy_tier INT NOT NULL DEFAULT 1,
    sensitivity_class TEXT NOT NULL DEFAULT 'routine_project'
        CHECK (sensitivity_class IN
            ('routine_project','personal_private','third_party_communication',
             'calendar_contact','behavioral_activity','raw_media','exact_location',
             'health','biometric','finance','credential_or_secret_reference')),
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(raw_payload) = 'object'),
    CONSTRAINT build_artifacts_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    CONSTRAINT build_artifacts_corpus_id_nonempty CHECK (btrim(corpus_id) <> ''),
    CONSTRAINT build_artifacts_root_id_nonempty CHECK (btrim(artifact_root_id) <> ''),
    CONSTRAINT build_artifacts_path_nonempty CHECK (btrim(relative_path) <> ''),
    UNIQUE (tenant_id, corpus_id, artifact_root_id, relative_path, content_hash)
);

CREATE INDEX IF NOT EXISTS build_artifacts_kind_idx
    ON build_artifacts (tenant_id, corpus_id, artifact_kind, imported_at DESC);

CREATE INDEX IF NOT EXISTS build_artifacts_commit_sha_idx
    ON build_artifacts (commit_sha)
    WHERE commit_sha IS NOT NULL;

CREATE INDEX IF NOT EXISTS build_artifacts_run_id_idx
    ON build_artifacts (run_id)
    WHERE run_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS build_artifact_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES build_artifacts(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    finding_index INT NOT NULL CHECK (finding_index >= 0),
    finding_kind TEXT NOT NULL CHECK (finding_kind IN
        ('test_case','coverage_summary','coverage_file','benchmark','lint_finding',
         'log_summary','log_chunk','redaction_marker')),
    status TEXT NULL,
    name TEXT NULL,
    file_path TEXT NULL,
    line_number INT NULL CHECK (line_number IS NULL OR line_number >= 0),
    column_number INT NULL CHECK (column_number IS NULL OR column_number >= 0),
    duration_ms NUMERIC NULL CHECK (duration_ms IS NULL OR duration_ms >= 0),
    severity TEXT NULL,
    message TEXT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(raw_payload) = 'object'),
    UNIQUE (artifact_id, finding_index)
);

CREATE INDEX IF NOT EXISTS build_artifact_findings_file_idx
    ON build_artifact_findings (tenant_id, corpus_id, file_path)
    WHERE file_path IS NOT NULL;

CREATE INDEX IF NOT EXISTS build_artifact_findings_kind_idx
    ON build_artifact_findings (tenant_id, corpus_id, finding_kind);

-- Append-only enforcement.
CREATE OR REPLACE FUNCTION prevent_build_artifacts_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'build_artifacts rows are append-only (RFC 0050 Layer 2)';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS build_artifacts_no_update ON build_artifacts;
CREATE TRIGGER build_artifacts_no_update
    BEFORE UPDATE ON build_artifacts
    FOR EACH ROW
    EXECUTE FUNCTION prevent_build_artifacts_mutation();

DROP TRIGGER IF EXISTS build_artifacts_no_delete ON build_artifacts;
CREATE TRIGGER build_artifacts_no_delete
    BEFORE DELETE ON build_artifacts
    FOR EACH ROW
    EXECUTE FUNCTION prevent_build_artifacts_mutation();

CREATE OR REPLACE FUNCTION prevent_build_artifact_findings_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'build_artifact_findings rows are append-only (RFC 0050 Layer 2)';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS build_artifact_findings_no_update ON build_artifact_findings;
CREATE TRIGGER build_artifact_findings_no_update
    BEFORE UPDATE ON build_artifact_findings
    FOR EACH ROW
    EXECUTE FUNCTION prevent_build_artifact_findings_mutation();

DROP TRIGGER IF EXISTS build_artifact_findings_no_delete ON build_artifact_findings;
CREATE TRIGGER build_artifact_findings_no_delete
    BEFORE DELETE ON build_artifact_findings
    FOR EACH ROW
    EXECUTE FUNCTION prevent_build_artifact_findings_mutation();
