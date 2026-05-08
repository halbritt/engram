# Tier 1 Non-Human Quality And UX Gate

Collect the non-human subset of RFC 0024 Tier 1 evidence. Do not ask for human
input. Treat human-labeled entity precision/recall and review-queue UX
feedback as deferred to RFC 0021.

Use `docs/operations/phase4-build/tiered-gate/TIER0_SMOKE_REPORT.md` as input.

Evaluate and report:

- deterministic entity build idempotency evidence;
- current-beliefs filtering for candidate, provisional, accepted, rejected,
  superseded, and closed beliefs;
- review action audit behavior for accept, reject, correct, and
  promote-to-pinned;
- correction-as-capture behavior and reprocessing queue implications;
- synthetic or test-backed recursive CTE neighborhood query evidence;
- explicit gaps that require RFC 0021 interview/human labels.

Run focused local commands when safe, such as:

```sh
.venv/bin/python -m pytest tests/test_phase4_entities_review.py
make -n phase4-build-entities LIMIT=200
make -n phase4-smoke LIMIT=200
```

Write `docs/operations/phase4-build/tiered-gate/TIER1_NONHUMAN_REPORT.md`.
Do not claim Tier 1 passes for full-corpus promotion while human labels are
missing. Use `deferred_until_rfc0021` for missing human-label evidence.
