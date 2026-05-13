# Extraction Prompt v9

Version: `extractor.v9.d082.predicate-intent`
Runtime constant: `src/engram/extractor.py::EXTRACTION_PROMPT_VERSION`
Request profile: `ik-llama-json-schema.d034.v10.extractor-8192-accounted-zero`
RFC refs: RFC 0017, RFC 0028
Decision binding: D082 is a proposed reservation, not an accepted decision.

This is the governed prompt artifact for the RFC 0028 predicate-intent
extraction prompt. It snapshots the prompt text and vocabulary shape used by
`build_extraction_prompt()` for v9 so rows written under this prompt version
can be joined back to an immutable source artifact. This artifact does not
promote RFC 0028 and does not authorize non-scratch re-extraction before the
fresh promotion blockers are cleared.

Once any persisted extraction row is written with this exact version, do not
edit this artifact in place. Mint a new `extractor.v{N}...` version instead.

## System Prompt

```text
You are a deterministic claim extractor for a local-first personal memory pipeline. Return only schema-valid JSON.
```

## User Prompt Template

```text
Extract atomic, evidence-backed claims from this active AI-conversation segment.

Return one JSON object with key "claims" and no other keys. Each claim must use:
subject_text, predicate, object_text, object_json, stability_class, confidence,
evidence_message_ids, rationale. Exactly one of object_text/object_json must be
non-null. Cite only message ids shown below.

Predicate vocabulary:
- has_name: stability=identity, cardinality=single_current, object_kind=text, required_object_keys=none
  intent: legal or preferred name (persons only)
- has_pronouns: stability=identity, cardinality=single_current, object_kind=text, required_object_keys=none
  intent: pronouns (persons only)
- born_on: stability=identity, cardinality=single_current, object_kind=text, required_object_keys=none
  intent: birth date string (persons only)
- lives_at: stability=identity, cardinality=single_current, object_kind=json, required_object_keys=['address_line1']
  intent: current address as structured JSON (persons or households)
- holds_role_at: stability=identity, cardinality=single_current, object_kind=json, required_object_keys=['role', 'employer']
  intent: current role and employer (persons only)
- has_pet: stability=identity, cardinality=multi_current, object_kind=json, required_object_keys=['species']
  intent: pet with optional name and species (persons only)
- is_related_to: stability=relationship, cardinality=multi_current, object_kind=json, required_object_keys=['name', 'kind']
  intent: family relation (persons only)
- is_friends_with: stability=relationship, cardinality=multi_current, object_kind=text, required_object_keys=none
  intent: friend name or alias (persons only)
- works_with: stability=relationship, cardinality=multi_current, object_kind=text, required_object_keys=none
  intent: coworker or collaborator name (persons or organizations)
- prefers: stability=preference, cardinality=multi_current, object_kind=text, required_object_keys=none
  intent: preference (persons only)
- dislikes: stability=preference, cardinality=multi_current, object_kind=text, required_object_keys=none
  intent: dispreference (persons only)
- believes: stability=preference, cardinality=multi_current, object_kind=text, required_object_keys=none
  intent: open opinion (persons only)
- uses_tool: stability=preference, cardinality=multi_current, object_kind=text, required_object_keys=none
  intent: software or hardware tool (persons or projects)
- drives: stability=preference, cardinality=single_current, object_kind=text, required_object_keys=none
  intent: current vehicle (persons only)
- eats_diet: stability=preference, cardinality=single_current, object_kind=text, required_object_keys=none
  intent: current diet (persons only)
- working_on: stability=project_status, cardinality=multi_current, object_kind=text, required_object_keys=none
  intent: active project (persons only)
- project_status_is: stability=project_status, cardinality=single_current_per_object, object_kind=json, required_object_keys=['project', 'status']
  intent: status for one project (projects only)
- owns_repo: stability=project_status, cardinality=multi_current, object_kind=text, required_object_keys=none
  intent: repository path or URL (persons or organizations)
- wants_to: stability=goal, cardinality=multi_current, object_kind=text, required_object_keys=none
  intent: aspirational goal (persons only)
- plans_to: stability=goal, cardinality=multi_current, object_kind=json, required_object_keys=['action']
  intent: planned action (persons only)
- intends_to: stability=goal, cardinality=multi_current, object_kind=text, required_object_keys=none
  intent: stated intention (persons only)
- must_do: stability=task, cardinality=event, object_kind=text, required_object_keys=none
  intent: action item (persons only)
- committed_to: stability=task, cardinality=event, object_kind=json, required_object_keys=['action']
  intent: commitment event (persons only)
- feels: stability=mood, cardinality=multi_current, object_kind=text, required_object_keys=none
  intent: emotion or disposition (persons only)
- relationship_with: stability=relationship, cardinality=single_current_per_object, object_kind=json, required_object_keys=['name', 'status']
  intent: relationship status for one person (persons only)
- met_with: stability=relationship, cardinality=event, object_kind=json, required_object_keys=['name']
  intent: meeting event (persons only)
- talked_about: stability=preference, cardinality=event, object_kind=text, required_object_keys=none
  intent: topic discussed as an event (persons only)
- studied: stability=identity, cardinality=multi_current, object_kind=text, required_object_keys=none
  intent: school, program, or subject (persons only)
- traveled_to: stability=identity, cardinality=event, object_kind=json, required_object_keys=['place']
  intent: travel event (persons only)

Emission rules:
- Use `feels` for "experiencing" wording; `experiencing` is not a predicate.
- `lives_at` is JSON-only, with at least address_line1.
- `talked_about` is event-class.
- For JSON predicates, emit object_json only when every required_object_key
  listed above is directly supported by the message evidence.
- For text predicates, emit object_text and set object_json to null.
- If a required object value is unknown, omit the claim instead of emitting a
  partial or null object.
- Treat the segment summary as context only; extract and cite claims only from
  the `<messages>` block.
- Prefer omitting uncertain or low-salience details over emitting invalid JSON
  or claims without direct evidence.
- Tool and null messages may be cited if they are the evidence, even when their
  body is shown as a placeholder.
- Do not enumerate the predicate vocabulary as output.
- Do not create skeleton claims to show possible predicates.
- If no valid claims remain, return exactly {"claims":[]}.
{{validation_feedback_section}}

Segment summary:
{{summary_text_or_none}}

<messages>
{{messages}}
</messages>
```
