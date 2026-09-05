# Technical requirements: report-view errors

Prepared before implementation; finalized 2026-09-05.

| ID | Contract | Evidence required |
|---|---|---|
| R1 | Route addon logging by record severity | exact console method assertions for all standard severities |
| R2 | Preserve one record once on repeated setup | repeated setup/handler count/duplicate assertions |
| R3 | Preserve unrelated logger/root handlers and stdio protocol | sentinel handlers and standalone fallback tests |
| R4 | Configure before first MCP startup record on each GUI path | entrypoint/controller tests |
| R5 | Preserve failures, formatting and tracebacks | ERROR and exception tests |
| R6 | Remove addon `Sans` family request without changing sizes | Qt font resolution and widget/probe tests |
| R7 | Diagnose native model before changing it | ZIP/XML inventory plus native load/objects/shapes on copy |
| R8 | Preserve input model and live state | SHA-256 before/after, isolated profile and no lifecycle changes |
| R9 | Distinguish verified fix from unactivated GUI behavior | explicit runtime evidence or HOLD |
| R10 | Document reproducible repair and residual items | linked final dossiers/manual/STP |

## Existing interfaces

`logging.getLogger(__name__)` in MCP modules; FreeCAD.Console.PrintMessage/PrintWarning/PrintError; Qt compatibility shim supplies QtGui/QtWidgets for PySide versions. No new API, database, schema, migration, dependency or authentication change is intended. Log installation belongs to an existing shared GUI start boundary; exact helper placement may be updated after caller inspection.

## Model baseline

User file: `<original.FCStd>`. Root initial evidence: ZIP 234 entries, CRC check passed, GUI XML exists; SHA-256 `<original-model-sha256>`. Native validity is UNKNOWN at planning. Do not call this corrupt or healthy solely from ZIP tests.

## Safety and performance

No paid vision/provider request is needed to test local PNG generation. No native write to the original model. Log formatting should remain constant per record with no filesystem/network I/O; measure burst behavior on a fake console and native isolated font creation. Capture time as measured evidence, not the screenshot's 65 ms as a universal performance target.

[ARD](ARD_report_errors_2026-09-05.md) · [ID](ID_report_errors_2026-09-05.md) · [TD](../tests/TD_report_errors_2026-09-05.md)

## External read-only review (agy)

`agy --help` succeeded. First `agy --print --mode plan ... --prompt <text>` returned 2 because this CLI treated `--mode` as the print prompt. Corrected subprocess argv used `agy --mode plan --print-timeout 1m0s --print=<self-contained-text>` and returned 0. The review explicitly used supplied text only, no files/tools/tests; no session ID was exposed. It judged READY FOR EXECUTION, not completed verification.

Accepted: namespace-local non-propagating logging, idempotence, unrelated handler preservation, traceback tests, stdio separation, worker-thread/native proof, isolated font rendering, copy-only model checks without recompute. Rejected: calling the model corrupt before native evidence (unproven); adding manual traceback concatenation (logging.Formatter already preserves it); obligatory extra user approval (task authorizes this bounded fix); speculative Qt dispatcher (only add if native thread evidence requires it); redesigning the four-person allocation (already fixed). DEBUG→PrintLog is a reasonable optional refinement but not required by screenshot intent; either tested native DEBUG sink must preserve its configured level. Generic `QCoreApplication` is insufficient for actual GUI fonts; use offscreen QApplication. The review's expanded acronym labels do not replace TCCode dossier contracts.

## Native diagnosis update

Regular native copy open succeeded with 163 objects/64 links and unchanged bytes. Exact installed 1.1.3 recovery checker returned false with a different CWD and true with the model directory CWD, proving basename-based false corruption. No model repair is needed for this reproduced warning; signed FreeCAD core remains unmodified. The separate generic read error was not reproduced, and full isValid geometry checks remain NOT_COMPLETED_CPU_BOUND. See TD for exact boundaries.
