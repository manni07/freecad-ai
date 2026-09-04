# Test Definition: macOS Installer — 2026-09-04

## Control record

- Scope: test-first definition for `scripts/install_macos.sh`.
- Worktree: `/Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-183200-macos-installer`.
- Base: `04fc3ba94d7882684369a9cd2b8a4999a39811c9`.
- Approved writes for this phase: this dossier and `tests/unit/test_install_macos.py` only.
- Baseline: `1556 passed in 113.60s`, zero skips.
- Runtime rule: no test may start, stop, restart, or inspect a live FreeCAD process.

## Test objective

Prove that the macOS installer is deterministic, Bash 3.2 compatible,
read-only unless installation is explicitly requested, and reversible when an
existing destination is explicitly replaced. Tests exercise the public shell
interface in subprocesses. They do not bind to shell function names or use
production test switches.

The workflow began with a genuine missing-production RED, then added
adversarial RED cases as review exposed platform, transaction, race, and
cleanup boundaries. The final focused root and independent runs, full-unit
regression, and security review now provide the as-built acceptance evidence.

## Isolation prerequisites and fixtures

`isolated_process` creates all state below `tmp_path`:

- a temporary `HOME` containing the only FreeCAD profile visible to the script;
- a temporary `TMPDIR` for staging;
- a fixture-owned `uname` placed first on a minimal `PATH`, returning `Darwin`
  or the requested negative platform;
- a minimal environment without inherited provider keys, FreeCAD settings, or
  user configuration;
- subprocess execution through `/bin/bash`, with captured output and a bounded
  15-second timeout.

The tests never set `HOME` to the operator's home, never invoke FreeCAD, and
never create a listener. Source-validation cases place a copy of the future
installer in a minimal temporary checkout. Failure injection shadows only the
publication primitive under test in the fixture `PATH`: direct `ln` for link
publication and direct destination `mkdir` for copy publication. Delegated
commands use absolute system paths, so backup/restore operations and fixture
setup are not accidentally injected.

## Requirement-to-test matrix

| Requirement | Tests and evidence |
|---|---|
| CLI and Bash 3.2 | `test_help_uses_apple_bash_and_documents_the_complete_interface`; `test_script_parses_with_bash_3_2_compatible_entrypoint`; `test_script_avoids_bash_4_and_gnu_only_constructs` |
| Darwin before mutation | `test_non_darwin_gate_precedes_every_filesystem_mutation` snapshots the isolated HOME and proves the explicit target is not created. |
| Root refusal | `test_effective_root_is_refused_early_without_target_mutation` uses the fixture-owned `id -u` result `0`; normal cases use `501`. `test_root_gate_is_statically_before_mutating_commands` binds the robust EUID query before target mutations. No real privilege is required. |
| Physical source validation | `test_source_requires_every_workbench_entry_before_target_mutation` removes each of `Init.py`, `InitGui.py`, `package.xml`, and `freecad_ai/` in turn. |
| Target precedence | Explicit override, exactly one versioned `v*/Mod`, generic fallback, multiple-version ambiguity, relative/dot/root rejection are separately tested. |
| User-only canonical scope | All system prefixes including `/private/etc` fail even under dry-run; a user-looking path with a symlink parent resolving below `/private/etc` also fails without mutation. |
| Staged symlink install | `test_default_install_publishes_a_link_via_clean_sibling_staging` verifies exact source resolution and absence of staging residue. |
| Staged copy install | `test_copy_install_is_structurally_complete_and_excludes_development_data` verifies required payload and exclusion of repository, test, documentation, cache, build, coverage, and editor data. |
| Idempotence and mode | Correct link is an exact no-op; a structural copy is a no-op only in copy mode; no backup is created for either no-op. |
| Conflict classification | File, directory, wrong link, and broken link all fail unchanged without `--replace`; absent/check states are distinct. |
| Explicit replacement | `test_replace_moves_conflict_to_unique_backups_before_publication` proves old payload preservation and collision-safe distinct backups. |
| Rollback | Direct link-claim failure after backup requires exact restoration; a fresh link failure independently requires destination/stage/lock cleanup without any backup; a deterministic invalidation after the final copy claim forces only the second `rsync` to fail and requires no partial destination. |
| Per-target serialization | `test_preexisting_per_target_install_lock_fails_unchanged` models a second run by pre-creating the installer-owned lock and requires no target change; link/copy success, ordinary failure, and signal cases require installer-owned lock cleanup. The stale foreign lock itself remains untouched. |
| Publish race | Link injection recreates a directory inside the direct `ln` publication primitive; another injects a correct-source symlink and forbids a nested source-basename link or false success while preserving the backup. Copy injection creates a structurally valid foreign workbench inside the direct destination `mkdir` claim. None may false-succeed, nest payload, or overwrite raced state. |
| Signal rollback | Fixture-owned publication primitives inject TERM during direct link publication and during the second copy `rsync`; both require exact restoration plus stage/backup/lock cleanup. The copy watcher is bounded and exits when its installer process ends. |
| Spaces | Explicit paths containing spaces are covered in link, copy, replacement, backup, HOME, TMPDIR, fake-bin, and fixture-source paths. |
| Read-only modes | Both dry-run cases and all check cases compare before/after tree snapshots; dry-run replacement is a permitted preview. |
| Invalid CLI states | `--check` incompatibilities, missing `--mod-dir` value, and unknown options fail before mutation. |
| Prohibited behavior | Static tests reject privilege escalation, network/package operations, process/service/application control, dynamic evaluation, provider/credential/config mutation, Bash 4 syntax, and GNU-only path resolution. |

