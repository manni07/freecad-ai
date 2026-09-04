# Security Hardening Proposals after 0.23.1-alpha

## Decision frame

These are proposals, not implemented scope. Delta scoring uses security impact minus compatibility/operational cost. Quick-Win-First (QWF) orders reversible, low-dependency work before platform or protocol changes. Each proposal remains gated by its own design, tests and user approval.

## QWF ranking

| Rank | Proposal | Security delta | Effort | Compatibility risk | QWF rationale |
|---|---|---:|---:|---:|---|
| 1 | Pin CI Actions and all test artifacts | Medium | Low | Low | Supply-chain control, isolated metadata delta |
| 2 | Establish Ruff/Bandit security baseline ratchet | Medium | Medium | Low | Prevents regression without mass cleanup |
| 3 | Signed actual-host SBOM release attestation | High | Medium | Medium | Closes the largest release-assurance gap |
| 4 | OS-native secret storage and Windows ACL layer | High | High | Medium | Removes plaintext file dependence across platforms |
| 5 | Confidential remote MCP transport | High | High | High | Needed before supported LAN/remote operation |

## P1 — Immutable CI supply chain

Pros:

1. Full-commit Action pins prevent mutable tag drift.
2. Hash-locked tooling improves reproducibility.
3. Small, reviewable and easily reverted metadata change.

Cons:

1. Dependabot/renovation needs explicit upkeep.
2. Hash lists are noisy.
3. Pinning does not secure the runner image itself.

Risks:

1. Stale pins delay security fixes.
2. Transitive downloads can remain unpinned.
3. Overly strict hashes can break multi-platform resolution.

Mitigations:

1. Scheduled verified update PRs.
2. Inventory every download/install edge.
3. Test supported platforms before promotion.

## P2 — Static-analysis ratchet

Pros:

1. New findings fail CI while legacy debt remains visible.
2. Enables gradual ownership-based cleanup.
3. Preserves critical-diagnostic gate already proven useful.

Cons:

1. Baseline maintenance adds tooling.
2. Renames can appear as new debt.
3. Rule upgrades require triage.

Risks:

1. Baseline becomes a permanent suppression list.
2. Broad exception findings could be “fixed” into fail-open behavior.
3. Developers may optimize for the scanner instead of the threat model.

Mitigations:

1. Store exact finding fingerprints with owners/expiry.
2. Require behavior tests for exception-boundary changes.
3. Keep manual security review and no blanket pragmas.

## P3 — Actual-host SBOM attestation

Pros:

1. Inventories FreeCAD, Python, PySide and Qt actually shipped.
2. Enables incident lookup and CVE response.
3. Signed provenance prevents confusing synthetic and production BOMs.

Cons:

1. Requires each release platform/runtime.
2. CVE scanners can disagree or lack FreeCAD coordinates.
3. Signing infrastructure adds operational burden.

Risks:

1. Partial BOM is misrepresented as complete.
2. Local paths/identifiers leak into artifacts.
3. Scanner outages block releases indefinitely.

Mitigations:

1. Fail on any missing required component and schema-validate.
2. Retain the current privacy allowlist and review artifacts.
3. Define cached-database/offline scan policy with explicit freshness window.

## P4 — Native secret and ACL abstraction

Pros:

1. macOS Keychain, Windows Credential Manager and Linux Secret Service reduce plaintext exposure.
2. Windows ACL enforcement becomes testable rather than inferred from chmod.
3. Central abstraction can rotate/migrate secrets transactionally.

Cons:

1. Platform APIs and packaging differ.
2. Headless environments need a fallback.
3. Recovery and export are more complex.

Risks:

1. Migration can lock users out or lose credentials.
2. UI prompts can deadlock during startup.
3. Store labels/metadata may still leak provider identity.

Mitigations:

1. Copy-readback-switch transaction; never delete old value automatically.
2. Lazy access outside import/startup critical sections.
3. Document metadata and provide explicit user-controlled cleanup.

## P5 — Confidential remote MCP

Pros:

1. TLS protects Bearer tokens and document/tool traffic.
2. OAuth 2.1/Protected Resource Metadata enables principal-aware authorization.
3. Per-tool scopes could remove broad remote capabilities.

Cons:

1. Certificate and identity lifecycle is substantial.
2. Existing clients may not support the chosen flow.
3. Local-first simplicity decreases.

Risks:

1. A “TLS optional” fallback recreates the original class of defect.
2. Proxy/header trust errors can bypass origin/principal boundaries.
3. Token refresh and SSE sessions may diverge.

Mitigations:

1. Fail closed; keep Loopback/STDIO as separate explicit modes.
2. Threat-model direct and reverse-proxy deployments independently.
3. Bind every request/session to a validated principal and reauthenticate rotation.

## Recommended next decision

Approve P1 first, then P2. Run P3 in the actual release image before changing platform storage or remote transport. P4 and P5 need separate architecture/security dossiers because they change durable credentials and network trust boundaries. Independent `agy` review is required before implementation; this document records no implementation authorization.

## Independent `agy` review record

The proposal dossier was included in the final fixed-team thorough review.
Architecture/security scored the complete artifact set 97.5% and test/
documentation simulation scored 98.4%; both returned `PASS` for review quality
with no new High or blocker. Accepted feedback: keep actual-host, LAN and
Windows claims fail-closed; retain static-analysis debt and add descriptor-
pinned AGENTS reads as later defense-in-depth. Rejected feedback: none. This
review approves the dossier as a planning artifact only; it does not authorize
P1–P5 implementation.
