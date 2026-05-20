# Idempotency And Security

Harden the existing RFC 0055 materializer for daemon use.

Required behavior:

- prevent repeated provider dispatch for approved grants that already have a
  prepared, dispatched, succeeded, or failed dispatch audit row for the target
  adapter;
- add a deterministic test proving a second materializer pass does not invoke
  the adapter again;
- keep retry semantics explicit: retrying a provider call requires a new
  approved grant unless a later RFC adds bounded retry/cooldown state;
- preserve existing byte-exact query validation, materializer URL filtering,
  and review-action privacy tiers.

Publish `docs/reviews/entity-grounding-broker-daemon-2026-05-19/IDEMPOTENCY_SECURITY_HANDOFF.md`.
