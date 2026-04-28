# Security

Specific security considerations for engram. The principles in
[HUMAN_REQUIREMENTS.md](HUMAN_REQUIREMENTS.md) set the constraints; this
document covers how the implementation enforces them and what's still
open.

This is a **skeleton**. Sections marked **(TBD)** are unresolved
implementation decisions. Sections marked **(decided)** point back to a
HUMAN_REQUIREMENTS resolution.

## Threat model

The asset is the user's complete time-indexed biography. Concentration of
this asset on user hardware makes the user the high-value target of any
attacker.

**In scope:**

- Remote attackers (network-borne malware, compromised dependencies,
  supply-chain attacks on the engram process or its model substrates)
- Local attackers with physical access (device theft, device seizure,
  border / customs)
- Compromised tool services (cloud APIs the action-taking model invokes)
- Prompt injection via tool output (a web page or email designed to
  exfiltrate)
- Malicious or accidental egress by the engram-reading model itself
- Posthumous compromise of dead-man-switch infrastructure

**Out of scope:**

- A nation-state with arbitrary on-device root and unbounded patience.
  Engram raises the cost of compromise; it does not promise to defeat
  unbounded adversaries.
- The user being coerced into entering credentials. Out-of-band threat.
- Side channels in the underlying CPU / OS / firmware. The trust
  boundary is the hardware.

## Security properties claimed

Cross-references to the seven foundational principles in
HUMAN_REQUIREMENTS.md:

- **Local-first.** No data leaves the machine. Enforced at the network
  layer for the engram-reading process. (See *Process isolation*,
  *Network egress*.)
- **Corpus / network separation.** Engram-reading process has no network
  egress; network-using process has no direct corpus access. Enforced
  at the OS level. (See *Process isolation*.)
- **Raw is sacred.** Raw artifacts are immutable, content-addressed,
  encrypted at rest. (See *Data at rest*.)
- **Refusal of false precision.** Confidence and provenance propagate to
  consumers; the system refuses to assert what it doesn't know. Not a
  classical security property, but the contract that prevents downstream
  misuse of context.

## Process isolation **(Resolved for V1)**

The principle commits the design to: engram-reading process has no
network egress; network-using process has no direct corpus access.
Implementation options under consideration:

- **OS-level network namespace** (Linux) / sandboxed app (macOS) for
  the engram-reading process. Default-deny on the network interface.
- **Separate user accounts** with filesystem ACLs preventing the
  network-using process from reading the engram database directly.
- **IPC-only communication** between processes (Unix domain sockets,
  explicit message types — never raw queries).

**V1 Implementation:** Enforced via OS-level network namespace (Linux) or sandboxed app (macOS) for the engram-reading process, with default-deny on the network interface. The MCP server binds only to `127.0.0.1`.

## Data at rest **(Resolved for V1)**

The database itself must be encrypted with a key not derivable from the
OS login alone. Options:

- pgcrypto / column-level encryption for sensitive tiers, leaving low-
  sensitivity tables in the clear for query performance.
- Filesystem-level encryption (FileVault, LUKS) is necessary but not
  sufficient — it protects against device theft only when locked, not
  against malware running as the user.
- Application-level encryption with key held in OS keychain / hardware
  enclave.

**V1 Implementation:** Postgres data directory encrypted via LUKS (or equivalent FDE). Key held by user at login.
*Note:* Tier-5 (redact-on-death) requires a separate destroyable key regardless (cryptographic erasure). See *Posthumous handoff*.

## Network egress **(TBD)**

For the network-using process (the action surface):

- **Default-deny.** Outbound traffic blocked unless an explicit tool
  grant is active.
- **Domain allowlist.** Only domains the user has explicitly approved
  per task.
- **Egress proxy** with audit log of every outbound request:
  destination, payload size, originating prompt context.
- **Anomaly hold.** New domains, unusually large payloads, or
  suspicious patterns require user confirmation before sending.

Open: where the proxy lives (in-process vs separate daemon), allowlist
update flow, how egress decisions are surfaced to the user without
training them to click-through.

## Tool input handling **(TBD)**

Tool output (web pages, emails, calendar events, API responses) is
treated as adversarial input.

- **Instruction-shaped content quarantined.** Anything that looks like
  natural-language instructions in tool output is stripped, escaped, or
  flagged before being passed back to a model.
- **No model that processes tool output ever has elevated capability.**
  The processing model has no corpus access and no further tool
  capability.
- **Prompt-injection pattern detection.** A small classifier flags
  obvious injection attempts; the response to a flagged input is
  refusal, not best-effort handling.

Open: quarantine-layer design, detection-model choice, acceptable false
positive / negative rates.

## Key management **(TBD)**

Three classes of key:

