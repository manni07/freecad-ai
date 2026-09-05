# Proposals after report-view diagnosis

Scope: future proposals only; none adds runtime behavior to this correction. Ranked Quick-Win-First (QWF), using requirement coverage, effort, risk, reversibility and dependency impact. Current findings support narrow follow-up decisions, not a new platform or dependency.

| Rank | Proposal | Current → target | Effort / risk / reversibility |
|---|---|---|---|
| 1 | P2: Tested version issue note | warning interpretation requires source archaeology → exact version-bound note | low / low / easy |
| 2 | P3: Installed-versus-tested version evidence | branch success can differ from active code → explicit path/hash provenance | low / medium / easy |
| 3 | P1: Native console contract check | source/unit checks → documented native severity fixture | low / low / easy |
| 4 | Read-only document integrity checklist | ZIP success can be mistaken for model validity → archive plus native object/shape checks | medium / medium / easy |
| 5 | Local redacted diagnostics bundle | ad hoc evidence → small reproducible local report | medium / medium / easy |

## P1 — Native console contract check

Rationale: Python record severity and native report-view severity are separate boundaries. Retain an isolated fixture using actual FreeCAD Console APIs with controlled INFO/WARNING/ERROR records. Label the two boundaries separately: CLI console routing and Qt GUI report-widget presentation. HOLD is a recorded status, never a hanging automated prompt.

Pros: catches red INFO regressions; protects real warning/error visibility; makes thread behavior reproducible.
Cons: requires native FreeCAD runtime; GUI versions vary; slower than unit tests.

| Risk | Mitigations (three each) |
|---|---|
| Native fixture disturbs user session | separate process; temporary profile; prohibit attaching to live GUI |
| Test mistakes mocked success for visual proof | label boundary tested; capture native output; preserve explicit visual HOLD |
| Version-dependent console behavior flakes | record binary version; bounded timeouts; maintain a minimal supported-version fixture |

## P2 — Tested version issue note

Rationale: a native application defect should be recorded against its exact source version and observed behavior so users do not damage valid documents in response to misleading recovery warnings.

Pros: prevents unnecessary recovery writes; explains provenance clearly; inexpensive maintenance.
Cons: requires version maintenance; cannot itself fix upstream binaries; notes can become stale.

| Risk | Mitigations (three each) |
|---|---|
| Applies a known defect to unrelated real corruption | state exact trigger; require native copy reopen; keep real read errors actionable |
| Upgrade advice becomes stale | date every note; link exact upstream commit; verify actual installed build before advice |
| User infers permission to patch signed application | explicitly exclude binary modification; use normal release channels only when authorized; keep workaround separate from code fix |

## P3 — Installed-versus-tested version evidence

Rationale: an isolated branch can pass while the running FreeCAD instance still has older modules loaded. Add a short documented evidence checklist for installation path, git commit and loaded module location.

Pros: avoids false completion; speeds support; makes rollback identity clear.
Cons: paths may contain private names; loaded modules can be mixed; commit identity misses dirty edits.

| Risk | Mitigations (three each) |
|---|---|
| Metadata leaks private paths | retain report locally; redact before sharing; collect only required paths |
| Commit presented as exact active content | record dirty status; hash changed modules; state loaded-versus-disk distinction |
| Check triggers lifecycle changes | readonly inspection only; no import reload; require separate restart authorization |

## P4 — Read-only document integrity checklist

Rationale: document validation needs ZIP CRC, XML, native load and shape/object evidence. Standardize the layered checklist before considering a reusable utility. Classify external document links as unresolved dependencies when their targets are intentionally outside the copied fixture; do not mislabel them as corrupt geometry.

Pros: distinguishes archive/native failures; preserves data; enables repeatable diagnosis.
Cons: shape validation can be expensive; references may depend on external files; some proxy objects need their workbenches.

| Risk | Mitigations (three each) |
|---|---|
| Inspection modifies/recomputes model | copy fixture first; do not recompute/save; compare original hash afterwards |
| Partial geometry passes unnoticed | inventory object types; report null/invalid shapes; compare expected object/link counts |
| Host dependencies change result | record FreeCAD/OCCT versions; list missing proxies/workbenches; retain exact native errors |

## P5 — Local redacted diagnostics bundle

Rationale: this investigation combines logs, branch identity, document hash and native version. A bounded local report template could reduce manual repetition without introducing remote telemetry. P3 and P5 should share one explicit redaction rule: tokenize user/home paths and omit token/config values before any sharing.

Pros: reproducible handoff; fewer missing evidence fields; no network requirement.
Cons: requires redaction discipline; more artifacts to maintain; collection may become overbroad.

| Risk | Mitigations (three each) |
|---|---|
| Secrets or document contents are collected | allowlist fields; exclude token/config values; scan report before sharing |
| Bundle becomes a second source of truth | include timestamps; preserve exact commands; link canonical source artifacts |
| Automation expands scope | begin with documented template; fixed size limits; no network or lifecycle commands |

## Review and decision

All five are proposals, not implementation commitments. QWF favors small native contract/version documentation first; a diagnostics utility should wait for repeated concrete need. Existing surgical-change rules remain controlling. Read-only `agy --mode plan --print-timeout 1m0s --print=<self-contained PPD>` returned 0 and reviewed supplied text only. Accepted its QWF adjustment to P2, P3, P1, P4, P5 because documentation has lower setup cost; added GUI/CLI boundary, external-link classification and shared redaction rule. Rejected calling documentation zero-risk/zero-effort and interpreting HOLD as an interactive wait: all artifacts still require maintenance and HOLD is a recorded evidence status. No external test success or file review is claimed.

[Plan](../plan/PD_report_errors_2026-09-05.md) · [Open items](../openitem/report-errors-open-items-2026-09-05.md)
