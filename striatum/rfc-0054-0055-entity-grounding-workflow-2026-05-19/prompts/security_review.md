# Adversarial Security Review

Review the RFC 0054/0055 implementation for privacy and security failures.

Focus areas:

1. Draft workflow opens no sockets and never calls configured adapters.
2. Only exact approved entity search queries can cross the broker boundary.
3. Private query text is visible for operator approval but never sent without a
   latest approved persisted grant.
4. Provider secrets do not appear in URLs, request bodies, DB JSON, exceptions,
   CLI output, logs, or handoff artifacts.
5. Provider snippets are treated as adversarial data and are persisted locally
   before response candidates cite them.
6. No automatic merge, alias, split, external-id, claim, belief, or entity
   mutation occurs from provider rank.
7. The network-capable processor does not read raw messages, segments, captures,
   notes, beliefs, or claim text.

Use maximum safe parallelism for inspection. Do not edit implementation files.

Write `docs/reviews/rfc0054-0055-entity-grounding-workflow/ADVERSARIAL_SECURITY_REVIEW.md`.

