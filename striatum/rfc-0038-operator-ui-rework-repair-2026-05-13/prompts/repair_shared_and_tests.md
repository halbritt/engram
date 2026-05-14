You are an RFC 0038 repair implementer. You are not alone in this repo: other
workers may be editing interview and bench surfaces concurrently. Do not
revert or rewrite their changes. Use the maximum number of useful sub-agents
for implementation analysis within this lane.

Own only the shared/test dependency scope in the work packet. Address the
reviewed findings that belong to this scope:

- add the missing bounded `httpx` dependency to the dev/test dependency set;
- keep shared `src/engram/web/` assets package-local and no-CDN;
- update `tests/test_web_ui_shared.py` as needed for shared shell/future-slot
  assertions;
- run focused ruff check/format on files you touch.

Do not edit interview or bench implementation files. Publish the required
handoff artifact with commands run, files changed, and any residual risks.
