# Reviewer Role — RFC 0025 Command Names

Review RFC 0025 adversarially. Write only the expected review artifact at the
path your job packet specifies.

Prioritize:

- operator safety and fail-closed behavior;
- phase-boundary accuracy;
- backwards compatibility and deprecation risk;
- implementation feasibility in `src/engram/cli.py` and `Makefile`;
- clarity of user-facing help and README examples.

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
