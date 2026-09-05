# Architecture requirements: report-view errors

Prepared before implementation; finalized 2026-09-05. Task: distinguish and fix the attached FreeCAD warnings/errors with TCCode and Agent Workflow v4 thorough, four total team members.

## Evidence and architecture

The screenshot contains three independent classes: Qt resolves an unavailable `Sans` font; native FreeCAD reports a document read failure; Python INFO MCP startup messages appear as errors. `mcp_server_http.py` configures root logging at INFO with default stderr. `freecad_ai/mcp/gui_server.py`, `transport.py` and `server.py` emit the displayed startup text through Python logging. `chat_widget.py` constructs two Sans fonts; `llm/client.py` constructs a third for the local vision test image.

The addon runs inside FreeCAD and must preserve FreeCAD's console severity semantics. Target flow: addon logger → severity-aware FreeCAD console handler → native report view. Worker/server threads must not directly mutate Qt widgets. CLI stdio transport remains separate and protocol stdout must remain clean.

## Acceptance and boundaries

- INFO startup text reaches PrintMessage, WARNING reaches PrintWarning, ERROR/CRITICAL reach PrintError; errors and traceback context remain visible.
- Configuration is idempotent and works for script and toolbar routes without changing unrelated loggers or requiring a restart.
- UI/probe fonts derive from an available/default application font and retain sizes/boldness; do not suppress Qt warnings globally.
- Model diagnosis uses a copied fixture. Original model and backups must remain hash-identical. CRC success alone does not prove a valid FreeCAD document.
- A repaired model, if needed, must be a new separately named file and pass native reopen/shape validation before offered for use. Never overwrite the user's original.
- Existing GUI/server, profile, security policy and unrelated dirty checkout remain unchanged. No reboot/restart, stopping, hot reload or live-model edit is authorized.

## Lessons and conflicts

Existing diary records the distinction between mocked tests and FreeCAD runtime evidence, isolated profile requirements and fail-closed release gates. No `docs/settings/` or `docs/lessons_learnt_project.md` was found. Prefer these current repository lessons over a generic browser-only test rule: FreeCAD is native Qt; native isolated tests are the relevant alternative explicitly provided by TCCode. Team size four overrides the canonical illustrative 12–15 thorough roles; roles are combined, stages retained. User surgical-change rules override generic refactoring of pre-existing large files.

## Traceability

[TRD](TRD_report_errors_2026-09-05.md), [ID](ID_report_errors_2026-09-05.md), [plan](../plan/PD_report_errors_2026-09-05.md), [tests](../tests/TD_report_errors_2026-09-05.md).

## External read-only review (agy)

`agy --help` succeeded. First `agy --print --mode plan ... --prompt <text>` returned 2 because this CLI treated `--mode` as the print prompt. Corrected subprocess argv used `agy --mode plan --print-timeout 1m0s --print=<self-contained-text>` and returned 0. The review explicitly used supplied text only, no files/tools/tests; no session ID was exposed. It judged READY FOR EXECUTION, not completed verification.

Accepted: namespace-local non-propagating logging, idempotence, unrelated handler preservation, traceback tests, stdio separation, worker-thread/native proof, isolated font rendering, copy-only model checks without recompute. Rejected: calling the model corrupt before native evidence (unproven); adding manual traceback concatenation (logging.Formatter already preserves it); obligatory extra user approval (task authorizes this bounded fix); speculative Qt dispatcher (only add if native thread evidence requires it); redesigning the four-person allocation (already fixed). DEBUG→PrintLog is a reasonable optional refinement but not required by screenshot intent; either tested native DEBUG sink must preserve its configured level. Generic `QCoreApplication` is insufficient for actual GUI fonts; use offscreen QApplication. The review's expanded acronym labels do not replace TCCode dossier contracts.
