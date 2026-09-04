# Technical Requirements Dossier: macOS Installer

## Interface

`scripts/install_macos.sh [--copy] [--dry-run] [--check] [--replace] [--mod-dir ABSOLUTE_PATH]`

- no option: install a symbolic link;
- `--copy`: install a real directory;
- `--dry-run`: validate and print the prospective action without mutation;
- `--check`: inspect only and return success only for a correct link or structurally valid copy;
- `--replace`: allow a conflicting destination to be moved to a backup before installation;
- `--mod-dir`: override discovery with an absolute `Mod` directory;
- `--help`: print usage and exit successfully.

`--check` is incompatible with `--copy`, `--replace`, and `--dry-run`. Unknown options, missing values, relative `--mod-dir` values, and `/` as the target fail before mutation. `--dry-run --replace` is allowed so replacement can be previewed safely.

## Target algorithm

1. Gate on `uname -s` being `Darwin`.
2. Resolve the script's physical directory and its parent as source.
3. Validate `Init.py`, `InitGui.py`, `package.xml`, and `freecad_ai/`.
4. If supplied, validate and select `--mod-dir`.
5. Otherwise enumerate existing version-scoped `v*/Mod` directories under the user's FreeCAD Application Support directory.
6. Select one, fail on more than one, or use the generic `Mod` path when none exist.
7. Set destination to `<selected Mod>/freecad-ai` and print it before any requested mutation.

## State and exit contract

| State | Normal install | `--replace` | `--dry-run` | `--check` |
|---|---|---|---|---|
| absent | create | create | report create | fail |
| correct link | no-op | no-op | report no-op | pass |
| valid copy | conflict in link mode; no-op in copy mode | replace if mode differs | report | pass |
| wrong/broken link or foreign object | fail | backup then replace | report conflict/replace | fail |

All ordinary failures return `1` with a concise diagnostic. Handled `HUP`, `INT`, or `TERM` exits `130` after transaction cleanup. Help and successful create/no-op/check return `0`.

## Publication and rollback

The selected `Mod` directory is created only for a real install. A per-target `.freecad-ai.install.lock` directory is acquired atomically, then destination state is checked again. A private sibling staging directory is created with `mktemp -d`. Link mode creates and validates a staged link, then exclusively claims the final path with `ln`. Copy mode uses `/usr/bin/rsync -a` and excludes repository/development-only content (`.git`, virtual environments, caches, tests, documentation, build artifacts, and editor metadata); after staged validation, `mkdir` exclusively claims the final directory and a second `rsync` publishes its contents.

On conflict replacement, the existing destination is moved to `freecad-ai.backup.YYYYMMDD-HHMMSS.PID`, with a numeric suffix if needed. If staging or publication fails, any positively claimed partial destination is removed and the backup is moved back when the destination remains safe. If an external actor has recreated the destination, it is preserved and the original backup is retained with a visible error. Cleanup is limited to installer-owned destination, staging, and lock paths.

Root execution is rejected using Bash `EUID` plus a reported-UID consistency check. The nearest existing ancestor of every resolved target is canonicalized with `pwd -P`; protected macOS prefixes, including the `/private/etc` alias, are rejected before mutation.

## Test hooks and isolation

Tests execute the real script using a fixture-owned environment. `HOME` points to `tmp_path`; a fixture-owned `uname` placed first on `PATH` returns Darwin or a requested non-Darwin value. The script has no test-only switches. A failure-injection test shadows an ordinary command used during publication, while leaving inspection commands intact, to prove restoration.

## Compatibility

Production syntax is limited to Apple Bash 3.2: no associative arrays, `mapfile`, `readarray`, `globstar`, GNU long options, or Bash 4 parameter features. Runtime dependencies are commands shipped with macOS; `/usr/bin/rsync` is used explicitly for copy mode.

## Verification

Required evidence:

1. RED test execution before the script exists.
2. `/bin/bash -n scripts/install_macos.sh`.
3. Focused installer pytest run with zero skips.
4. Complete unit pytest run with zero skips.
5. Critical Ruff diagnostics and `git diff --check`.
6. Static prohibited-operation scan.
7. Real-host generic dry-run plus before/after filesystem evidence.
8. Live FreeCAD execution documented as `HOLD` while unavailable.

Final evidence after PR-CI correction: `69 passed in 18.30s` in the focused suite, `375 passed in 46.43s` in the exact CI-equivalent security slice, and `1625 passed in 150.79s` in the complete unit suite, all with zero skips. Independent review of the final multi-leading-slash normalization passed at 98.4% (C1 99%, C2 99%, C3 99%, C4 98%, C5 97%). These are local gates; GitHub-hosted CI remains `HOLD` until the correction commit is pushed and its latest-head checks pass.
