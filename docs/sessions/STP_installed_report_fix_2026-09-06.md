# Session transfer: installed report fix and live activation

2026-09-06; TCCode + Agent Workflow v4, thorough, production, four total agents. **LIVE_ACTIVATION_PASS**: the explicitly approved targeted restart after verified backups is complete. Weekly-2026.09.02 FreeCAD26.3.0 (`c68c452275ec188f35c02f6b30aba880b3783cf1`) is running with the corrected addon. The [activation report](../reports/installed-report-activation-2026-09-06.md) is the current authority/status record; earlier disk-only workflow/dossier HOLD entries describe the pre-approval stage.

## Verified live outcome

Five backup files passed independent native reopen, CRC/XML/hash/object/link/GUI/state checks and five camera-framing comparisons before shutdown. The actual save operation temporarily repointed FileName and set all documents modified; the bootstrap restored exact recorded Name/Label/original FileName/Modified/active/count values. Final state matches the original two-modified/three-unmodified split. Original files were not overwritten, and source/backup hashes passed. Undo history is not restored by restart.

The first candidate launch failed before restoration/MCP because built-in App has no `__file__`; its owned process was closed, the guard changed to native home-path verification, and the next launch passed. Actual acceptance verified15 source files/13 loaded modules,55 authenticated tools with full schema parity, unauthenticated401, unchanged token, toolbar checked/chat visible, normal INFO and actual10pt default fonts. Three normal MCP startup lines are present; no original Sans/read/corruption warning. Local AI Python remains OFF; optimized preflight is ON.

Viewport comparison found23,690 changed pixels only in the navigation-cube overlay; zero changed model pixels outside it. Supervisor visually confirmed the same wall position/eight rows. The images are not byte-identical; all five camera-framing checks passed.

## Authority and rule source

The restart rule was the user's pasted “AGENTS.md instructions”: “Never reboot or restart a coomputer or server without my confirmation!” No applicable filesystem AGENTS.md was found in the checked parent/worktree ancestor chains or relevant subtrees. The user's subsequent explicit yes approved this concrete restart/candidate activation after backups. That permission must not be reclassified as still missing. Local Python consent is a separate application boundary and was not enabled.

## Safe continuation

1. Refresh current process/listener/document state before another operation; this report records the observed successful activation, not a perpetual health guarantee.
2. Keep the dirty `<user-checkout>` and its local preflight/Future work. The previous ten-file integration preserved337 unrelated baseline files; do not replace the checkout from a clean public branch.
3. The active weekly uses the private explicit profile/bootstrap recipe. The generic starter still defaults to the stable application, and default-app associations were not changed. Preserve both the tested weekly/profile and stable rollback application.
4. Retain all five protected backups, original files and old recovery data. Existing save_document changes FileName; any future save/backup must account for that behavior and verify identity/state. Do not replay this completed save/start sequence blindly.
5. Use `<worktree>/.integration-evidence/activation-20260906/` for exact private activation plan, manifest, result, acceptance, authenticated-read and viewport evidence. Private backup-validator evidence is under `.integration-evidence/native/saved-backup-validation-…/`. Never publish model paths, profiles or token material.

## Earlier verification and remaining limits

Combined unit1992 passed plus3 subtests182.39 s, zero fail/error/skip; selected native preflight10 passed24.91 s; installed-target63 passed9.77 s. Candidate compatibility passed addon GUI/13 source hashes and10 selected native preflight cases13.45 s. Eight genuine recovery-GUI cases proved the legacy error and candidate positive/status/negative/open behavior. These retain their original scope, not full candidate-suite coverage.

Same-CWD/decoy/Unicode/relative recovery variants, exhaustive geometry and full candidate unit/integration coverage remain NOT RUN. Historical cache drift changed two records before diagnostic GUIs; the writer was unobserved. This activation uses a fresh candidate cache and does not claim a repair or deletion of old recovery metadata.

Prior verification publication: commit `a5752dc` and [PR #4](https://github.com/manni07/freecad-ai/pull/4). Publication of the activation documentation is tracked in the successor pull request; this handoff records runtime evidence.

[Activation report](../reports/installed-report-activation-2026-09-06.md) · [Manual](../manuals/installed-report-fix-2026-09-06.html) · [Earlier TD](../tests/TD_installed_report_fix_2026-09-06.md) · [Earlier plan](../plan/PD_installed_report_fix_2026-09-06.md)
