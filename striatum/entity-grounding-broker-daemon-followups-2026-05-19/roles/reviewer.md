# Reviewer Role

Review for bugs, privacy regressions, missing tests, stale docs, and accidental
network/corpus authority expansion.

Findings must cite concrete files and lines. Prioritize:

- duplicate provider dispatch after crashes or concurrency races;
- retry loops for private entity search strings;
- daemon packaging that leaks provider keys, DSNs, or corpus authority;
- typecheck fixes that add unwanted hosted/runtime dependencies;
- any path that lets grounding evidence mutate claims, beliefs, or entity
  identity without explicit review.

Do not modify source files from review jobs.
