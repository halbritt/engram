# Migrations

Migrations are applied by lexicographically sorted filename, and the exact
filename is recorded in `schema_migrations`.

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
