<a id="rfc-0035"></a>
# RFC 0035: Location Timeline And Place Model

Status: proposal
Date: 2026-05-07
Context: RFC 0033, RFC 0034; `HUMAN_REQUIREMENTS.md` sections time-indexed
biography, locations, travel, daily log, gaps as data; DECISION_LOG D002,
D003, D004, D018, D019, D020, D021, D022, D051

This is an idea-capture RFC, not an accepted architecture decision. It
proposes a post-V1 location timeline and place model for answering "where"
questions without forcing raw coordinates, visits, and place labels into the
claim/belief pipeline too early.

The core distinction: the historical fact of where the user was at a moment
does not change, but Engram's knowledge and interpretation of that fact can
change. Raw samples are immutable. Derived visits, place labels, and "home" or
"work" roles are revisable projections over evidence.

## Background

The human requirements make location central to Engram's long arc:

- every address ever lived at,
- daily location history,
- places that mattered,
- travel with dates and companions,
- frequented places,
- daily entries that say what the user did, who they saw, and where they went.

The current V1 claim/belief pipeline can represent some location facts,
especially textual claims such as "I lived in Oakland" or "I traveled to
Lisbon." But a location corpus is much denser and more continuous:

- GPS samples from Google Timeline or phone exports,
- EXIF coordinates from photos,
- calendar locations,
- reservation and receipt locations,
- GPX/activity tracks,
- manual check-ins,
- journal entries.

These are not all beliefs. Most are observations and intervals. The system
needs a location substrate that can answer day-level and event-level questions
while preserving uncertainty and privacy.

## Problem

If Engram treats location as ordinary beliefs, several things go wrong:

- A GPS point at 18:42 becomes awkward to express as a bitemporal belief.
- Thousands of samples flood the belief table with non-semantic facts.
- Place labels such as "home", "the office", or "SFO" get mixed up with raw
  coordinates, even though place interpretation is revisable.
- Exact coordinates may leak into ordinary assistant context when the user
  only needed city-level or place-category context.
- Missing days become silent absences instead of explicit coverage gaps.

The model should separate:

```text
raw location source
  -> location samples
  -> place candidates
  -> place entities and roles
  -> visit intervals
  -> day-level location coverage and summaries
```

## Proposal

### Source scope

The first location backfill should support local files or local exports:

- Google Location History / Timeline Takeout,
- EXIF GPS observations from RFC 0034,
- GPX files and fitness/activity tracks,
- calendar events with local exported locations,
- manual check-ins via capture,
- future Apple location exports where accessible.

No online reverse-geocoding API should be used by the corpus-reading process.
If place naming needs external map data, the user should explicitly download a
local gazetteer or map extract, and the location process should read it
offline.

### Raw and normalized layers

Raw location exports should be preserved as immutable source artifacts.
Normalized location samples should be derived observations:

- `id`
- `source_id`
- raw evidence reference
- `sample_time`
- source timezone or offset
- `latitude`
- `longitude`
- optional altitude
- accuracy radius
- source family
- motion/activity hint if present
- confidence
- privacy tier
- parser version
- raw payload

Location samples are observations, not beliefs. They are append-only derived
rows that can be regenerated under a new parser version.

### Place candidates and place entities

Coordinates are not places. A place model should distinguish:

**Place candidate.** A cluster or possible named location inferred from
coordinates, EXIF, calendar text, manual labels, or local gazetteer data.

**Place entity.** A canonical place Engram can refer to: "SFO", "old Oakland
apartment", "Dolores Park", "Mom's house", "Lisbon", "the gym."

**Place role.** A time-bound meaning assigned to a place: `home`, `work`,
`school`, `airport`, `gym`, `frequented_place`, `travel_destination`.

Place roles are bitemporal in the ordinary biographical sense:

```text
old Oakland apartment
  role: home
  valid_from: 2018-04
  valid_to: 2022-09
```

Those durable role assignments may become claims/beliefs when grounded by raw
evidence. Raw coordinates themselves should stay in the location layer.

