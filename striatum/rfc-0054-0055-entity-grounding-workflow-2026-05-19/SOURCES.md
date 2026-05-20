# Sources

Canonical context:

- `AGENTS.md`
- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `BUILD_PHASES.md`
- `ROADMAP.md`
- `SPEC.md`
- `docs/AGENT_CONTEXT_NOTES.md`
- `docs/rfcs/0012-python-agentic-coding-standard.md`
- `docs/rfcs/0052-entity-identity-review-and-grounding.md`
- `docs/rfcs/0053-claim-extraction-grounding-boundary.md`
- `docs/rfcs/0054-entity-grounding-batch-workflow.md`
- `docs/rfcs/0055-grounding-evidence-materialization.md`

Implementation surfaces:

- `migrations/009_phase4_entities_review.sql`
- `migrations/014_striatum_tenant_corpus.sql`
- `migrations/023_entity_grounding_review.sql`
- `migrations/024_claim_grounding_runtime.sql`
- `src/engram/entity_grounding.py`
- `src/engram/claim_grounding.py`
- `src/engram/claim_grounding_runtime.py`
- `src/engram/claim_grounding_network.py`
- `src/engram/cli.py`
- `tests/conftest.py`
- `tests/test_claim_grounding_runtime.py`
- `tests/test_claim_grounding_network.py`
- `tests/test_phase4_entities_review.py`
- `tests/test_cli.py`