1. **Disk-encryption key** for the engram database. Held in OS keychain
   / hardware enclave; unlocked at session start.
2. **Tier-encryption keys** (one per privacy tier, where tier-aware
   encryption is used). Some held by the user, some by the dead-man-
   switch infrastructure.
3. **Posthumous-release keys.** Held by successors in some form. See
   *Posthumous handoff*.

Open: rotation policy, recovery posture (probably "none — engram is
willing to lose data over leak data"), hardware-token requirements.

## Posthumous handoff **(decided — see HUMAN_REQUIREMENTS)**

Policy: encrypted dead-man's-switch releases keys to designated
successors after a confirmed inactivity period.

Security implementation considerations:

- **Heartbeat must be unforgeable.** A simple timer the user can
  suppress is a forgery surface for an attacker who has compromised the
  user's machine. The heartbeat requires a signed timestamp with a key
  the attacker doesn't have, witnessed externally.
- **Release-key custody must not be cloud-mediated.** Threshold secret
  sharing across human / hardware-token holders is the default posture.
  Cloud key escrow is disqualifying.
- **Tier-5 destruction is cryptographic.** Tier-5 categories are
  encrypted under a separate key that is destroyed *before* release.
  Withholding the key from successors is insufficient — the key must
  be erased so a successor with full access cannot decrypt those rows.

Open: heartbeat protocol, M-of-N parameters for secret sharing, who
holds shares, how the user updates successor designations over time.

## Privacy tiers **(TBD — coupled to posthumous)**

The five-tier model from HUMAN_REQUIREMENTS:

| Tier | Audience |
|------|----------|
| 1 | only-me, only-this-machine |
| 2 | surfaceable to AI assistants |
| 3 | partner / chosen heirs |
| 4 | posthumous-only release |
| 5 | redact-on-death |

Security implementation:

- **Tier 1 vs Tier 2** is a process-boundary question: whether a given
  context may include the row. Enforced by the read-side decision to
  include in `context_for(...)`, not by encryption.
- **Tier 3+ requires per-recipient encryption** so the right successor
  decrypts the right slice.
- **Tier 5 requires a separate destroyable key.**

Open: per-category default tier (Health → 1? Finances → 1? Daily log →
2?), tier-update flow, audit trail of tier changes.

## Backup security **(TBD)**

- Backups are encrypted at rest with user-held keys.
- No SaaS sync — explicitly disqualified by local-first.
- 3-2-1 backup posture applies: three copies, two media, one off-site —
  "off-site" cannot mean a cloud service.
- Off-site location options: encrypted external drive at a different
  physical location, hardware token at a trusted human's residence,
  encrypted USB in a safe deposit box.

Open: backup frequency, restoration drill cadence, off-site rotation
policy.

## Audit logging

- Every outbound network request from the action surface, with
  destination, payload size, timestamp, originating prompt context.
- Every belief insertion / supersession recorded in `belief_audit`.
- Every privacy-tier change.
- Every posthumous key-share access (if logging is reachable at that
  point).

Logs live in the engram database under their own table, with the same
encryption posture as the rest. Logs that are themselves sensitive get
the same tier treatment as the data they describe.

Open: retention policy, log-review tooling.

## Known limitations / accepted risks

- **Capability ceiling.** Local-only inference means engram is bounded
  by the local model's quality. Frontier models may reason about the
  user better than the local stack can. Accepted in exchange for the
  data-egress guarantee.
- **Imperfect prompt-injection defense.** No quarantine layer is
  perfect. A determined adversary with control of an approved tool may
  still find a path. The defense is layered — no corpus access in the
  network process, default-deny egress, audit logs — so any single
  failure does not produce full corpus exfiltration.
- **No defense against the user.** The user can always export their own
  corpus to a cloud service. The system makes that a deliberate
  action, not an accident.
- **Hardware trust boundary.** A compromised CPU, firmware, or OS root
  is out of scope. Engram raises the cost of compromise; it doesn't
  defeat unbounded adversaries.

## Vulnerability disclosure

For security-relevant issues — anything that affects corpus / network
separation, posthumous-handoff integrity, encryption-at-rest properties,
or the egress guarantee — please report privately rather than via the
public issue tracker.

[Contact / process — TBD]

## Open questions

Consolidated from the sections above:

1. Process isolation enforcement mechanism (OS namespace, separate user,
   sandboxed app, or composition).
2. Tier-aware encryption vs single DB key.
3. Egress proxy: in-process vs separate daemon.
4. Quarantine-layer design for tool input.
5. Heartbeat protocol for the dead-man's-switch.
6. M-of-N parameters for posthumous key sharing, and who holds shares.
7. Per-category default privacy tiers.
8. Off-site backup rotation policy.
9. Vulnerability disclosure contact and process.
y.
9. Vulnerability disclosure contact and process.