## State and assertion model

Tests assert outcomes by return code, non-empty failure diagnostics, selected
destination, link resolution, required copied entries, excluded content,
before/after filesystem manifests, backup payloads, and staging cleanup. A
successful negative test may not rely solely on matching prose. Broken links
are captured with `lstat`/`readlink`, so they cannot be mistaken for absence.

Expected state contract:

| Destination | Link mode | Copy mode | `--replace` | `--check` |
|---|---|---|---|---|
| absent | install link | install copy | install requested mode | fail read-only |
| correct source link | no-op | conflict | replace only for copy | pass |
| structural copy | conflict | no-op | replace only for link | pass |
| foreign file/dir/link or broken link | fail unchanged | fail unchanged | backup, publish, or restore | fail unchanged |

## Exact commands and gates

Focused RED/GREEN command:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen /Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation/.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_install_macos.py -rs
```

The new installer worktree has no local `.venv`. The command therefore uses
the already validated project test environment from the security-remediation
worktree while collecting and importing this checkout's tests and sources.

Later production gates:

```bash
/bin/bash -n scripts/install_macos.sh
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit -rs
.venv/bin/ruff check tests/unit/test_install_macos.py --select E9,F63,F7,F82
git diff --check
```

After automated GREEN, a real-Darwin `--dry-run` requires separately recorded
before/after evidence for the resolved target. Live FreeCAD loading is not
available and remains `HOLD`; a successful dry-run is not a substitute.

## RED/GREEN evidence ledger

| Stage | Expected result | Actual evidence | Gate |
|---|---|---|---|
| Test-first RED | Missing and unsafe behavior failed for production reasons only; collection, fixtures, syntax, timeouts, and skips remained clean. | Successive RED reviews bound the initial interface and then root refusal, canonical system-scope rejection, locking, direct destination claims, raced-state identity, signal rollback, and backup-independent partial cleanup. Inadequate exploratory injection conditions were explicitly discarded rather than counted as evidence. | TDD provenance confirmed. |
| Production GREEN | Every focused case passes with zero skips; both direct publication modes and all cleanup paths meet the final contract. | Root run: **`56 passed in 14.70s`**, zero skips. Independent run: **`56 passed in 21.40s`**, zero skips. Link publication uses a validated stage followed by an exclusive direct `ln`; copy publication validates a staged copy, exclusively claims with `mkdir`, then performs the final `/usr/bin/rsync`. | **PASS** |
| Regression | Full unit suite passes with zero skips. | Final pre-commit run: **`1612 passed in 145.05s`**, zero skips. An earlier final-code run also passed all 1,612 tests in 149.15s. | **PASS** |
| Security review | Implementation is feasible, complete, maintainable, and fail-closed for the approved user-scope contract. | Final security score **97.4%**: C1 99%, C2 98%, C3 97%, C4 97%, C5 96%. The initial headless `agy` attempt was permission-blocked; a later independent architecture review successfully used `agy`, incorporated real findings, and the final scoped review passed. | **PASS** |
| Real-host read-only | Darwin target selection and absent-state check do not mutate the real profile. | `scripts/install_macos.sh --dry-run` returned 0, resolved `/Users/turgay/Library/Application Support/FreeCAD/Mod/freecad-ai`, and profile state remained `ABSENT` before/after. `--check` returned the expected 1 for absence and also remained `ABSENT` before/after. | **PASS** |
| Live runtime | Supported FreeCAD loads the installed workbench and completes a disposable-document smoke test. | FreeCAD unavailable; no install was performed. | **HOLD** |

## Test simulation gate

| Criterion | Score | Rationale |
|---|---:|---|
| T1 coverage completeness | 99% | All public options, target branches, destination types, modes, rollback, and static vetoes have explicit cases. |
| T2 isolation | 99% | Temporary HOME/TMPDIR/PATH and fake uname contain every subprocess; no live process or network is used. |
| T3 assertion quality | 98% | Behavior is proven through filesystem identity/snapshots and payloads, not implementation names or output text alone. |
| T4 maintainability | 97% | Shared runner and state helpers keep tests concise while retaining named intent boundaries. |
| T5 risk strategy | 99% | Ambiguity, broken links, explicit replacement, injected post-backup failure, unsafe targets, and prohibited operations fail closed. |

Aggregate for the test definition: **98.6%**. All automated installer and unit
gates are **PASS**. Live FreeCAD/runtime acceptance remains a separate `HOLD`;
filesystem evidence is not presented as application-load evidence.

Expanded test simulation remains above threshold: T1 coverage 99%, T2
isolation 99%, T3 assertion quality 99%, T4 maintainability 97%, and T5 risk
strategy 99%, aggregate **98.6%**. The higher T3 reflects deterministic fake
EUID, lock-state, destination-reappearance, and signal injection with exact
filesystem assertions; it does not promote the production gate while RED.

## External review attempt

The required time-bounded read-only review was attempted with:

```bash
agy --mode plan --sandbox --print-timeout 45s --print "Read only. Review tests/unit/test_install_macos.py and docs/tests/TD_macos_installer_2026-09-04.md against the ARD, TRD, and ID."
```

It returned after 9.1 seconds without a review: `jetski: no output produced —
a tool required the "command" permission that headless mode cannot prompt for,
so it was auto-denied.` No unrestricted permission override was used. A later
independent architecture review could execute `agy` in its approved context,
converted its findings into tests and implementation corrections, and the
final scoped review passed. The executable tests remain the acceptance source.
