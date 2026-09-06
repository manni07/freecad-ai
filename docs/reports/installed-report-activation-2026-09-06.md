# FreeCAD report correction: verified live activation

2026-09-06. **LIVE_ACTIVATION_PASS** for the explicitly approved targeted restart into weekly-2026.09.02, FreeCAD26.3.0, source `c68c452275ec188f35c02f6b30aba880b3783cf1`. The corrected addon is now loaded in the running application. This report supersedes the earlier disk-only/activation-HOLD status; earlier dossiers remain historical evidence.

## Approval and rule provenance

The user explicitly approved the proposed restart with the tested weekly candidate after verified backups. The earlier rule was supplied in the user's message headed “AGENTS.md instructions”:

> Never reboot or restart a coomputer or server without my confirmation!

It was not read from a filesystem AGENTS.md. Fresh checks found no applicable file in the parent/worktree ancestor chains or relevant docs/scripts/freecad_ai subtrees. The user's explicit yes satisfied this confirmation requirement for the agreed target. No second generic confirmation was needed; local Allow AI Python remained OFF throughout the new session.

## Backup and restoration

All five open documents were saved to distinct backup files, then reopened independently in the tested candidate before the existing process was stopped. CRC, XML, source/copy hashes, native GUI documents, object/link counts, absence of Invalid states/external links and all five saved/native camera-framing comparisons passed. Counts were163/163/0/163/163 objects and64/64/0/64/64 links. The empty document was retained.

The actual structured save operation temporarily repointed FileName to the backup paths and marked all five documents modified. It was not identity-preserving by itself. The startup bootstrap restored the recorded Name, Label, original FileName, Modified flags, active document and object counts in memory: two modified and three unmodified, matching the pre-backup state. Original files on disk were not overwritten; original and backup hashes remained unchanged during activation. Undo history is not preserved by an application restart.

## Startup and acceptance

After backup validation the supervisor stopped the identified old FreeCAD process. The first candidate startup failed before document restoration or MCP startup because its built-in App module has no `__file__`. The supervisor closed only that failed owned process and corrected the guard to use the native home-path API. The next launch passed and remains running; this was a diagnosed startup failure, not an unreported retry.

| Boundary | Observed result |
|---|---|
| Actual runtime | FreeCAD26.3.0, build20260902, exact tested source revision |
| Addon source |15 source files verified;13 actual imported module paths/hashes matched |
| Documents | All five recorded identities, active state, counts and Modified flags restored |
| Authentication | Unauthenticated request401; authenticated discovery/read succeeded;55 tools with complete schema parity; token unchanged |
| MCP/UI | Toolbar checked, chat visible, normal INFO color and actual10pt `.AppleSystemUIFont` fonts |
| Original screenshot messages | Three normal MCP startup INFO lines present; no original Sans, read-error or corruption warnings |
| Execution policy | Local AI Python access OFF; optimized preflight ON |
| Viewport |23,690 changed pixels confined to navigation-cube bounds `[1003,13,1266,276]`; zero changed pixels outside that overlay; supervisor visually confirmed the same wall position/eight rows |

Final supervisor checks also passed deep strict signature verification for both actual application bundles, confirmed exactly one native process owning port3000, and repeated the read-only document inventory with all five original states intact.

The viewport images are not byte-identical. The model pixels outside the navigation overlay are identical, and all five native camera-framing comparisons passed. This is the supported visual claim.

## Continuing this installation

The active weekly process uses the reviewed explicit bootstrap recipe and a private profile with the integrated `<user-checkout>` addon. The stable signed application remains available. The generic starter still defaults to the stable application; desktop/default-app associations were not changed. Do not assume an ordinary generic launch reproduces this weekly session. Retain the private activation plan, profile and protected backups for the next reviewed launch.

Private evidence is under `<worktree>/.integration-evidence/activation-20260906/`: `activation-result.json`, `activation-acceptance.json`, `mcp-after-start.json`, `viewport-comparison.json`, the backup manifest and activation plan. Independent backup validation is under the private `native/saved-backup-validation-…/` directory. These files contain private paths and are not publication artifacts.

Additional same-CWD/decoy/Unicode/relative recovery variants, exhaustive Shape.isValid and the full candidate unit/integration suite remain NOT RUN. Historical live recovery-cache metadata drift is not repaired or erased by this activation; the candidate uses a fresh cache. The observed recovery-route errors were reproduced in1.1.3 and absent with the same copied project in the tested candidate.

[Current handoff](../sessions/STP_installed_report_fix_2026-09-06.md) · [HTML manual](../manuals/installed-report-fix-2026-09-06.html) · [Earlier test evidence](../tests/TD_installed_report_fix_2026-09-06.md). Publication is tracked in the successor pull request; this report records runtime evidence.
