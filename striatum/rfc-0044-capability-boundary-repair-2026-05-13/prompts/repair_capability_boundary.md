You are the RFC 0044 capability-boundary repair implementer. You are not alone
in this repository; do not revert unrelated operator or reviewer changes. Use
the maximum number of useful sub-agents for implementation analysis within
this lane.

Repair only the serving-path authorization gap identified in
`REVIEW_correctness_codex.md`:

- `MemoryService.search()` and `fetch_reference()` must not allow a token with
  multiple allowed pairs to read a second same-tenant corpus without
  `memory.read_cross_corpus`.
- They must not allow a second tenant without `memory.read_cross_tenant`.
- Add regression tests through the service path and, if practical, the MCP
  handler path using the same shape of token the CLI constructs.

Keep Engram local-first. Do not add cloud/network dependencies. Update
`CHANGELOG.md` for the repair. Publish the required handoff with commands run,
files changed, and residual risk.
