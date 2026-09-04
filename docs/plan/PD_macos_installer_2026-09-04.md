# Planning Document: macOS Installer

## Success criteria

The repository gains a safe, simple macOS installer that supports link and copy installations, deterministic target discovery, read-only preview/check modes, explicit reversible replacement, spaces in paths, Apple Bash 3.2, and clear documentation. Automated tests must be isolated and complete; real FreeCAD validation must not be claimed while FreeCAD is absent.

## Quick-win-first phases

| Phase | Work | Gate |
|---|---|---|
| 0 | Isolated worktree, baseline, ARD/TRD/ID/PD | Clean base; baseline exact; C1–C5 >95%. |
| 1 | TD and behavior tests only | Expected RED caused by missing installer; no skips. |
| 2 | Parsing, platform/source checks, discovery, dry-run/check | Focused slice green; no mutation cases proven. |
| 3 | Staged link/copy installation | Mode and space-path tests green. |
| 4 | Conflict, backup, restore, idempotence | Destructive-edge tests green; independent review. |
| 5 | README, HTML manual, workflow, TCCode completion artifacts | Links and structure verified. |
| 6 | Full verification, real Darwin dry-run, commit/push/PR | All reported gates exact; no merge. |

## Execution ownership

The root agent integrates and implements. A dedicated orchestrator produced dependency ordering and gate scores. An architecture/security worker reviews path and replacement safety. A test/documentation worker owns tests and test/user artifacts. Workers may not edit the installer concurrently with root.

## Checkpoints

After each phase, record what changed, exact verification, and remaining gates. Stop on unclear target selection, unsafe filesystem scope, unexpected primary-worktree changes, failure to restore a backup, any skipped test, or a required restart. A live FreeCAD start is never authorized by this plan.

## Verification commands

```bash
/bin/bash -n scripts/install_macos.sh
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen <python> -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_install_macos.py -rs
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen <python> -m pytest -q -p no:cacheprovider -o addopts='' tests/unit -rs
<python> -m ruff check freecad_ai tests/unit --select E9,F63,F7,F82
git diff --check
scripts/install_macos.sh --dry-run
```

`<python>` is the already validated project test environment. The dry-run command is executed on the real Darwin host only after automated tests pass, with before/after evidence for the resolved target.

## Review record

Agent Workflow v4 selected staged parallel execution because tests/documentation and design review are separable, while filesystem publication and replacement must remain serial. The five readiness scores are 99%, 98%, 98%, 97%, and 97% (aggregate 97.8%).

The external `agy` dossier review is attempted as required by TCCode. If its headless execution cannot return, that limitation is reported explicitly and the independent four-agent review plus executable gates remain authoritative; no missing review is silently called passed.

## Execution result

The first headless `agy` attempt was permission-blocked and reported as such. The architecture worker later completed a corrected read-only `agy` review and independently issued three successive security vetoes. Each veto became new failing tests before production changes: root/system path and lock boundaries, signal rollback and BSD publication races, canonical symlink aliases, exclusive link/copy claims, and backup-independent partial-copy cleanup. The fourth review found no scoped code blocker and scored the implementation 97.4%.

Final automated evidence is `56 passed in 14.70s` for the installer suite and `1612 passed in 149.15s` for all unit tests, both with zero skips. Live FreeCAD loading remains `HOLD`; it was not started or represented as tested.
