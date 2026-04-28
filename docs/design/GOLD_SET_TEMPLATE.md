# Gold Set Template

> The gold set is the actual specification. Principles describe *what* engram
> should do; the gold set describes *what good looks like when it does*.
> Author the gold set before casting migrations — it will surface
> architectural gaps a principle review can't.

Target: 25–50 entries spanning the categories below for the v1 eval gate. The
set grows over time — every `context_feedback` annotation in production is a
candidate new entry.

## Entry shape

```yaml
id: gold-007
category: past-decision-recall
trigger: |
  I'm considering switching engram to a graph database. Help me think
  through it.
expected_facts:
  - "User considered Apache AGE / Neo4j / FalkorDB / Kuzu in 2026-04 and
    chose Postgres + relational entity_edges; AGE is the eventual escape
    valve if SQL becomes ugly."
  - "Reasoning was operational overhead vs marginal gain at single-user scale."
expected_evidence:
  - "At least one citation back to CONSENSUS_REVIEW.md or the conversation
    that produced it."
forbidden_facts: []
forbidden_evidence: []
historical_window: null   # null = current state; or "2025-01-01..2025-06-30"
notes: |
  Tests that decisions in the design corpus surface when topically relevant.
```

Field semantics:

- **`id`** — stable identifier; never reused after retirement.
- **`category`** — one of the categories below.
- **`trigger`** — the conversational input or query that should activate
  retrieval. Write it as a real user would phrase it, not as a clean query
  string.
- **`expected_facts`** — beliefs (in plain language) that *must* appear in the
  produced context. Match by semantic content, not exact wording — the eval
  must tolerate paraphrase.
- **`expected_evidence`** — at least one raw-store citation grounding each
  expected fact. A fact appearing without evidence is a different kind of
  failure than the fact being absent.
- **`forbidden_facts`** — things that *must not* appear. Critical for
  stale-fact-suppression and ambiguous-reference categories.
- **`forbidden_evidence`** — raw rows that should not surface (often the same
  row that's right for a historical query but wrong for a current one).
- **`historical_window`** — `null` for "what's true now"; an interval for
  "what was true between these dates." Tests that bitemporal retrieval honors
  validity windows.
- **`notes`** — author intent. Six months from now, "why did I write this
  entry?" is a real question.

## Categories

Eight from CONSENSUS_REVIEW + two recommended additions.

### 1. Current project continuation
*"Let's keep working on X."* The context should produce: what X is, the last
known state, the current blocker, who else is involved. Tests that active
project context is reachable without explicit enumeration.

### 2. Past decision recall
*"Why did I decide to use Y?"* The context should produce the original
decision, the alternatives considered, the rationale. Tests that one-time
significant decisions don't get buried by recency-weighted retrieval.

### 3. Person / entity recall
*"What's going on with [person]?"* The context should produce: relationship
context, last interaction, anything outstanding. Tests entity-neighborhood
expansion.

### 4. Style preference recall
*"Help me write X."* The context should produce the user's stated preferences,
things they like and dislike, without being asked about explicitly. Tests
identity-class belief retrieval for stylistic tasks.

### 5. Active goal support
*"I'm thinking about what to work on."* The context should produce active
goals, current projects, recent commitments. Tests goal-class belief
retrieval.

### 6. Failed-approach avoidance
*"Should I try Z?"* The context should produce prior attempts at similar
things and what failed. Tests `failures` recall — engram should help the user
not relearn the same lesson.

### 7. Historical self-state
*"What was I working on in summer 2024?"* The context should produce
time-bound recall. Tests that bitemporal queries actually work — not just
that beliefs have validity intervals, but that retrieval honors them.

### 8. Stale-fact suppression
*"What's my address?"* — when there are multiple addresses in history, only
the current one should surface. Old addresses should be retrievable but must
not pollute current-state queries. Critical for the "biography at any point
in time" promise.

### 9. Ambiguous reference resolution *(recommended addition)*
*"What did Sarah say about that thing?"* — when the user has multiple Sarahs
and multiple "things." The context should disambiguate or flag the ambiguity
rather than picking confidently. Tests refusal-of-false-precision.

### 10. Gap acknowledgment *(recommended addition)*
A trigger about a topic engram has no data on. The context should explicitly
acknowledge "no data on this" rather than producing inference dressed as
recall. Tests that absence is represented.

## Authoring guidance

- **Be specific enough to grade pass/fail; lenient enough to tolerate
  paraphrase.** Match semantic content, not strings.
- **Cover both easy and hard cases per category.** "What's my email" is an
  easy current-state query; "what was my email in 2017" is the same category,
  hard mode.
- **Write triggers as real phrasings.** "Help me think through the engram
  schema" beats "retrieve schema-related beliefs."
- **For every category, include at least one entry where the right answer is
  silence or refusal.** Engram's value is partly in what it *doesn't* surface.
- **Don't author against the existing schema.** Author against your real life.
  If a gold-set entry has no answer V1 could possibly produce, that's a
  finding — V1 may need to grow.
- **Keep author intent in `notes`.** It will not be obvious later.

## Maintenance

- Every `context_feedback` annotation in production is a candidate new entry.
  Triage the feedback table monthly.
- Retire entries that no longer test what they were authored to test. Mark
  them `retired: true` rather than deleting — historical pass-rates are
  useful.
- Re-run the full gold set after every prompt-version or model-version
  change. Diffs in pass-rate are the regression signal.
