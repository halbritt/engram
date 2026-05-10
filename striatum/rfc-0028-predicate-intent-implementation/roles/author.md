# Author Role

Implement the accepted owner-directed RFC 0028 slice while preserving Engram's
local-first and append-only invariants.

Stay inside the packet's write scope. Record notable changes in the handoff
artifact with the exact `author:` line supplied by Striatum.
