# Retry Cooldown Policy

Draft the retry/cooldown policy before runtime retry behavior changes.

Required outcome:

- Create `docs/rfcs/0056-grounding-broker-retry-cooldown-policy.md`.
- Define retry states, attempt caps, cooldown windows, expiry behavior,
  operator override, and how private entity search strings are protected from
  tight retry loops.
- State whether retries consume the same approved grant, require a new grant, or
  require a new explicit retry grant.
- Define audit rows/events needed for retry state and how they interact with
  the durable dispatch boundary.
- Keep provider snippets/data as untrusted input; no claim/entity mutation from
  retry status alone.
- Update `docs/rfcs/README.md` if this repo's RFC index requires it.

Do not implement runtime retry behavior in this lane.

Publish
`docs/reviews/entity-grounding-broker-daemon-followups-2026-05-19/RETRY_COOLDOWN_POLICY_HANDOFF.md`.
