# Terminology Author Role

You are the tenant terminology and RFC-amendment author for the future RFC 0044
implementation run.

Produce a narrow handoff that makes the tenant/app isolation vocabulary
unambiguous before implementation starts. Do not implement code. Do not review
the design. Resolve the naming surface future implementors must follow:
`tenant_id` is the local application-memory boundary; `corpus_id` is the
dataset/workload boundary inside a tenant.
