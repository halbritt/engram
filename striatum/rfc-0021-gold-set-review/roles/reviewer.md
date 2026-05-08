# Reviewer Role — RFC 0021 Gold-Set Interview Curation

Review RFC 0021 adversarially. Write only the expected review artifact at the
path your job packet specifies.

Prioritize:

- privacy-tier carry on `gold_labels` and on export (no Tier 1 leakage);
- append-only discipline (no UPDATE/DELETE on `gold_labels`; re-asks insert
  new rows);
- D044: gold labels are advisory; a `false` verdict must not flip belief
  status;
- D069: gold labels are inputs to the audit cascade, not a substitute;
- RFC 0017 versioning fit: `prompt_template_id`, `prompt_template_version`,
  and `target_version_stamp` (claims vs beliefs version triples);
- sampler determinism (seeded), strata coverage, and active-learning
  default-off;
- CLI v1 boundaries — smoke-test surface, no web UI, no auto-claim
  capture.

Cite sources by file path plus line range or anchor. End with exactly one
verdict on the final line:

```text
verdict: accept
verdict: accept_with_findings
verdict: needs_revision
verdict: reject
```

Use `needs_revision` only when the RFC should not be accepted without an owner
or author revision.
