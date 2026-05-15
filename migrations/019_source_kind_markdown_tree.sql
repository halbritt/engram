-- RFC 0050 Layer 3: add source_kind='markdown_tree' and document tables.

ALTER TYPE source_kind ADD VALUE IF NOT EXISTS 'markdown_tree';

CREATE TABLE IF NOT EXISTS markdown_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES sources(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    markdown_root_id TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    content_hash TEXT NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    file_mtime TIMESTAMPTZ NULL,
    title TEXT NULL,
    frontmatter JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(frontmatter) = 'object'),
    body_text TEXT NOT NULL DEFAULT '',
    adapter_version TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    privacy_tier INT NOT NULL DEFAULT 1,
    sensitivity_class TEXT NOT NULL DEFAULT 'routine_project'
        CHECK (sensitivity_class IN
            ('routine_project','personal_private','third_party_communication',
             'calendar_contact','behavioral_activity','raw_media','exact_location',
             'health','biometric','finance','credential_or_secret_reference')),
    superseded_at TIMESTAMPTZ NULL,
    superseded_by UUID NULL REFERENCES markdown_files(id),
    CONSTRAINT markdown_files_tenant_nonempty CHECK (btrim(tenant_id) <> ''),
    CONSTRAINT markdown_files_corpus_nonempty CHECK (btrim(corpus_id) <> ''),
    CONSTRAINT markdown_files_root_nonempty CHECK (btrim(markdown_root_id) <> ''),
    CONSTRAINT markdown_files_path_nonempty CHECK (btrim(relative_path) <> ''),
    UNIQUE (tenant_id, corpus_id, markdown_root_id, relative_path, content_hash)
);

CREATE INDEX IF NOT EXISTS markdown_files_active_idx
    ON markdown_files (tenant_id, corpus_id, markdown_root_id, relative_path)
    WHERE superseded_at IS NULL;

CREATE INDEX IF NOT EXISTS markdown_files_root_idx
    ON markdown_files (tenant_id, corpus_id, markdown_root_id, imported_at DESC);

CREATE TABLE IF NOT EXISTS markdown_file_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES markdown_files(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    chunk_index INT NOT NULL CHECK (chunk_index >= 0),
    heading_level INT NULL CHECK (heading_level IS NULL OR (heading_level >= 1 AND heading_level <= 6)),
    heading_anchor TEXT NULL,
    heading_text TEXT NULL,
    body_text TEXT NOT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(raw_payload) = 'object'),
    UNIQUE (file_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS markdown_file_chunks_anchor_idx
    ON markdown_file_chunks (tenant_id, corpus_id, heading_anchor)
    WHERE heading_anchor IS NOT NULL;

CREATE TABLE IF NOT EXISTS markdown_file_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES markdown_files(id),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    link_index INT NOT NULL CHECK (link_index >= 0),
    link_kind TEXT NOT NULL CHECK (link_kind IN
        ('inline_url','reference','wikilink','image','autolink','tag','footnote')),
    text TEXT NULL,
    target TEXT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(raw_payload) = 'object'),
    UNIQUE (file_id, link_index)
);

CREATE INDEX IF NOT EXISTS markdown_file_links_target_idx
    ON markdown_file_links (tenant_id, corpus_id, target)
    WHERE target IS NOT NULL;

-- Append-only on chunks and links. Files allow exactly two updates: setting
-- `superseded_at`/`superseded_by` when a tombstone+replace operation runs.

CREATE OR REPLACE FUNCTION prevent_markdown_files_destructive_mutation() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'markdown_files rows are append-only (RFC 0050 Layer 3)';
    END IF;
    IF NEW.id <> OLD.id
       OR NEW.source_id <> OLD.source_id
       OR NEW.tenant_id <> OLD.tenant_id
       OR NEW.corpus_id <> OLD.corpus_id
       OR NEW.markdown_root_id <> OLD.markdown_root_id
       OR NEW.relative_path <> OLD.relative_path
       OR NEW.content_hash <> OLD.content_hash
       OR NEW.size_bytes <> OLD.size_bytes
       OR NEW.body_text <> OLD.body_text
       OR NEW.adapter_version <> OLD.adapter_version
       OR NEW.imported_at <> OLD.imported_at
       OR NEW.privacy_tier <> OLD.privacy_tier THEN
        RAISE EXCEPTION 'markdown_files identity columns are immutable (RFC 0050 Layer 3)';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS markdown_files_immutable_identity ON markdown_files;
CREATE TRIGGER markdown_files_immutable_identity
    BEFORE UPDATE OR DELETE ON markdown_files
    FOR EACH ROW
    EXECUTE FUNCTION prevent_markdown_files_destructive_mutation();

CREATE OR REPLACE FUNCTION prevent_markdown_chunks_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'markdown_file_chunks rows are append-only (RFC 0050 Layer 3)';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS markdown_file_chunks_no_update ON markdown_file_chunks;
CREATE TRIGGER markdown_file_chunks_no_update
    BEFORE UPDATE ON markdown_file_chunks
    FOR EACH ROW
    EXECUTE FUNCTION prevent_markdown_chunks_mutation();

DROP TRIGGER IF EXISTS markdown_file_chunks_no_delete ON markdown_file_chunks;
CREATE TRIGGER markdown_file_chunks_no_delete
    BEFORE DELETE ON markdown_file_chunks
    FOR EACH ROW
    EXECUTE FUNCTION prevent_markdown_chunks_mutation();

CREATE OR REPLACE FUNCTION prevent_markdown_links_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'markdown_file_links rows are append-only (RFC 0050 Layer 3)';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS markdown_file_links_no_update ON markdown_file_links;
CREATE TRIGGER markdown_file_links_no_update
    BEFORE UPDATE ON markdown_file_links
    FOR EACH ROW
    EXECUTE FUNCTION prevent_markdown_links_mutation();

DROP TRIGGER IF EXISTS markdown_file_links_no_delete ON markdown_file_links;
CREATE TRIGGER markdown_file_links_no_delete
    BEFORE DELETE ON markdown_file_links
    FOR EACH ROW
    EXECUTE FUNCTION prevent_markdown_links_mutation();
