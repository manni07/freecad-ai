# Follow-up proposals: installed-source integration

2026-09-06. These are future proposals, not added implementation scope. Successor to [previous report-fix proposals](PPD_report_errors_2026-09-05.md). QWF ranks requirement coverage, effort, risk, reversibility and dependency impact.

| Rank | Proposal | Current → target | Effort / risk / dependency |
|---|---|---|---|
| 1 | P1: repeatable integration manifest template | task-specific private hashes → concise reusable evidence checklist | low / low / none |
| 2 | P2: loaded-versus-disk acceptance checklist | prepared files can precede activation → explicit three-layer evidence | low / low / activation authority |
| 3 | P3: copied recovery-status regression fixture | basename fix plus stale Corrupted records → stable positive/negative status tests | medium / medium / isolated native candidate |
| 4 | P4: identity-preserving backup contract | save_document is a save-as operation → reviewed saveCopy operational procedure | medium / medium / user-state authority |
| 5 | P5: combined test-inventory report | older public counts hide newer local features → exact collection comparison | medium / low / repeated need |

## P1 — Reusable integration manifest template

Rationale: fresh preflight changes made yesterday's apply-check insufficient. A small template can preserve what was tested and what stayed untouched without adding a deployment framework.

Pros: catches drift; documents task ownership; supports precise rollback.
Cons: adds maintained evidence; hashes do not prove semantics; snapshots require storage.

| Risk | Three mitigations |
|---|---|
| Snapshot captures secrets | source allowlist; exclude private profiles/models; scan before publication |
| Manifest becomes stale | timestamp generation; fresh pre-integration comparison; reject mismatch |
| Template expands into framework | start with document; retain simple deterministic commands; require repeated need before automation |

## P2 — Loaded versus disk acceptance

Rationale: a successful merge or patch does not reload Python modules or recreate Qt widgets. Record repository, installed-file and active-runtime evidence separately.

Pros: prevents false completion; clarifies restart authority; eases support diagnosis.
Cons: runtime proof needs a session; active objects can differ from files; privacy redaction is required.

| Risk | Three mitigations |
|---|---|
| Evidence collection triggers reload | readonly inspection only; forbid importlib.reload; isolate probe processes |
| Partial runtime sampled as full proof | identify module/widget boundaries; test authenticated read; preserve unexercised gates |
| Private paths leak | placeholders publicly; local mapping private; exact staged scan |

## P3 — Copied recovery-status regression

Rationale: a corrected absolute-path validator can coexist with already-persisted Corrupted records. Test the complete state transition using synthetic copied metadata before any real-cache action.

Pros: catches stale status; distinguishes invalid files; supports upstream regression reporting.
Cons: metadata format varies; GUI harness adds maintenance; synthetic cases may miss real recovery complexity.

| Risk | Three mitigations |
|---|---|
| Test touches actual recovery cache | isolated profile; fixed fixture root; before/after installed-cache hash guard |
| Fixture promotes invalid recovery | negative ZIP/XML controls; require native read; preserve original metadata copies |
| Version-specific test generalized | bind version/source; document unsupported schemas; fail on unknown status |

## P4 — Identity-preserving backup procedure

Rationale: existing save_document assigns FileName after saveCopy and is not a transparent backup. A narrowly reviewed operational procedure can preserve unsaved document identity without adding a new tool API.

Pros: protects unsaved work; preserves document associations; provides a verifiable copy.
Cons: needs explicit live-state authority; large models take time; saveCopy side effects need native checks.

| Risk | Three mitigations |
|---|---|
| Backup alters active identity | record Name/FileName/Modified; verify after saveCopy; stop on drift |
| Backup overwrites another file | unique exclusive destination; preserve existing files; validate ownership/root |
| Copy appears successful but cannot load | hash written bytes; reopen in isolated process; compare object/link inventory |

## P5 — Combined collection report

Rationale: the published1642-test result excluded local Qt and later preflight tests. A simple collection comparison could expose accidental omissions before time is spent running a candidate.

Pros: reveals missing local tests; explains count changes; improves reproducibility.
Cons: collection can import code; optional environments affect inventory; comparisons need interpretation.

| Risk | Three mitigations |
|---|---|
| Collection mutates profile | isolated HOME/config; no native user session; inspect collection fixtures |
| Legitimate removals treated as failure | record source changes; review node-id delta; distinguish deselection from omission |
| Counts replace intent | retain test names/areas; require native boundary tests; report failure/skip reasons separately |

## Decision and review

P1/P2 are small documentation-first follow-ups. P3/P4 require isolated evidence and explicit live-state boundaries. P5 should remain a simple report, not a new CI framework, until repeated integrations justify it. No proposal authorizes restart, live backup, native app replacement or publication of dirty parent features. External review completed with `agy --mode plan --print-timeout 1m0s --print=<self-contained text>`, exit 0. It verified all five proposals have three pros, three cons and three risks with three mitigations each; accepted the QWF order and documentation-first limits. No tools, files or network were used by that review. Its suggestion to confine recovery testing to file-only tests is not adopted as a replacement for the already-authorized isolated native GUI acceptance; real recovery behavior requires that separate evidence. Review does not authorize live changes.

[Plan](../plan/PD_installed_report_fix_2026-09-06.md) · [Open items](../openitem/installed-report-fix-open-items-2026-09-06.md)
