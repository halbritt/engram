You are an RFC 0038 repair implementer for the bench-review surface. You are
not alone in this repo: shared/test and interview workers may be active
concurrently. Do not revert or overwrite their edits. Use the maximum number of
useful sub-agents for implementation analysis within this lane.

Own only the bench-review surface. Address the reviewed blockers:

- fix FastAPI route return annotations so `create_app(...)` starts;
- enforce loopback Origin/Sec-Fetch behavior for mutating POST routes;
- wire bench UI into the shared chrome/help/keyboard/copy/future-slot contract;
- make the copy command button functional;
- render the scratch-local / no-production-mutation disclaimer on segment
  decision pages;
- update focused bench route tests and run them if dependencies are present.

Do not edit interview files. Publish the required handoff artifact with commands
run, files changed, and residual risks.
