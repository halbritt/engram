You are the RFC 0038 accept-with-findings shared cleanup implementer. Stay
inside your write scope and do not edit interview or bench surface files.

Use the corrected ergonomics review as the source of truth. Address
shared-owned cleanup, especially FU105: `chrome.DEFAULT_SURFACE_TABS` is dead
or drift-prone at render time. Either make the shared templates consume a
single source of truth in a way that does not require surface-file edits, or
remove/adjust the unused constant and tests so the shared contract is explicit.

Preserve no-CDN/local-only behavior. Use maximal useful internal sub-agents if
available, with disjoint ownership inside this lane. Publish the required
handoff with changed files, commands, finding disposition, and remaining risk.
