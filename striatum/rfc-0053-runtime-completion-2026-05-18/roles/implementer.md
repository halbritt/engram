# Implementer Role

Implement one bounded RFC 0053 runtime-completion slice. Preserve Engram's
local-first rule: no user data leaves the machine unless explicitly requested.

Stay inside the declared write scope. Do not add live network behavior to claim
extraction. Network-capable code must be disabled by default, explicit, bounded,
audited, and covered by deterministic tests with monkeypatched I/O.

When done, write the expected artifact declared in the workflow with changed
files, verification commands, residual risks, and the exact boundary that stays
disabled.
