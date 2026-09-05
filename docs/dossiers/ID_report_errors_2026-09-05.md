# Implementation dossier: report-view errors

Status: implementation plan prepared before code. Base `6e51894`, branch `agent-workflow/20260905-report-errors`, isolated worktree `<worktree>`.

## Phase A: addon logging and fonts

Read the shared `freecad_ai/mcp/gui_server.py` controller, immediate toolbar and script callers, logger use in `server.py`/`transport.py`, Qt compatibility exports and existing tests before editing. Introduce the smallest reusable console handler needed by both GUI startup routes. Prefer a dedicated small module only if keeping the controller implementation simple warrants it. Configure the addon namespace before startup INFO records. Choose FreeCAD Console methods from record severity; append exactly one record terminator, retain formatter exception handling and avoid recursion. Make repeat installation deterministic; do not replace global root handlers or redirect process stdout. Ensure standard Python logging behavior remains available outside native GUI context. Remove the entrypoint's root-wide basicConfig if replaced by the native shared setup. Configure launcher and Workbench.Initialize; inspect direct ToggleMCPServerCommand.Activated and cover pre-initialize invocation through the smallest shared boundary if necessary. Do not reclassify actual errors as information.

For `freecad_ai/ui/chat_widget.py`, copy the relevant current widget/application font and set 10 point size for chat and input. For `freecad_ai/llm/client.py`, obtain a default resolved font, set 32 points and bold for the local PNG probe. Keep PySide compatibility through the existing shim. Do not add a platform-specific installed font name, global Qt warning filter or network vision test.

Tests must first reproduce INFO→stderr and unavailable-family requests, then verify severity preservation and default-family use. Worker reports exact commands, fail/pass counts and changed paths. Existing large files receive only surgical changes; generic profile line limits do not justify unrelated refactoring.

## Phase B: model diagnosis and conditional recovery

Inventory archive entries, CRC and XML references on the existing file read-only. Root records the known SHA before and after. Run native FreeCAD against a copy in a private fixture directory with isolated user/system configuration and offscreen/native CLI where supported; do not touch the open user session. Record load exception, object count, shape state and native diagnostics. If no concrete native failure reproduces, document that result and residual live-session uncertainty. If a structural defect is reproduced, first update this dossier with exact bytes/structure to repair, obtain independent review, then produce a separately named repaired copy and reopen it. No model mutation is approved by this initial plan.

## Phase C: assurance and handoff

Run Phase A focused tests and available full unit regression using the validated interpreter. Run source lint relevant to changed code and check diffs. Reviewer checks security boundaries, native-thread behavior, duplicate logging and severity. Root owns real integration and explicitly labels any unavailable/unsafe GUI test HOLD. Record model hash unchanged. Create exactly three High, three Medium and three Low classified open items before final docs; completed concerns can remain closed with evidence. Then update STP, HTML manual, diary below 1000 lines and five ranked proposals. Repository integration remains root-owned, only current-task scope eligible; unconfirmed older dirty work is excluded.

## Simulation: iteration 1, design readiness only

Scores are engineering judgments of this bounded plan, not measured test success or guaranteed outcomes. Each score is >95 as required by Agent Workflow v4. Whole-system completeness is conditional on explicit HOLD treatment for live activation; it does not assert model recovery is complete.

| Phase | C1 feasibility | C2 correctness | C3 completeness | C4 risk control | C5 maintainability | Basis |
|---|---:|---:|---:|---:|---:|---|
| A | 99 | 97 | 97 | 97 | 98 | existing logging/console/font APIs, scoped handler, severity/reentry/Qt tests |
| B diagnosis | 98 | 97 | 96 | 99 | 98 | copied fixtures, layered native validation, no speculative repair |
| C | 98 | 97 | 97 | 98 | 98 | tests, independent review, explicit evidence/HOLD and scoped Git |
| Whole plan | 98 | 97 | 96 | 98 | 98 | all three screenshot classes assigned, recovery mutation separately gated |

TCCode additional criteria: integration fit 97, safety 99, testability 98, performance 97, observability 99, rollback readiness 99. Justification: shared start boundary; no live mutation; mock/native split; no I/O added to logging; severity retained; isolated branch and immutable model. Any concrete new defect requires dossier update and gate reassessment. Model repair implementation itself is HOLD until a defect and exact repair are known.

[ARD](ARD_report_errors_2026-09-05.md) · [TRD](TRD_report_errors_2026-09-05.md) · [PD](../plan/PD_report_errors_2026-09-05.md) · [TD](../tests/TD_report_errors_2026-09-05.md)

## Final implementation and gate result

Implemented five runtime files: new namespace console handler, HTTP launcher, InitGui Initialize/direct-toggle setup and three font constructions in chat/client. Four test files cover intent, native Qt fixtures and legacy launcher Console fidelity. Initial full-regression failure (two incomplete test doubles) was corrected without weakening production behavior.

Scoped commit `b785feb8748327c4b5dc439f8500320f004b102f` on remote base `5abeb8879d093a7c0853ecd34fd8aa8f80d15280` excludes unrelated predecessor `6e51894`. Final exact-code suite1642passed177.58s, zero skips; critical lint and independent nine-file review PASS. Byte-identical runtime files preserve real native GUI severity/thread/font proof. Final documentation is separate; root owns PR/merge.

Phase B native copy load163objects64links and installed checker CWD A/B passed. The warning is an upstream FreeCAD1.1.3 basename defect; no model rewrite, binary patch or live workaround was applied. Generic read error not reproduced; full isValid remains NOT_COMPLETED_CPU_BOUND. Existing GUI activation and native core correction HOLD; safe reviewed five-file activation patch exists privately, not applied. See STP/TD for exact boundaries and next validation.
