# Installed report fix: open-item register

Created before final documentation,2026-09-06. Exactly three High, three Medium and three Low entries. Severity describes consequence if mishandled, not a count of discovered vulnerabilities. Closed entries remain evidence checkpoints.

| ID | Severity | Concern | Current status | Closure / boundary |
|---|---|---|---|---|
| H1 | High | Current dirty preflight/source work must survive integration | CLOSED_DISK | root10files integrated;337unchanged+7expectedchanges+3new; fullcombined/native/installedtests passed |
| H2 | High | Two modified live documents and recovery data must remain intact | HOLD_LIVE_WRITE_UNAUTHORIZED | no model/cachewrites; identity-preserving saveCopy preparation only; save_document is not transparentbackup |
| H3 | High | Installed disk source and active process must not be conflated | HOLD_RESTART_UNAUTHORIZED | root integrated tested ten files; runtime unchanged; no restart/reload/stop until explicit confirmation |
| M1 | Medium | Native prerelease candidate fixes path bug without losing invalid/status detection | PASS_8_CASES_EXTRA_PATHS_NOT_RUN | artifact+postsignaturePASS;8genuineGUIcasesPASS;4pathvariantsNOTRUN; no installed-core replacement |
| M2 | Medium | Full combined regression/native GUI and independent review | CLOSED_ADDON | 1992+3unit;10native;13GUIhashes/exit0;63installedtarget;18guards;Ruff/rootreview |
| M3 | Medium | Recovery-route generic error now reproduced; full geometry remains incomplete | HOLD_GEOMETRY | reallegacyGUI reproduced botherrors; identicalcopycandidateA/BPASS; Shape.isValid NOT_COMPLETED; no modelrewrite |
| L1 | Low | External review and workflow documentation completeness | CLOSED_DOCS | agy plan/PPD reviews, linked dossiers/manual/STP/diary and exactstage outcomes |
| L2 | Low | Candidate/disk tests must retain reproducible private provenance | CLOSED_PRIVATE_EVIDENCE | relativehashmanifest, buildidentity, exactcommands/timings; private paths/credentials notpublished |
| L3 | Low | Task-only publication must exclude parent features/config/models | OPEN | freshpublicworktree, exactstagedlist, privacy/diff/linkchecks; root ownsGit |
