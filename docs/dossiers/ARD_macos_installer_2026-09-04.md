# Architecture Requirements Dossier: macOS Installer

## Control record

- Workflow: TCCode with Agent Workflow v4, thorough execution, team size 4.
- Worktree: `/Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-183200-macos-installer`
- Branch: `agent-workflow/20260904-183200-macos-installer`
- Base: `04fc3ba94d7882684369a9cd2b8a4999a39811c9`
- Baseline: `1556 passed in 113.60s`, zero skips.
- Safety invariant: never start, stop, restart, or reboot FreeCAD, a service, a server, or a computer.

## Goal

Provide one Bash 3.2-compatible script that installs this checkout as a FreeCAD user workbench on macOS. The default result is a symbolic link for development; `--copy` creates a self-contained directory. The script must be deterministic, reversible on explicit replacement, and safe for paths containing spaces.

## Boundaries

The installer may change only the selected FreeCAD `Mod` directory and its `freecad-ai` child. It must not use `sudo`, install packages, launch FreeCAD, edit provider configuration, read or write API keys, touch system directories, or use the network.

Live FreeCAD loading is outside this implementation because no FreeCAD application or CLI is installed on the validation host. That gate remains `HOLD`, not passed.

## Architectural decisions

1. Source is the physical parent of the script directory and must contain `Init.py`, `InitGui.py`, `package.xml`, and `freecad_ai/`.
2. `--mod-dir` accepts only an absolute path and has highest precedence.
3. Without it, exactly one existing `$HOME/Library/Application Support/FreeCAD/v*/Mod` directory is selected. Multiple matches fail closed. With no match, the generic `$HOME/Library/Application Support/FreeCAD/Mod` path is used.
4. Destination is always `<Mod>/freecad-ai`.
5. An absent destination may be installed. A correct installation is an idempotent no-op. Every other existing object, including a broken symlink, is a conflict unless `--replace` is present.
6. Replacement moves the old object to a unique timestamped sibling backup before publishing. Publication failure restores it.
7. Both modes build and validate in a sibling staging directory. Publication then exclusively claims the final destination: `ln` creates the final link directly, while copy mode atomically claims an empty directory with `mkdir` and copies the validated staged payload into it.
8. A per-target atomic directory lock serializes cooperating installer processes. State is classified again after lock acquisition, and the lock is removed after success, failure, and handled signals. An existing or stale foreign lock is never removed automatically.
9. Root execution is refused. The nearest existing target ancestor is resolved physically so protected system prefixes and symlink aliases such as `/etc` to `/private/etc` are rejected.
10. `--dry-run` and `--check` are read-only. `--check` accepts either a link resolving to the current checkout or a structurally valid copied workbench.

## Risk controls

| Risk | Controls |
|---|---|
| Wrong FreeCAD version | Explicit target wins; one candidate is deterministic; several candidates fail with guidance. |
| Existing installation loss | Explicit `--replace`, sibling backup, unique suffix, restore on failure. |
| Partial copy/link | Same-filesystem staging, exclusive final target claim, required-file validation, owned-partial cleanup, and backup restoration. |
| Broken or hostile links | Detect with both `-e` and `-L`; never infer that a broken link is absent. |
| Spaces or shell injection | Quote all expansions; no `eval`; absolute custom target; subprocess tests with spaces. |
| Real profile mutation by tests | Temporary HOME and fake `uname` exist only in each test subprocess. |
| False validation claim | Real Darwin dry-run is required; live FreeCAD remains explicitly unavailable. |

## Acceptance and vetoes

The change is acceptable only if focused installer tests and the full unit suite pass with zero skips, Bash syntax passes on the host Apple Bash 3.2, dry-run leaves the real profile unchanged, and static inspection finds no prohibited operations. Silent overwrite, ambiguous target choice, failed rollback, test access to the real profile, or presenting unavailable FreeCAD execution as passed is a veto.

## Implementation simulation

| Criterion | Score | Evidence |
|---|---:|---|
| C1 technical feasibility | 99% | Host provides Darwin, Apple Bash 3.2, and OpenRSYNC 2.6.9. |
| C2 logical correctness | 98% | Deterministic target state machine and transactional replacement. |
| C3 completeness | 98% | Every approved option and failure state is mapped to a test. |
| C4 risk control | 97% | No privilege/process/config actions; backup and restore are explicit. |
| C5 maintainability | 97% | One dependency-free script and behavior-level subprocess tests. |

Aggregate: **97.8% — PASS**. This remains conditional on fail-closed ambiguity and verified rollback.

## As-built security review

Three corrective TDD cycles followed successive independent vetoes for signal rollback, concurrent target access, BSD `mv` nesting, canonical system-path aliases, fresh-copy cleanup, and correct-link races. The final implementation uses a target lock, physical ancestor resolution, direct exclusive claims, and state-aware `EXIT` cleanup. The fourth independent review found no scoped code blocker and scored C1 99%, C2 98%, C3 97%, C4 97%, and C5 96%: aggregate **97.4% — PASS**.

Accepted residuals are fail-closed stale-lock recovery after `SIGKILL`, manual recovery when an external actor changes the destination during rollback, the unavoidable authority of another process under the same user account, a briefly observable copy while the final payload is written, and user responsibility for explicit non-system external targets. Live FreeCAD loading remains a separate `HOLD`.
