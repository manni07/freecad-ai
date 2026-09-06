# Plan: integrate the installed report fix

## Current verified outcome

**PASS_DISK_ONLY_RUNTIME_NOT_RELOADED.** The corrected combined suite passed1992 tests plus3 subtests in182.39 s (JUnit1995, zero failures/errors/skips). Selected native preflight checks passed10 in24.91 s. Exact combined native GUI passed with13 imported-module hashes and normal exit0. Root integrated ten scoped files: seven expected baseline changes plus three new files;337 other baseline files are unchanged. Actual installed-target tests passed63 in9.77 s, zero skips. Authenticated MCP check and read-only document inventory still pass. Live activation remains HOLD: no reload, stop or restart was performed. Eight genuine recovery-GUI cases passed with normal exit0 and a confirmed ReportOutput widget: legacy defect reproduced, candidate valid/status/negative/accept controls passed. Four additional path variants and exhaustive geometry remain NOT RUN. The native candidate is not installed.

Prepared before implementation,2026-09-06. [Previous PD](PD_report_errors_2026-09-05.md). Publication worktree base051d161; combined snapshot is private and distinct from the publication tree.

## Three candidate integration plans and QWF

| Rank | Plan | Coverage / effort / risk / reversibility / dependency |
|---|---|---|
| 1 | A: private exact-parent snapshot, surgical existing fix, full combined test, root-only ten-file integration | full targeted coverage; moderate test cost; low controlled data risk; file-level rollback; preserves local dependencies |
| 2 | B: reconcile all parent changes into a clean published branch before activation | potentially broad coverage; high effort/review; expands publication scope; reversible only with careful patch separation; depends on unrelated feature approvals |
| 3 | C: runtime hot reload or complete checkout/Mod-link replacement | incomplete reliable coverage; deceptively low effort; high singleton/thread or feature-loss risk; difficult live rollback; depends on unsaved GUI state |

Choose A. B is deferred because user only authorized current task scope. C is rejected: existing controller/thread/registry and Qt widget objects persist, and changing Mod target would drop local repairs/features. Native recovery upgrade preparation is independent of this ranking and stays separate from addon integration.

## Phases and risk controls

1. A — inventory/snapshot/surgical overlay. Root builds private code-only candidate; orchestrator gates before workers execute tests.
2. B — combined full unit and isolated native GUI verification, plus independent scope/security review. Fix only task-caused defects; surface parent-baseline defects separately.
3. C — isolated native candidate selection/preparation and copied-fixture recovery validation. If unavailable, deliver exact provenance/build blocker and ready reproduction plan.
4. D — root integrates five runtime files, four matching regression/fixture files and one local preflight timing-test correction only after A/B and fresh drift checks; records hashes. No restart, reload, model backup/save or signed-core replacement. Document activation preparation and remaining authority gates.

| Risk | Three mitigations |
|---|---|
| A: stale snapshot loses newer preflight edits | fresh inventory; per-file before/after hashes; reject drift immediately before integration |
| A: private material copied/published | explicit code/test allowlist; exclude profiles/models/keys/cache/env; staged privacy scan |
| B: tests silently omit local functionality | compare collection inventory; include local/untracked test files; report skips and baseline failures separately |
| B: native fixture touches live session | new owned process; isolated profile/config/temp; no server/model from user session |
| B: report patch damages asynchronous review | preserve non-font chat hunks; combined preflight/dispatcher tests; independent diff review |
| C: wrong build or untrusted candidate | primary provenance; architecture/source-fix verification; separate candidate destination and hashes |
| C: invalid recovery data hidden | invalid control fixtures; copied Corrupted-state tests; no live cache cleanup |
| D: unsaved identity altered by backup | do not use save_document as backup; design native saveCopy with identity before/after; wait for separate live-state authority |
| D: partial activation called complete | distinguish disk/loaded modules; restart HOLD explicit; post-activation auth/read-only/native gates |

## Review

Reuse the adopted master_orchestrator profile and canonical thorough stage order; no extra agents. agy self-contained text-only plan/ID/TD review follows documented current print syntax; unavailable review is a stated local-review fallback, never permission to broaden scope.

[ARD](../dossiers/ARD_installed_report_fix_2026-09-06.md) · [TRD](../dossiers/TRD_installed_report_fix_2026-09-06.md) · [ID](../dossiers/ID_installed_report_fix_2026-09-06.md) · [TD](../tests/TD_installed_report_fix_2026-09-06.md)

## External plan/ID/TD review

`agy --help` succeeded; `agy --mode plan --print-timeout 1m0s --print=<self-contained text>` returned0. It reviewed supplied text only, without files/tools/tests; no session ID exposed. Accepted: non-target manifest equality, rollback/drift checks, candidate ARM64/signature provenance, explicit Unicode-path fixture, and persisted-Corrupted-status boundary. Existing pre-code gate already covers snapshot hashing and all four actual team roles.

Corrected/rejected review inaccuracies: public base051d161 is not the combined dirty-parent base; the native saveCopy operation was not shown to change identity—the existing save_document handler explicitly assigns FileName afterwards; two documents are modified, not simultaneously active; existing native GUI harness is available, so absence of automation is not established. Full geometry is a separate unresolved model gate, not a new requirement to rewrite logging. Invented file URLs, new team roles and extra generic approval requirements are not adopted. No live backup, restart, core/cache change or publication of dirty features was authorized by review.
