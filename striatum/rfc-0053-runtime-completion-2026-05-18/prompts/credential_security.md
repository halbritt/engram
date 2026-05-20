# Credential Security Slice

Scaffold broker credential-separation checks for RFC 0053.

Required:

1. Add deterministic tests proving the broker/network-adapter role should not
   read private corpus tables such as `messages`, `segments`, and
   `conversations`.
2. If the test database user can manage roles, create temporary role tests;
   otherwise skip with an explicit reason.
3. Prove allowed writes are limited to sidecar audit rows and local grounding
   evidence rows required by RFC 0053.
4. Do not change production credentials or require a privileged local database
   user for the normal test suite.

Write `docs/reviews/rfc0053-runtime-completion/CREDENTIAL_SECURITY_HANDOFF.md`.
