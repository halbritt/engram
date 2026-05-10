# RFC 0028 Findings Ledger

Read the three review artifacts and normalize them into one ledger. Merge
duplicates, keep original reviewer references, and preserve severity unless a
merge requires a clear adjustment.

Write
`docs/reviews/rfc0028-predicate-intent-implementation/FINDINGS_LEDGER.md`
with the exact lowercase `author:` line from the work packet.

Required sections:

- Summary
- Findings table with ID, severity, title, affected files, source reviews
- Finding detail sections with rationale and recommended action
- Items intentionally not carried forward, with reasons

Do not modify implementation files or review artifacts.
