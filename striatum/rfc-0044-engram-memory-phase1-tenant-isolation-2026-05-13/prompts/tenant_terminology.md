# Tenant Terminology And RFC 0044 Amendment Handoff

Read:

- `/home/halbritt/git/striatum/ENGRAM_DEVELOPER_REQUEST.md`
- `/home/halbritt/git/striatum/docs/rfcs/0044-engram-phase-1-implementation-spec.md`
- Engram canonical docs listed in the workflow context.

Produce only:

- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/TENANT_TERMINOLOGY_HANDOFF.md`

Required content:

- Confirm the final vocabulary for local isolation under the same machine owner
  and root authority.
- State that `tenant_id` is the application-memory-system boundary, not hosted
  multi-tenancy.
- State that `corpus_id` is the workload/dataset boundary inside a tenant.
- Account for future local application memory systems beyond Striatum.
- Identify any RFC 0044 wording that still says only `corpus_id` where
  `tenant_id` plus `corpus_id` is required.
- List the implementation requirements future agents must read before coding.

Do not implement code, create migrations, write the ingester, write the MCP
server, run tests, or perform design review.

Use this artifact shape:

```md
# RFC 0044 Tenant Terminology Handoff
author: <packet author line>

Status: queued
Date: 2026-05-13
External Striatum RFC: 0044
Decision refs: D001, D002, D020

## Terminology

## Required RFC Amendment Notes

## Implementation Preconditions

## Non-Goals Preserved
```
