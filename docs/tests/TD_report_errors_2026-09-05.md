# Test dossier: report-view errors

Prepared before code; every result initially NOT RUN. The root selects the already validated interpreter and records it with results. No paid provider calls, live GUI writes, restarts or original model writes.

## Phase A functional and regression cases

| ID | Scenario / intent | Expected |
|---|---|---|
| A01 | INFO startup should not alarm the user | PrintMessage once, no PrintError |
| A02 | DEBUG retained according to configured level | expected filtering, no error classification |
| A03 | WARNING remains actionable | PrintWarning once |
| A04 | ERROR remains visible | PrintError once |
| A05 | CRITICAL remains visible | PrintError once |
| A06 | Exception report preserves debugging context | traceback and message visible |
| A07 | Repeated GUI/controller setup | one handler, one output per record |
| A08 | Existing root/other-addon handlers | identities and configuration preserved |
| A09 | Script and toolbar startup routes | handler active before startup record |
| A10 | Headless/stdio context | fallback remains valid and protocol stdout clean |
| A11 | Worker-thread emission | no direct widget mutation, correct console method |
| A12 | Local handler formatting failure | does not recurse or hide diagnostics |
| A13 | Chat font | available/default family, 10 point |
| A14 | Input font | available/default family, 10 point |
| A15 | Local probe font/image | available/default family, 32 point, bold, valid PNG |
| A16 | No QApplication local probe | existing fallback retained |
| A17 | Source unavailable-family regression | addon no longer constructs Sans |
| A18 | Burst logging performance | bounded per-record work, time/count recorded |

Command after worker adds tests: `<validated-python> -m pytest tests/unit/test_console_logging.py -q` (worker records actual filename if different). Run existing entrypoint/controller/vision/UI slices and whole unit suite: `<validated-python> -m pytest tests/unit -q`. Pass requires no unexpected failures; skipped tests explicitly enumerated, never silently counted as passed.

## Phase B copied-document/native cases

| ID | Check | Expected |
|---|---|---|
| B01 | Original file SHA before | matches recorded baseline |
| B02 | ZIP CRC | no bad entry |
| B03 | Duplicate/case-sensitive entries | deterministic inventory recorded |
| B04 | Document.xml parse | syntactically valid or exact defect |
| B05 | GuiDocument.xml parse | syntactically valid or exact defect |
| B06 | Referenced archive payloads | missing references identified |
| B07 | Native reopen of isolated copy | success or exact reproducible exception |
| B08 | Objects loaded | count and expected structure recorded |
| B09 | Shape validity on native load | invalid/null states recorded |
| B10 | Original SHA after | identical to B01 |
| B11 | Isolated profile/live-session preservation | only fixture paths used |
| B12 | Conditional repaired copy roundtrip | only after specific repair approval; otherwise NOT APPLICABLE |

Exact native command is recorded by root after discovering the installed binary and supported profile flags; inventing FreeCAD CLI flags would be unsafe. Generic archive check: `python3 -m zipfile -t <copied-model.FCStd>`; native validity is a separate gate.

## Phase C integration and assurance

C01 full unit suite; C02 focused changed-code coverage ≥80%; C03 critical lint; C04 independent security/code review; C05 changed files scope review; C06 model hash preservation; C07 read-only live MCP discovery/document operation if available; C08 isolated native log/font proof; C09 documentation links/structure; C10 rollback by branch/code separation; C11 classify all remaining items PASS/HOLD/NOT APPLICABLE; C12 final staged diff review if publication proceeds.

Native report-view activation in the existing user GUI is HOLD unless safely observable without mutation; unit tests do not establish live visual correction. Native isolated Qt/FreeCAD tests are the suitable desktop alternative to browser E2E. No database/schema tests apply because this task has no datastore change. Performance: capture logging burst elapsed time and font construction/probe behavior locally; no benchmark claim without measurements.

## Test-strategy simulation

C1 99, C2 98, C3 97, C4 99, C5 98 (>95 each): cases preserve user-visible severity and data, cover both startup paths and fallback, include native proof separately, and retain reproducible blockers. Mock-only results cannot close native gates.

[ID](../dossiers/ID_report_errors_2026-09-05.md) · [PD](../plan/PD_report_errors_2026-09-05.md)

## External read-only review (agy)

`agy --help` succeeded. First `agy --print --mode plan ... --prompt <text>` returned 2 because this CLI treated `--mode` as the print prompt. Corrected subprocess argv used `agy --mode plan --print-timeout 1m0s --print=<self-contained-text>` and returned 0. The review explicitly used supplied text only, no files/tools/tests; no session ID was exposed. It judged READY FOR EXECUTION, not completed verification.

Accepted: namespace-local non-propagating logging, idempotence, unrelated handler preservation, traceback tests, stdio separation, worker-thread/native proof, isolated font rendering, copy-only model checks without recompute. Rejected: calling the model corrupt before native evidence (unproven); adding manual traceback concatenation (logging.Formatter already preserves it); obligatory extra user approval (task authorizes this bounded fix); speculative Qt dispatcher (only add if native thread evidence requires it); redesigning the four-person allocation (already fixed). DEBUG→PrintLog is a reasonable optional refinement but not required by screenshot intent; either tested native DEBUG sink must preserve its configured level. Generic `QCoreApplication` is insufficient for actual GUI fonts; use offscreen QApplication. The review's expanded acronym labels do not replace TCCode dossier contracts.

## Final results on the scoped publication tree

Code commit: `b785feb8748327c4b5dc439f8500320f004b102f`; base: `5abeb8879d093a7c0853ecd34fd8aa8f80d15280`. Unpublished predecessor `6e51894` was excluded. **1642 passed in 177.58 s, zero skipped, exit 0.** All nine task code/test files are byte-identical before/after isolation, preserving the relevant native proof. The three-test count reduction versus the initial 1645 collected tests comes from excluding that predecessor, not skipping tests.

