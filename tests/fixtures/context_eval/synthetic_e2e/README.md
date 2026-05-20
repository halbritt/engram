# Synthetic Context Eval E2E Fixture

This fixture is the public, non-private starter harness for context-serving
evaluation. It exists because real LLM chat history is ambiguous and hard to use
as the first gold set.

- `corpus.json` defines the synthetic evidence to seed into the test database.
- `context_eval.gold.jsonl` defines the expected context-eval items for that
  corpus.

The fixture is exercised by `make e2e-context-synthetic`. It does not replace a
future owner-authored private eval set; it gives the compiler/eval loop a stable
end-to-end contract first.
