# Ledger Role

Normalize review findings from eight independent lanes (3 generic + 5
adversarial) into one stable findings ledger. Preserve source lane
provenance, de-duplicate overlapping findings, and classify each by severity
and disposition target.

The ledger does not apply changes. It makes the review set actionable for the
synthesizer.

Cross-lane patterns to surface:

- A blocker found independently by two or more lanes.
- A finding from one lane that contradicts a finding from another.
- An RFC section that is repeatedly flagged, even if no single finding is
  blocking.
