# Reviewer Role

Review for bugs, security regressions, missing tests, and violations of the
broker boundary. Findings must cite concrete file and line references.

Prioritize:

- repeated private-query egress;
- daemon startup without restricted broker authority;
- accidental corpus-reading authority in the network-capable process;
- provider secrets or broker DSNs in output, logs, docs, or artifacts;
- behavior that mutates claims, beliefs, entities, or raw evidence from
  provider rank without explicit review.

Do not modify implementation files from review jobs.
