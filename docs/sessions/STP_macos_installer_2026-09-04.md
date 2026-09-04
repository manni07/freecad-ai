# Session Transfer Protocol: macOS Installer — 2026-09-04

## Immutable resume coordinates

- Repository: `/Volumes/ExtremePro/projects/freecad-ai`
- Worktree: `/Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-183200-macos-installer`
- Branch: `agent-workflow/20260904-183200-macos-installer`
- Base commit: `04fc3ba94d7882684369a9cd2b8a4999a39811c9`
- Pull request: `https://github.com/manni07/freecad-ai/pull/2`
- Correction parent: `207329a8bec1dfad862ad7e8387d5577f0fc7e14`.
  The correction commit cannot embed its own hash; resolve the current PR head
  with `git rev-parse HEAD` and compare it with the remote before resuming.
- Installer: `scripts/install_macos.sh`
- Installer SHA-256 at this checkpoint: `54aba9b1e88c0c120b3698eb6c34c3cb07dd2b80e2166a0215a7ad5487da6eb6`
- Test dossier: `docs/tests/TD_macos_installer_2026-09-04.md`
- Open items: `docs/openitem/macos-installer-open-items-2026-09-04.md`

Do not resume in the primary checkout, and do not reset, clean, stash,
overwrite, or broadly format this worktree. Verify the current branch and HEAD
from Git/PR evidence when resuming. Existing README and CI changes belong to
the root workflow and are not incidental cleanup targets.

## Verified checkpoint

- Final post-PR focused installer command: **69 passed in 18.30 seconds**, zero
  skips. Prior root and independent runs passed the earlier 56-case suite.
- Exact CI-equivalent security slice: **375 passed in 46.43 seconds**, zero
  skips. The corrected MCP admission test also passed **20/20** repetitions.
- Final post-PR complete unit command: **1625 passed in 150.79 seconds**, zero
  skips; the prior committed tree passed 1,612 tests in 145.05 seconds.
- GitHub-hosted CI is **HOLD at this checkpoint**: the two failed runs belong
  to correction parent `207329a8bec1dfad862ad7e8387d5577f0fc7e14`.
  Commit and push the correction, then require all checks on the new PR head
  to pass before changing this integration gate.
- Real Darwin `--dry-run`: rc 0, resolved generic destination
  `/Users/turgay/Library/Application Support/FreeCAD/Mod/freecad-ai`, with the
  real profile `ABSENT` before and after. Real `--check`: expected rc 1 for the
  absent destination, also `ABSENT` before and after.
- Tests isolate `HOME`, `TMPDIR`, and `PATH`; their fixture-owned `uname`
  supplies Darwin/non-Darwin results. No real FreeCAD profile is a test target.
- Installer behavior covers early Darwin/root gates, physical source and
  canonical user-target validation, deterministic selection, per-target lock,
  validated staging, exclusive direct `ln`/`mkdir` claims, final copy `rsync`,
  idempotence, backups, race/signal/partial cleanup, and read-only modes.
- The first time-bounded headless `agy` attempt was permission-blocked. Later
  independent review incorporated real findings, vetoed the first PR-CI
  correction after reproducing macOS `//System`, and passed the final scoped
  normalization at **98.4%** (C1 99, C2 99, C3 99, C4 98, C5 97).
- No FreeCAD application or CLI is installed on the validation host. Live
  workbench loading remains `HOLD`, regardless of green unit evidence.

## Safe read-only resume

```bash
cd /Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-183200-macos-installer
test "$(git branch --show-current)" = agent-workflow/20260904-183200-macos-installer
test "$(git merge-base HEAD 04fc3ba94d7882684369a9cd2b8a4999a39811c9)" = 04fc3ba94d7882684369a9cd2b8a4999a39811c9
test "$(shasum -a 256 scripts/install_macos.sh | awk '{print $1}')" = 54aba9b1e88c0c120b3698eb6c34c3cb07dd2b80e2166a0215a7ad5487da6eb6
git status --short
git diff --check
```

This worktree has no local `.venv`. The verified interpreter is:

```text
/Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation/.venv/bin/python
```

Re-run the deterministic gates without installation or FreeCAD startup:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen /Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation/.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_install_macos.py -rs
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen /Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation/.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit -rs
/bin/bash -n scripts/install_macos.sh
/Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation/.venv/bin/ruff check tests/unit/test_install_macos.py --select E9,F63,F7,F82
git diff --check
```

## Mutation and runtime gates

The automated tests use temporary profiles; they do not authorize a real
installation. The authorized real-host read-only gate resolved the generic
destination above without creating it, and check failed as expected for
absence without mutation. To repeat it, obtain fresh confirmation for the
intended checkout and inspect the resolved target:

```bash
/bin/bash scripts/install_macos.sh --dry-run
```

`--dry-run` must produce expected source/destination output and no filesystem
change. A real install, replacement, backup restoration, FreeCAD start/restart,
merge, or release requires its own explicit authority. The current workflow
has authority only for its focused commit, push, and pull request.

Live acceptance remains blocked until a supported FreeCAD process can prove:

1. the intended version-specific workbench is discovered;
2. imports complete without Report-view errors;
3. FreeCAD AI appears in the workbench selector;
4. a disposable document can complete a non-destructive smoke test;
5. rollback to the exact preserved backup works if acceptance fails.

Unavailable FreeCAD is a `HOLD`, never a pass and never a reason to install or
restart another process implicitly.

## Stop rules

Stop and report rather than improvising if:

1. branch, base/HEAD, worktree, or installer hash differs;
2. any selected test fails, errors, skips, or times out;
3. source or destination output is unexpected;
4. more than one versioned `Mod` directory exists without explicit choice;
5. the destination is a conflict and `--replace` was not deliberately approved;
6. publication or automatic restoration fails;
7. a real profile, FreeCAD process, provider secret, network, system directory,
   privilege boundary, or package manager would be touched unexpectedly;
8. live FreeCAD or external review evidence is unavailable but requested as a
   release claim.

## Authority state

Documentation and deterministic testing are complete for this checkpoint.
No authority is carried forward for filesystem installation, backup deletion,
process lifecycle, merge, or release. The worktree remains available after the
authorized pull request for review and follow-up. Resume with identity checks
and request a new bounded scope for any additional action.
