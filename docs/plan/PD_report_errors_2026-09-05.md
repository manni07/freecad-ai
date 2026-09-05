# Plan: report-view errors

## QWF and sequence

1. Diagnose all three message classes from source/current artifacts (coverage high, no mutation, low risk).
2. Phase A: implement logger severity and font corrections after simulation/TD review (high coverage, low effort, reversible code change).
3. Phase B: native copied-model validation; repair a new copy only if a concrete defect is proven (high importance, data risk controlled by copying, depends on diagnosis).
4. Phase C: focused/full tests, independent security/code review, native integration evidence, documentation and scoped repository integration (depends on A/B).

## Fixed team and stages

Root supervisor: workspace/authority, real native validation, integration. Dedicated orchestrator: architecture/simulation/test plan/gates/artifacts. Logging worker: implementation, focused unit evidence. Recovery/reviewer worker: model structure diagnosis and independent review. Four total; no further agents.

Thorough stages are retained: foundation/review → implementation simulation >95 → implementation → test-strategy refinement → test simulation → security/unit → integration → native E2E → documentation/devops/performance. TCCode moves initial test definition before code; canonical stage 4 refines it rather than creating tests late.

## Risk register

| Risk | Three mitigations |
|---|---|
| A: Logging recursion/duplicate records | namespace-local configuration; repeat-install tests; preserve unrelated handlers |
| A: Thread/GUI coupling | use FreeCAD console API; no direct widget mutation; worker-thread test and native evidence |
| A: Hidden errors/protocol contamination | standard-level mapping; traceback tests; stdio/headless regression |
| A: Font appearance/probe changes | preserve sizes/boldness; default font copy; local PNG/Qt validation |
| B: False corruption conclusion | CRC/XML is only first layer; native reopen copy; object/shape checks |
| B: User data loss | hash original; never overwrite; separate output with verified reopen |
| C: False completion | explicit skipped tests; runtime HOLD when unactivated; evidence-bound final report |
| C: Unrelated publication | isolated worktree; exact staged path list; parent dirty state check |

## agy review

`agy --help` and corrected read-only plan-mode one-shot review succeeded; see review record below. External review cannot authorize writes, restarts or publication. Non-functional/permission-blocked review is recorded and replaced with independent local review under TCCode.

[ARD](../dossiers/ARD_report_errors_2026-09-05.md) · [TRD](../dossiers/TRD_report_errors_2026-09-05.md) · [ID](../dossiers/ID_report_errors_2026-09-05.md) · [TD](../tests/TD_report_errors_2026-09-05.md)

## External read-only review (agy)

`agy --help` succeeded. First `agy --print --mode plan ... --prompt <text>` returned 2 because this CLI treated `--mode` as the print prompt. Corrected subprocess argv used `agy --mode plan --print-timeout 1m0s --print=<self-contained-text>` and returned 0. The review explicitly used supplied text only, no files/tools/tests; no session ID was exposed. It judged READY FOR EXECUTION, not completed verification.

Accepted: namespace-local non-propagating logging, idempotence, unrelated handler preservation, traceback tests, stdio separation, worker-thread/native proof, isolated font rendering, copy-only model checks without recompute. Rejected: calling the model corrupt before native evidence (unproven); adding manual traceback concatenation (logging.Formatter already preserves it); obligatory extra user approval (task authorizes this bounded fix); speculative Qt dispatcher (only add if native thread evidence requires it); redesigning the four-person allocation (already fixed). DEBUG→PrintLog is a reasonable optional refinement but not required by screenshot intent; either tested native DEBUG sink must preserve its configured level. Generic `QCoreApplication` is insufficient for actual GUI fonts; use offscreen QApplication. The review's expanded acronym labels do not replace TCCode dossier contracts.
