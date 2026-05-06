# Documentation Map

Start with the root canonical docs when orienting on the current system:

1. [README.md](../README.md)
2. [HUMAN_REQUIREMENTS.md](../HUMAN_REQUIREMENTS.md)
3. [DECISION_LOG.md](../DECISION_LOG.md)
4. [BUILD_PHASES.md](../BUILD_PHASES.md)
5. [ROADMAP.md](../ROADMAP.md)
6. [SPEC.md](../SPEC.md)
7. [UBIQUITOUS_LANGUAGE.md](UBIQUITOUS_LANGUAGE.md)

## Current Design

- [design/V1_ARCHITECTURE_DRAFT.md](design/V1_ARCHITECTURE_DRAFT.md) — working V1 architecture.
- [schema/README.md](schema/README.md) — generated schema reference.
- [segmentation.md](segmentation.md) — Phase 2 segmentation operations and behavior.
- [claims_beliefs.md](claims_beliefs.md) — Phase 3 claim extraction and bitemporal belief consolidation contract.
- [ingestion.md](ingestion.md) — ingestion behavior and source notes.

## Process

- [process/multi-agent-review-loop.md](process/multi-agent-review-loop.md) —
  where multi-agent feedback goes, how synthesis is applied, and when to use a
  fresh execution context.
- [process/project-judgment.md](process/project-judgment.md) — coordinator
  guidance for scope control, model use, and attention management.
- [process/phase-3-agent-runbook.md](process/phase-3-agent-runbook.md) —
  tmux / marker-file coordination for the Phase 3 spec-to-pipeline chain.
- [../agent-runner/README.md](../agent-runner/README.md) — incubating
  `agent_runner` project, split out after its MVP is designed and built.

## Proposals

- [rfcs/README.md](rfcs/README.md) — proposal index. RFCs are not binding until
  promoted into the decision log, build phases, or a phase prompt.

## Reviews And History

- [reviews/](reviews/) — adversarial reviews, syntheses, and review findings.
- [reviews/phase3/](reviews/phase3/) — Phase 3 spec, build prompt,
  implementation, and pipeline-start reviews.
- [phases/](phases/) — phase-specific build status and review notes.
- [design/BRAINSTORM.md](design/BRAINSTORM.md) — older brainstorm context.
- [design/PRIOR_ART.md](design/PRIOR_ART.md) — prior-art background; context,
  not current architecture unless promoted elsewhere.
