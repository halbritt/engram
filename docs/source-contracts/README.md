# Source Contracts

Every Engram source adapter must declare a source contract before importer
code is written. The contract is a reviewer artifact, not a runtime
registry — at Layer 1 the contracts live here as checked-in YAML and a
pytest module exercises every contract.

The contract template below mirrors RFC 0050 § Source Contract verbatim.
The validator at `src/engram/source_contract.py` consumes contracts and
emits errors with a closed vocabulary.

## Required Questions

Every adapter must answer all four:

1. **Raw boundary** — Which export file, local database copy, repository
   object, directory snapshot, media asset, or capture record is the
   immutable evidence boundary?
2. **Projection** — Which closed projection families are emitted, and
   which fields remain raw-only?
3. **Default consumers** — Which systems may see the derived projection
   by default: retrieval, packet builder, segmentation, extraction,
   daily biography, or none?
4. **Protection rules** — Which provenance, confidence, sensitivity,
   privacy, lifecycle, redaction, rebuild, and no-egress rules apply?

An adapter that cannot answer all four does not pass review.

## Closed Vocabularies

### Projection Families

`conversation_thread`, `document_record`, `project_event`,
`execution_artifact`, `code_reference`, `artifact_reference`,
`observation`, `place_event`, `asset_record`.

### Operational Families

`coverage_gap`, `source_audit`.

### Source Families

`project_execution`, `documents`, `conversation`, `observation`, `asset`.

### Sensitivity Classes

`routine_project`, `personal_private`, `third_party_communication`,
`calendar_contact`, `behavioral_activity`, `raw_media`, `exact_location`,
`health`, `biometric`, `finance`, `credential_or_secret_reference`.

### Network Policies

`no outbound calls` is the only accepted value for corpus-reading paths.

### Conflict Policies

`raise_on_changed_raw_artifact_hash`, `raise_on_changed_manifest`,
`tombstone_and_replace`.

### Extraction Defaults

`metadata_only`, `disabled`, `opt_in`.

## Mandatory YAML Field Set

```yaml
source_kind: <required>
source_family: <required>  # one of source_families
sub_kinds: <required, non-empty list of strings>

raw_artifact_boundary:
  description: <required>
  acquisition: <required, non-empty list>
  network_policy: no outbound calls  # closed vocabulary

identity:
  source_instance_id: <required>
  item_identity_keys: <required, list>
  logical_identity_keys: <optional, list>

temporal_fields:
  observed_at: <required>
  recorded_at: <required>

deduplication:
  idempotency_key: <required, list>
  conflict_policy: <required, one of conflict_policies>

privacy:
  privacy_tier_default: <required, integer 1..5>
  sensitivity_class_default: <required, one of sensitivity_classes>

projection_families: <required, list of projection_families>
operational_families: <required, list of operational_families>

extraction_eligibility:
  default: <required, one of extraction_defaults>
  participant_third_party: <required, boolean>
  opt_in_required_for: <optional, list>

raw_retention:
  required: <required, non-empty list of strings>
  optional: <optional, list>

provenance:
  required: <required, non-empty list of strings>

rebuild:
  projection_generation: required
  reproject_from_raw: required
  stale_projection_policy: <required>

tests: <required, list of known test names>
```

## Validator Error Vocabulary

The validator at `src/engram/source_contract.py` returns errors with one
of the closed codes:

| Code | Meaning |
|------|---------|
| `CONTRACT_FILE_NOT_FOUND` | Contract path does not exist or is not a file. |
| `CONTRACT_NOT_YAML` | File could not be parsed as YAML. |
| `CONTRACT_NOT_OBJECT` | YAML root is not a mapping. |
| `MISSING_FIELD` | A mandatory field is absent. |
| `EMPTY_FIELD` | A mandatory field is present but empty. |
| `UNKNOWN_SOURCE_FAMILY` | Value is not in the closed source-family vocabulary. |
| `UNKNOWN_PROJECTION_FAMILY` | Value is not in the closed projection vocabulary. |
| `UNKNOWN_OPERATIONAL_FAMILY` | Value is not in the closed operational vocabulary. |
| `UNKNOWN_SENSITIVITY_CLASS` | Value is not in the closed sensitivity-class vocabulary. |
| `UNKNOWN_NETWORK_POLICY` | Value is not `no outbound calls`. |
| `UNKNOWN_CONFLICT_POLICY` | Value is not in the closed conflict-policy set. |
| `UNKNOWN_TEST_NAME` | Test name is not in the project's known test list. |
| `INVALID_PRIVACY_TIER` | Value is not an integer in 1..5. |
| `INVALID_EXTRACTION_DEFAULT` | Value is not in the closed extraction-default vocabulary. |
| `INVALID_PARTICIPANT_THIRD_PARTY` | Value is not a boolean. |
| `INVALID_RAW_RETENTION` | Required retention list is empty or contains non-string values. |
| `INVALID_PROVENANCE` | Required provenance list is empty or contains non-string values. |

The validator may also emit warnings for soft signals (e.g.
`participant_third_party: true` while extraction default is not
`disabled`). Warnings do not fail validation.

## Validation

`tests/test_source_contract_validator.py` exercises this template and
every contract under this directory. Adding a new source contract is a
two-step PR: drop the YAML in this directory, then add a positive case
to the test module.

## Known Contracts

- [`git.yaml`](git.yaml) — RFC 0050 Layer 1 git metadata + diff-stat
  importer.
- [`build_artifact.yaml`](build_artifact.yaml) — RFC 0050 Layer 2 forward
  pointer for the build/test/lint/coverage/benchmark artifact importer.
