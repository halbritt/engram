# Network Adapter Slice

Scaffold a constrained RFC 0053 network adapter boundary.

Required:

1. Add a disabled-by-default adapter module.
2. If configured by an explicit local environment variable, allow only a bounded
   local search endpoint shape. Do not use network when unset.
3. Enforce fixed method, fixed query parameter, timeout, byte/result limits,
   allowed target adapter, and private-address denial except explicitly allowed
   local development endpoints.
4. Tests must monkeypatch all network calls. No live network.
5. The adapter must return structured candidate/raw-result data that can be
   written to local evidence later, not prose claims.

Write `docs/reviews/rfc0053-runtime-completion/NETWORK_ADAPTER_HANDOFF.md`.