### Visit intervals

A visit interval is an inferred stay at a place or coordinate cluster:

- `start_time`
- `end_time`
- place candidate or place entity reference
- spatial envelope or centroid
- evidence sample count
- supporting observation ids and raw evidence refs
- confidence
- derivation version
- privacy tier

Visit intervals are rebuildable interpretations. They can be contradicted or
superseded by better parsing, better place labels, new EXIF data, or human
correction, but the original samples remain unchanged.

Visit confidence should reflect:

- sample density,
- accuracy radius,
- source family,
- duration,
- agreement across sources,
- movement between adjacent samples,
- manual labels or calendar corroboration.

### Temporal and timezone handling

Location is a timezone stress test. The model should store:

- UTC timestamp,
- source-local timestamp where present,
- source timezone or offset where present,
- inferred local timezone and confidence,
- parser decision metadata.

Daily biography queries need local-day grouping. The local day for a sample
should be computed from the best available timezone at that coordinate and
time, but the raw timestamp and inference trail must remain auditable.

### Privacy and granularity

Exact coordinates are Tier 1 by default. Context outputs should generally
surface coarser location unless the user explicitly asks for precision and the
privacy policy permits it.

Possible granularity levels:

- exact coordinate,
- named private place,
- named public place,
- neighborhood,
- city,
- region,
- country,
- travel/home/work category,
- unknown with coverage gap.

The location compiler should be able to answer:

- "You were in San Francisco that evening."
- "You appear to have been at a restaurant in the Mission."
- "Exact coordinates are available but not included at this context tier."

This preserves usefulness without leaking more than necessary.

### Coverage gaps

Location coverage should be explicit. For each day or interval, Engram should
know whether location evidence is:

- high coverage,
- partial coverage,
- photo-only,
- calendar-only,
- manual-only,
- absent,
- intentionally disabled or unavailable where known.

This is the location-specific form of D018's missing data lane. A day with no
samples should not be mistaken for a day spent nowhere.

### Relationship to claims and beliefs

Location observations can support claims and beliefs, but should not all become
claims:

- A raw GPS sample remains a location observation.
- A visit interval remains a location interpretation.
- "I lived at this address from 2018 to 2022" can become a belief.
- "I traveled to Lisbon in June 2015" can become an event belief.
- "I often went to this gym in 2023" may become a frequented-place belief if
  the pattern is strong enough and the user wants that class of inference.

The location layer should prefer answering "where" from visits and samples
directly. It should promote only durable semantic facts into beliefs.

## Non-goals

- Shipping this in V1.
- Online reverse geocoding, hosted maps, or hosted place APIs.
- Choosing PostGIS, a local gazetteer, or a map data format in this RFC.
- Inferring sensitive routines by default.
- Treating exact location history as ordinary assistant-visible context.
- Replacing a maps application or timeline UI.

## Open questions

1. Should the first schema use plain latitude/longitude columns, PostGIS, or an
   optional PostGIS extension? Plain columns may be enough for personal scale;
   PostGIS may pay off for place polygons and spatial indexes.
2. How much local gazetteer data should be bundled or required? None by
   default is safest; explicit user-downloaded extracts preserve local-first
   while enabling better place names.
3. What is the right place-review UX for naming clusters such as "old office"
   or "Alice's apartment"?
4. Should frequent-place detection run automatically, or only after the user
   opts into a sensitive-routine inference stage?
5. How should location evidence from photos and Google Timeline be weighted
   when they disagree?
6. How coarse should default `context_for` location output be for Tier 2
   assistant contexts?

## Acceptance criteria for promotion

This RFC is ready to promote when:

- RFC 0033 has an accepted observation storage shape,
- the first local location source is selected,
- exact-coordinate privacy defaults are accepted,
- a place/visit schema is specified,
- timezone and local-day rules are specified,
- a bounded sample backfill can answer "where was I on this day?" with
  provenance and explicit gaps.

Until then, this RFC records the intended location substrate for post-V1
biographical expansion.