```sh
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen "<FreeCAD.app>/Contents/Resources/bin/python" -c 'import sys; sys.path.append("<python-test-site-packages>"); import pytest; raise SystemExit(pytest.main(["-q", "-p", "no:cacheprovider", "--tb=short", "tests/unit"]))'
```

Replace placeholders with verified local values; exact paths/model hash remain only in private `.report-errors-evidence/orchestrator-private-path-mapping.json`.

| Boundary | Result | Evidence |
|---|---|---|
| A01–A12 logging/routes/stdio | PASS | standard severities, traceback, idempotence, retained root/explicit handlers and levels, both launcher forms, Initialize/direct command, thread and import-inert tests |
| A13–A17 fonts/probe | PASS | actual widgets and 128×64 PNG in fresh Qt; old source RED under identical installed-font fixture; actual native GUI font proof below |
| A18 burst | PASS_SCOPED | 10,000 INFO records → 10,000 fake-console writes in 0.119830 s; no native-throughput claim |
| B01–B08/B10–B11 archive/open/preservation | PASS | CRC/XML, native 163 objects/64 links, state/link/bounds/volume inventory, immutable input and isolated profile |
| B09 full Shape.isValid | NOT_COMPLETED_CPU_BOUND | 120 s timeout; later owned diagnostic terminated after root review; no full geometry validity claim |
| B12 repaired-copy roundtrip | NOT APPLICABLE | no concrete file defect requiring rewrite; no replacement model generated |
| C01–C06/C08–C11 code/native/docs/preservation | PASS_SCOPED | complete unit suite, helper trace, critical lint, independent review, exact scope, native GUI, docs checks; live activation remains HOLD |
| C07 existing live MCP read | PASS_READ_ONLY | three documents returned; active document163 objects and modified state retained; no live writes |
| C12 final publication review | ROOT-OWNED | code commit scope verified; documentation commit/PR/merge occurs after this dossier freeze |

## Regression history retained

Focused development-tree command used the bundled Python with `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH=<python-test-site-packages>` and `-m pytest tests/unit/test_console_logging.py tests/unit/test_ui_fonts.py tests/unit/test_initgui_commands.py tests/unit/test_vision_routing.py tests/unit/test_mcp_gui_server.py -q --tb=short`: **144 passed in 7.84 s**, no skips.

Initial full development-tree run: **2 failed, 1643 passed in 183.38 s**, zero skips. Both failures were old HTTP-launcher test doubles missing native `FreeCAD.Console`. They were corrected in `test_mcp_sse_transport.py`, including logger state restoration, without weakening production behavior. Corrected SSE/console/InitGui slice: **53 passed in 1.41 s**, zero skips. The final full result above supersedes this failed regression as the gate; the failure remains documented.

Old source under the corrected font fixture: chat fails on `Sans`; probe reproduces missing Sans warning (141 ms). Offscreen `systemFont(GeneralFont)` can itself request absent `Sans Serif`; fixture therefore uses an actually installed QFontDatabase family. Production inherits the application font; no warning filter was added.

## Coverage, lint and independent review

`coverage` package unavailable (`No module named coverage`); stdlib trace of 15 console tests (all passed in 1.90 s) hit all 26 real executable helper lines. Raw trace includes synthetic line0:26/27 (96.3%). This is helper execution coverage, not full-project or branch coverage. New-file py_compile and diff check passed.

Ruff CLI 0.15.6: `ruff check freecad_ai tests/unit --select E9,F63,F7,F82` PASS. Bundled `python -m ruff` was unavailable; the detected CLI completed the critical-rule check. No full-rule lint claim.

Independent final static review: PASS_NO_CODE_BLOCKERS for all nine code/test files at the scoped commit. Existing controller/allowed-host assertions remain intact. No private CAD, screenshots, evidence, config or secrets in code commit. Root verified277 parent baseline files and original/backup model hashes unchanged after rebase.

## Real native GUI

Isolated FreeCAD GUI with separate user parameters/data/cache and no models/server: old stderr INFO `#ff0000`; native PrintMessage control and corrected INFO/worker INFO `#102030`; warning `#987600`; error `#ff0000`. Repeat setup emits one record. Application and both actual ChatDockWidget fonts `.AppleSystemUIFont`; probe1116bytes; addon Qt messages empty. Normal close exit0. Existing user's GUI is untouched; activation HOLD. Private evidence `native-supervisor/gui-result.json` and `gui-exit.json` under `.report-errors-evidence/`.

## Native model and recovery checker

FreeCAD1.1.3 Git `145529fe741292ff0b3977a01195bf0247425794`: standard copied-model open0.267017s,163objects64links, both XML Qt parsePASS, input unchanged, exit0; complete inventory19.089422s. No save/recompute. Generic `Error reading from file` not reproduced; full Shape.isValid remains NOT_COMPLETED_CPU_BOUND.

Exact installed private C++ recovery checker, one version-specific FFI call per isolated child: same absolute copy/hash, different CWD/basename absent → false; same CWD/basename present → true; both exit0 and unchanged. This causally proves basename-based false corruption, not a supported repair API. Upstream fix: https://github.com/FreeCAD/FreeCAD/commit/1d70f987abbb429e5bcd1411fe067ac43a54785f . Signed installed core remains unpatched. Native startup also reports missing optional3DconnexionNavlib; no entirely-warning-free-FreeCAD claim.

Private local evidence: `recovery_review/native-readonly-result.json`, `validator-same.json`, `validator-different.json`, `code-review.json`, `preservation-review.json` under `.report-errors-evidence/`. Private models/evidence remain excluded from publication.
