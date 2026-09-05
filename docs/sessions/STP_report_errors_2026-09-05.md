# Session transfer: FreeCAD report-view errors

Final verification:2026-09-05. TCCode full workflow plus Agent Workflow v4 thorough; four total members: root supervisor, dedicated orchestrator, logging implementer, recovery/reviewer. Addon code and isolated native tests PASS; existing user session activation and installed native recovery-core correction HOLD.

## Exact repository scope

- Investigation base `6e51894` was excluded from publication because it contained an unrelated unpublished dispatcher predecessor.
- Scoped code commit `b785feb8748327c4b5dc439f8500320f004b102f` on base `5abeb8879d093a7c0853ecd34fd8aa8f80d15280` contains exactly nine current-task code/test files.
- Branch `agent-workflow/20260905-report-errors`; public destination `manni07/freecad-ai`, explicitly not the upstream fork target.
- Documentation commit/PR/merge are root-owned after this dossier freeze. The user's previous commit/PR/merge authorization applies to this scoped task; unrelated dirty parent changes are excluded.
- Public placeholders: `<worktree>`, `<user-checkout>`, `<FreeCAD.app>`, `<python-test-site-packages>`, `<original.FCStd>`. Exact private paths and model hash are retained only in untracked `.report-errors-evidence/orchestrator-private-path-mapping.json`.

## Change and evidence

Addon namespace handler preserves native severity: INFO→PrintMessage, WARNING→PrintWarning, ERROR/CRITICAL→PrintError. It preserves tracebacks, root/unrelated handlers and explicit levels, installs idempotently at launcher/Initialize/direct-toggle routes and leaves stdio untouched on import. Three Sans constructors now inherit widget/application family, preserving10pt chat and32pt bold local PNG.

Final exact-code full suite: **1642 passed in177.58s, zero skipped, exit0**. Initial development full run2failed1643passed was corrected by faithful launcher Console stubs and logger fixture restoration; final count is three lower because the unrelated predecessor tests were excluded, not skipped. Focused144passed7.84s; corrected slice53passed1.41s. Critical Ruff and independent nine-file review PASS; all nine files unchanged across rebase; 277parent baseline files and original/backup model hashes unchanged.

Real isolated native GUI: old INFO red, corrected INFO/worker INFO matches native PrintMessage; genuine warning/error colors preserved; one record after repeated install. Application/actual widgets `.AppleSystemUIFont`, PNG1116bytes, no addon Qt messages, normal close exit0. No models/server in fixture. Existing live MCP read returned three documents and retained active163object modified state.

Regular copied-model native open succeeded0.267017s with163objects64links; both XML parsed, bytes unchanged, inventory19.089422s. Exact installed1.1.3 recovery checker CWD A/B false/true on identical absolute bytes proves basename bug. Installed core remains unpatched; upstream fix `1d70f987abbb429e5bcd1411fe067ac43a54785f`. Generic read error not reproduced; complete Shape.isValid NOT_COMPLETED_CPU_BOUND after120s timeout and later owned diagnostic termination. Optional3DconnexionNavlib warning remains unrelated.

## Safe activation handoff

Private `.report-errors-evidence/addon-activation.patch` contains only five tested runtime files. Root verified `git -C <user-checkout> apply --check <worktree>/.report-errors-evidence/addon-activation.patch` PASS and the installed Mod link points to the parent checkout. **Patch not applied; no activation performed.**

1. Preserve unsaved documents and verify current installed/loaded paths and hashes against private mapping.
2. Recheck the five-file patch against current parent contents; apply only the reviewed patch as part of the authorized activation step.
3. A targeted FreeCAD restart requires explicit user confirmation. Never restart/reboot a computer/server, stop the existing listener, or hot-reload native modules to bypass this boundary.
4. After authorized activation, verify authenticated MCP discovery and one read-only document tool, plus INFO/WARNING/ERROR presentation. Do not equate merged source with already-loaded code.

A normal absolute-path copy open succeeds; a recovery CWD workaround is not universal and was not applied live. Do not rewrite a valid FCStd or patch signed FreeCAD binaries speculatively. Preserve original/backups and unsaved state. Full geometry validity remains unproven.

## Reproduction and artifacts

Exact test command and all results: [TD](../tests/TD_report_errors_2026-09-05.md). Safe resume starts with `git status --short`, `git log -5 --oneline`, `git diff --stat`, then verifies current code/base before mutation.

Private `.report-errors-evidence/`: native GUI result/exit, native model and checker results, review/preservation JSON, private mapping and activation patch. Do not stage these or the copied model. The private C++ FFI diagnostic is exact-version evidence, not a general supported repair command.

[ARD](../dossiers/ARD_report_errors_2026-09-05.md) · [TRD](../dossiers/TRD_report_errors_2026-09-05.md) · [ID](../dossiers/ID_report_errors_2026-09-05.md) · [PD](../plan/PD_report_errors_2026-09-05.md) · [HTML manual](../manuals/report-errors-2026-09-05.html) · [Open items](../openitem/report-errors-open-items-2026-09-05.md) · [PPD](../vision/PPD_report_errors_2026-09-05.md) · [Workflow](../reports/report-errors-workflow-2026-09-05.json).

Both agy plan and PPD read-only text reviews returned0 after correcting print-flag syntax. Accepted/rejected feedback is in dossiers; no exposed session ID or external runtime test claim.
