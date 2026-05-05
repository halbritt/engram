# Migrations

Migrations are applied by lexicographically sorted filename. The exact filename
and a SHA-256 checksum of the SQL file are recorded in `schema_migrations`.

If an applied migration file changes on disk after its checksum has been
recorded, the migration runner raises an error instead of silently no-oping.
Write a new forward migration for any post-apply change.

The numeric prefix is a human ordering convention, not the migration identity
after a file has been applied. Do not rename an applied migration to clean up
numbering unless the runner also gains an explicit compatibility alias for the
old filename; otherwise existing databases will see the renamed file as a new
unapplied migration.

There are two historical `004_` migrations:

- `004_segments_embeddings.sql`
- `004_source_kind_gemini.sql`

Their order is deterministic because filenames are sorted in full. Leave those
filenames stable. Future migrations should use the next unambiguous prefix and
name, for example `005_...`, unless a compatibility migration deliberately
handles a historical filename.
