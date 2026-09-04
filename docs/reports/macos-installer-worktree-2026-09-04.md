# macOS Installer Worktree Validation Report — 2026-09-04

## Scope

- Worktree: `/Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-183200-macos-installer`
- Branch: `agent-workflow/20260904-183200-macos-installer`
- Base commit: `04fc3ba94d7882684369a9cd2b8a4999a39811c9`
- Installer SHA-256: `f04e1919959673ffd70c6c7f02d7861ba3a1d991c2c1ec21189c71738ae9099d`
- Workflow: TCCode and Agent Workflow v4, thorough, fixed team of four.

## Implemented contract

The Bash 3.2-compatible installer refuses non-Darwin and effective-root runs,
then validates a complete physical source checkout before target mutation. It
canonicalizes the selected directory and rejects macOS system prefixes,
including symlink-parent aliases. An absolute `--mod-dir` wins; otherwise
exactly one existing version-scoped `v*/Mod` is selected, ambiguity fails, and
the generic user `Mod` path is the fallback.

Each mutating run holds one per-target lock. Link and copy modes use sibling
staging and validate before publication. Link mode exclusively claims the
destination with direct `ln`; copy mode claims it with direct `mkdir` and then
uses a final `/usr/bin/rsync` from the validated stage.
Correct installations are idempotent. Files, directories, wrong/broken links,
and mode mismatches are conflicts unless `--replace` is explicit. Replacement
moves the old object to a unique timestamped backup; publication failure
attempts exact restoration. Fresh failure, raced-state, signal, partial-copy,
stage, and lock cleanup are covered. `--dry-run` and `--check` are read-only.

The installer contains no package/network/provider/config actions, does not use
`sudo`, and does not launch, stop, or restart FreeCAD or another process.

## Evidence

| Gate | Result |
|---|---|
| Focused installer suite | Root: **56 passed in 14.70s**; independent: **56 passed in 21.40s**; zero skips. |
| Complete unit suite | Final pre-commit run: **1612 passed in 145.05s**, zero skips; prior final-code run: **1612 passed in 149.15s**, zero skips. |
| Real Darwin dry-run | rc 0; generic destination `/Users/turgay/Library/Application Support/FreeCAD/Mod/freecad-ai`; real profile `ABSENT` before/after. |
| Real absent-state check | Expected rc 1; real profile `ABSENT` before/after. |
| Test isolation | Temporary HOME/TMPDIR/PATH and fixture-owned `uname`; no real profile target. |
| Test simulation | T1 99%, T2 99%, T3 98%, T4 97%, T5 99%; aggregate 98.4%. |
| Security review | **PASS, 97.4%**: C1 99%, C2 98%, C3 97%, C4 97%, C5 96%. |
| External `agy` | Initial headless attempt permission-blocked; later approved independent architecture use incorporated real findings and final scoped review passed. |
| Live FreeCAD | Unavailable; explicit `HOLD`. |

The focused suite exercises the platform/root gates before mutation, source failure
for every required path, explicit/versioned/generic/ambiguous target selection,
canonical system/symlink-parent rejection, staged link and filtered copy output,
per-target locking, exclusive direct claims, link/copy
idempotence, all conflict types including broken symlinks, unique backup names,
injected races, publication/second-copy failures, TERM and restoration, partial/
stage/lock cleanup, paths with spaces, dry-run/check snapshots, invalid options,
prohibited commands, and Bash 4/GNU-only syntax.

## Decision

Filesystem implementation and deterministic tests: **PASS**.
Real-host read-only target selection and absence checking: **PASS**, with no
profile creation or installation.

Runtime/release acceptance: **HOLD**. No supported FreeCAD executable is
available to prove discovery, import, workbench activation, or disposable-
document behavior. Green unit tests and structural `--check` must not be
represented as live FreeCAD evidence.

No installation, FreeCAD lifecycle action, merge, or release is authorized by
this report. The user separately authorized a focused commit, push, and pull
request; the worktree remains available for review.
