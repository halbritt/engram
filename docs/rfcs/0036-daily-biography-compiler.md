<a id="rfc-0036"></a>
# RFC 0036: Daily Biography Compiler

Status: proposal
Date: 2026-05-07
Context: RFC 0033, RFC 0034, RFC 0035; `HUMAN_REQUIREMENTS.md` sections
time-indexed biography, daily log, locations, photos and media, outputs the
system should produce, gaps as data; DECISION_LOG D001, D002, D003, D018,
D019, D020, D021, D022, D025, D051

This is an idea-capture RFC, not an accepted architecture decision. It
proposes a post-V1 daily biography compiler: a rebuildable projection that
answers questions like "On this arbitrary day in 2023, what were you up to?"
by combining location, photos, calendar, messages, captures, and beliefs into
an evidence-backed day packet with explicit gaps.

The daily compiler is not a replacement for `context_for(conversation)`.
`context_for` answers "what should the next assistant know for this task?"
The daily compiler answers "what was this day in the biography of one human
life?"

## Background

The human requirements define Engram's distinguishing property as a complete
time-indexed biography:

> "What was my life like on March 15, 2003?"

The current V1 pipeline creates the first spine for that ambition, but its
serving path is conversation-centric. A daily biography query has a different
shape. It is time-first, not topic-first. It needs to gather weak signals from
many source families:

- location samples and visits,
- photo events and face/person observations,
- calendar events,
- messages and AI conversations,
- manual captures and journal entries,
- beliefs with biographical validity on that day,
- travel/reservation/receipt evidence later,
- explicit coverage gaps.

No single lane has to prove the whole day. The daily compiler's job is to
assemble a defensible packet and say what is known, what is inferred, and what
is missing.

## Problem

Without a daily compiler, Engram has two bad options:

1. Force day queries through ordinary semantic retrieval, which will miss
   low-text days, over-retrieve irrelevant memories, and hide gaps.
2. Ask an LLM to narrate across raw evidence directly, which risks false
   precision and breaks the project's provenance discipline.

The daily question is not simply a claim/belief lookup. A good answer may be:

```text
On 2023-06-14, you appear to have been in San Francisco. Location coverage is
moderate. Photos place you near the Mission around dinner time with two
recognized face clusters, one labeled Alice. Calendar evidence for the evening
is weak. There is no evidence after 22:10.
```

That answer is a projection over observations and beliefs. It should be
rebuildable and auditable, not a free-floating memory.

## Proposal

Introduce a **daily biography compiler** that produces a day packet:

```text
date + timezone
  -> evidence collection
  -> source coverage map
  -> candidate episodes
  -> day summary
  -> gaps and confidence
  -> provenance-bearing render
```

### Day packet

A day packet is the canonical derived unit for a local calendar day. It should
carry:

- date,
- timezone and timezone-confidence,
- coverage by source family,
- candidate episodes,
- people/entity candidates,
- place/visit candidates,
- relevant beliefs active or historically valid on that day,
- explicit gaps,
- summary text,
- confidence,
- privacy tier,
- derivation versions,
- provenance references.

The day packet is not raw evidence and not a belief. It is a projection. It can
be regenerated when photo, location, calendar, entity, or belief derivations
change.

### Evidence collection

For a requested day, the compiler gathers:

- location visits overlapping the local day,
- location samples if no visit interval exists,
- photo events and individual significant photos,
- face/person observations and confirmed labels,
- calendar events overlapping the day,
- messages and conversations created that day,
- manual captures observed that day,
- beliefs whose biographical validity overlaps the day,
- correction captures about that day,
- source-family coverage gaps.

Collection should be deterministic. If a local LLM is used later, it should
operate only after candidate evidence has been bounded and tagged.
Discovery-time-only V1 beliefs are not enough for this step; the daily
compiler should use biographical validity once that lift exists.

### Candidate episodes

An episode is a time-bounded cluster inside a day:

```text
morning commute
dinner with Alice
flight from SFO
work session on Engram
evening at home
unknown interval
```

Episodes are derived from overlapping evidence:

