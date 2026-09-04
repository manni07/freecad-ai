# Implementation Dossier: macOS Installer

## Planned files

- `scripts/install_macos.sh`: the complete installation state machine.
- `tests/unit/test_install_macos.py`: isolated behavior and safety tests.
- `.github/workflows/security-regression.yml`: include the deterministic installer test slice.
- `README.md`: point macOS users to the installer and guide.
- TCCode artifacts under `docs/` for requirements, tests, handoff, verification, open items, proposals, and the user manual.

Python production modules and existing audit artifacts are outside scope.

## Implementation sequence

1. Write behavior tests and record RED while the script is absent.
2. Add option parsing, Darwin/source validation, and deterministic target discovery.
3. Add read-only inspection and dry-run behavior.
4. Add staged symlink and copy publication.
5. Add explicit conflict replacement, unique backup, per-target serialization, canonical system-path rejection, direct destination claims, and signal-aware rollback.
6. Run focused tests after each slice, then the full unit suite.
7. Complete independent security review, documentation, real-host dry-run, commit, push, and PR without merging.

## Internal functions

The script remains one file with small single-purpose functions for usage/error output, source validation, target resolution, installation classification, structural validation, staging cleanup, unique backup selection, rollback, and publication. Global state is limited to parsed options and resolved paths. Every path expansion is quoted.

No generic framework or installer abstraction is introduced. Copy idempotence is structural: an existing non-symlink directory containing the required workbench entry points is accepted only when `--copy` is selected; updating it requires `--replace`.

## TDD traceability

Tests must fail for the absent installer, then cover:

- platform rejection before filesystem creation;
- explicit, single-version, generic, and ambiguous target selection;
- source validation through a copied fixture checkout;
- link and copy results and excluded development content;
- correct-install no-op without backup;
- foreign file/directory, wrong link, and broken link conflicts;
- replacement backup uniqueness and rollback after injected publish failure;
- root/system-path refusal, canonical symlink-parent containment, and stale-lock refusal;
- target reappearance during final link/copy claims, partial-copy cleanup, and link/copy signal rollback;
- paths containing spaces;
- dry-run/check non-mutation;
- rejected option combinations;
- absence of privileged, process-control, package-install, provider, credential, and configuration behavior.

Tests express intent through externally observable return codes, diagnostics, symlink resolution, tree snapshots, and backup contents. They do not assert private function names.

## Security review checklist

- Target cannot be `/`, relative, or silently selected among multiple versions.
- Existing destination is detected with `-e || -L`.
- `--replace` is the only overwrite authority.
- Backup precedes publication and is restored after any later failure.
- Staging is a sibling on the same filesystem and is removed on every exit.
- A per-target lock is acquired before reclassification and remains held through cleanup; a foreign lock is fail-closed and untouched.
- Publication never uses directory-following `mv` for the final claim: link mode claims with `ln`, copy mode claims with `mkdir`, and every owned incomplete copy is removed before backup restoration.
- No unquoted user-controlled path reaches a command.
- No `eval`, network, `sudo`, package manager, application launch, restart/reboot, key, or config mutation exists.
- Logs contain paths/actions only.

## Gate

Implementation proceeded because pre-implementation C1–C5 were all above 95% (aggregate 97.8%). Three independent veto rounds were converted into RED tests and fixes. The final as-built review scored 99/98/97/97/96, aggregate 97.4%, with no scoped code blocker. The focused suite passed 56 tests and the full unit suite passed 1,612 tests with zero skips. FreeCAD runtime loading remains a documented external `HOLD`.
