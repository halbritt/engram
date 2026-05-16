-- RFC 0050 Layer 1: add source_kind='git' and project-event tables.

ALTER TYPE source_kind ADD VALUE IF NOT EXISTS 'git';

CREATE TABLE IF NOT EXISTS git_commits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    repository_id TEXT NOT NULL,
    commit_sha TEXT NOT NULL CHECK (commit_sha ~ '^[0-9a-f]{40}$'),
    tree_sha TEXT NOT NULL CHECK (tree_sha ~ '^[0-9a-f]{40}$'),
    parent_shas TEXT[] NOT NULL DEFAULT '{}'::text[],
    author_name TEXT NULL,
    author_email TEXT NULL,
    committer_name TEXT NULL,
    committer_email TEXT NULL,
    author_date TIMESTAMPTZ NOT NULL,
    committer_date TIMESTAMPTZ NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    refs TEXT[] NOT NULL DEFAULT '{}'::text[],
    content_hash TEXT NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    adapter_version TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    privacy_tier INT NOT NULL DEFAULT 1,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(raw_payload) = 'object'),
    CONSTRAINT git_commits_tenant_id_nonempty CHECK (btrim(tenant_id) <> ''),
    CONSTRAINT git_commits_corpus_id_nonempty CHECK (btrim(corpus_id) <> ''),
    CONSTRAINT git_commits_repository_id_nonempty CHECK (btrim(repository_id) <> ''),
    CONSTRAINT git_commits_adapter_version_nonempty CHECK (btrim(adapter_version) <> ''),
    UNIQUE (tenant_id, corpus_id, repository_id, commit_sha)
);

CREATE INDEX IF NOT EXISTS git_commits_commit_sha_idx
    ON git_commits (commit_sha);

CREATE INDEX IF NOT EXISTS git_commits_tenant_corpus_idx
    ON git_commits (tenant_id, corpus_id, repository_id, committer_date DESC);

CREATE TABLE IF NOT EXISTS git_commit_paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commit_id UUID NOT NULL REFERENCES git_commits(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    change_index INT NOT NULL CHECK (change_index >= 0),
    change_kind TEXT NOT NULL CHECK (change_kind IN
        ('add','modify','delete','rename','copy','typechange','unknown')),
    old_path TEXT NULL,
    new_path TEXT NULL,
    additions INT NULL CHECK (additions IS NULL OR additions >= 0),
    deletions INT NULL CHECK (deletions IS NULL OR deletions >= 0),
    is_binary BOOLEAN NOT NULL DEFAULT false,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(raw_payload) = 'object'),
    UNIQUE (commit_id, change_index)
);

CREATE INDEX IF NOT EXISTS git_commit_paths_new_path_idx
    ON git_commit_paths (tenant_id, corpus_id, new_path);

CREATE INDEX IF NOT EXISTS git_commit_paths_old_path_idx
    ON git_commit_paths (tenant_id, corpus_id, old_path)
    WHERE old_path IS NOT NULL;

-- Append-only enforcement: Layer 1 disallows UPDATE/DELETE on git rows.
-- Future layers may add a `superseded_at` carve-out when retrieval lifecycle
-- needs to tombstone force-pushed history.

CREATE OR REPLACE FUNCTION prevent_git_commits_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'git_commits rows are append-only (RFC 0050 Layer 1)';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS git_commits_no_update ON git_commits;
CREATE TRIGGER git_commits_no_update
    BEFORE UPDATE ON git_commits
    FOR EACH ROW
    EXECUTE FUNCTION prevent_git_commits_mutation();

DROP TRIGGER IF EXISTS git_commits_no_delete ON git_commits;
CREATE TRIGGER git_commits_no_delete
    BEFORE DELETE ON git_commits
    FOR EACH ROW
    EXECUTE FUNCTION prevent_git_commits_mutation();

CREATE OR REPLACE FUNCTION prevent_git_commit_paths_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'git_commit_paths rows are append-only (RFC 0050 Layer 1)';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS git_commit_paths_no_update ON git_commit_paths;
CREATE TRIGGER git_commit_paths_no_update
    BEFORE UPDATE ON git_commit_paths
    FOR EACH ROW
    EXECUTE FUNCTION prevent_git_commit_paths_mutation();

DROP TRIGGER IF EXISTS git_commit_paths_no_delete ON git_commit_paths;
CREATE TRIGGER git_commit_paths_no_delete
    BEFORE DELETE ON git_commit_paths
    FOR EACH ROW
    EXECUTE FUNCTION prevent_git_commit_paths_mutation();