- visit intervals,
- photo clusters,
- calendar intervals,
- message bursts,
- manual captures,
- repeated source agreement.

Episodes carry confidence and evidence ids. They can be rendered directly, but
they should not become beliefs unless a separate claim/belief process promotes
some durable semantic fact.

### Coverage and gaps

The compiler should always include coverage, even when the narrative is sparse.

Coverage axes:

- location,
- photos/media,
- calendar,
- messages/conversations,
- manual capture/journal,
- health/activity later,
- finance/receipts later.

Coverage values:

- `high`,
- `partial`,
- `weak`,
- `absent`,
- `unknown`,
- `intentionally_unavailable`.

This makes "I do not know" structurally available. A no-data day can still be
represented:

```text
2023-02-09:
  summary: no reliable evidence
  coverage: location absent, photos absent, calendar absent, captures absent
```

### Summary generation

The first version should separate structured day facts from prose:

1. Deterministic compiler builds the evidence packet, coverage map, candidate
   episodes, confidence scores, and provenance references.
2. Optional local LLM renderer turns that packet into prose under a versioned
   prompt.
3. The prose is cached as a derived artifact, not treated as canonical truth.

If the renderer changes, day summaries can be regenerated without touching raw
evidence or structured episodes.

### Privacy and rendering

Daily packets inherit the maximum privacy tier of included evidence, with an
option to render lower-tier views:

- private full packet,
- AI-assistant context packet,
- partner/shareable packet later,
- posthumous packet later.

Exact coordinates, face clusters, OCR text, health data, and financial data
should not leak through a day summary merely because they helped compile it.
The renderer should support redaction and granularity policies:

- "San Francisco" instead of exact coordinates,
- "a recognized friend" instead of a face cluster name where unconfirmed,
- "private appointment" instead of sensitive calendar title,
- explicit "redacted at this tier" markers where omission would mislead.

This is the daily-biography version of D022's confidence/provenance contract.

### Relationship to `context_for`

The daily compiler can eventually feed `context_for` as a lane, but it has a
different primary interface:

```text
biography_for_day(date, timezone?)
biography_for_range(start_date, end_date, granularity="day")
this_day_in_my_life(date, years_back?)
```

`context_for` may use day packets when the current conversation asks about a
date, trip, person, or period. But day packets should also be useful as a
standalone product surface because the human requirements explicitly demand
biography outputs, not only AI-assistant context.

### Corrections

If the user says "that was not dinner with Alice; that was drinks with Ben,"
the correction is a raw capture, consistent with D017. The daily packet is then
invalidated and rebuilt. The compiler does not edit the old summary in place
as if it were raw truth.

## Non-goals

- Shipping this in V1.
- Replacing `context_for(conversation)` as the primary V1 product surface.
- Creating a private journal entry automatically for every day.
- Inferring emotions, relationship strength, or life significance by default.
- Treating generated narrative as canonical evidence.
- Hiding gaps to make the day sound more complete.

## Open questions

1. Should daily packets be materialized for every day in the corpus, or
   generated on demand and cached?
2. What is the first day-boundary rule for travel days: user's home timezone,
   local timezone at each sample, or query-specified timezone?
3. Should the compiler use a dedicated `daily_summaries` table, or a more
   general `biographical_projections` table that can also represent weeks,
   months, years, trips, and eras?
4. What source-family weights produce honest confidence without making dense
   GPS data overpower explicit journal entries?
5. How should day packets cite high-volume raw evidence without exploding
   token budgets?
6. When should a day-level episode emit a claim candidate, and when should it
   stay only in the daily projection?

## Acceptance criteria for promotion

This RFC is ready to promote when:

- at least two non-text source families exist or have accepted implementation
  specs, likely photos and location,
- source coverage and gap semantics are accepted,
- a day-packet schema or projection spec is accepted,
- privacy-tier rendering rules exist for exact coordinates and face/person
  observations,
- a bounded sample can answer at least ten real "what was I doing that day?"
  prompts with provenance, confidence, and explicit gaps.

Until then this RFC defines the target shape for the biographical output layer
that photos and location are meant to enable.
