# macOS Installer Open Items — 2026-09-04

These are future acceptance or hardening measures, not undisclosed defects in
the tested installer contract. The register contains exactly three High, three
Medium, and three Low items. Implementing any proposal requires a new scope.
The as-built filesystem contract passed two 56-test focused runs, a 1,612-test
unit regression, and the 97.4% security review. Only H1 is an active runtime
acceptance HOLD; H2 through L3 remain optional future improvements.

## High measures

### H1 — Supported FreeCAD live-load acceptance

- Status: `HOLD — ENVIRONMENT UNAVAILABLE`.
- Rationale: filesystem behavior is tested, but no supported FreeCAD app/CLI is
  installed on the validation host.
- Future evidence: install into an approved isolated user target, verify Report
  view/import/workbench selection and one disposable-document smoke test, then
  verify the preserved rollback path. No skip or absent runtime counts as pass.

### H2 — Signed and notarized release distribution

- Status: `PROPOSAL`.
- Rationale: the repository shell script is appropriate for a reviewed
  checkout but is not itself a signed/notarized macOS package or provenance
  guarantee.
- Future measure: design a separately signed artifact and checksum/provenance
  workflow without weakening transparent script behavior or user-level scope.

### H3 — Real-profile transactional recovery drill

- Status: `PROPOSAL / REQUIRES EXPLICIT AUTHORITY`.
- Rationale: injected temporary-path tests prove rollback logic; a controlled
  operational drill would validate storage, permissions, and recovery on the
  supported release filesystem.
- Future measure: use a disposable macOS account/profile, force publication
  failure safely, preserve evidence, and demonstrate exact backup restoration.
  This is additional operational assurance, not a report of current data loss.

## Medium measures

### M1 — Native macOS CI matrix and Apple Bash regression

- Status: `PROPOSAL`.
- Rationale: current tests execute on Darwin and statically reject Bash 4/GNU
  constructs; a maintained macOS CI matrix would continuously cover supported
  macOS/FreeCAD directory layouts and Apple Bash updates.
- Future measure: pin runner/action provenance and run focused tests, syntax,
  generic dry-run snapshots, and artifact checks without launching FreeCAD.

### M2 — Cryptographic copy manifest and version-aware check

- Status: `PROPOSAL`.
- Rationale: copied-workbench `--check` is intentionally structural. Users may
  later benefit from distinguishing a valid older copy from the current source.
- Future measure: publish a deterministic allowlisted manifest/version marker,
  verify it read-only, and define compatible handling for existing copies.

### M3 — Backup inventory and guided retention policy

- Status: `PROPOSAL`.
- Rationale: retaining every replacement backup maximizes recoverability but
  leaves lifecycle decisions to the user.
- Future measure: add a read-only inventory first, then an explicit age/count
  cleanup flow with preview, exact targets, refusal of symlinks, and no default
  deletion. Existing backups must never be silently pruned.

## Low measures

### L1 — ShellCheck policy for the installer

- Status: `PROPOSAL`.
- Rationale: behavior tests and static vetoes are green; an approved ShellCheck
  version could add maintainability diagnostics.
- Future measure: pin the tool, document intentional Apple Bash constructs,
  and avoid blanket suppressions or GNU-oriented rewrites.

### L2 — User-facing target discovery helper

- Status: `PROPOSAL`.
- Rationale: fail-closed ambiguity is safe but requires users to locate the
  desired versioned `Mod` directory manually.
- Future measure: add a read-only listing command that prints all candidates
  and copyable explicit invocations without making a selection or launching an
  application.

### L3 — Localized installer diagnostics

- Status: `PROPOSAL`.
- Rationale: concise English diagnostics satisfy the current contract; optional
  localization could improve accessibility for non-English macOS users.
- Future measure: keep stable exit behavior and tests while introducing a
  dependency-free message catalog. Do not parse localized prose in automation.

## Promotion rule

The current filesystem gate remains PASS while H1 runtime acceptance remains
HOLD. H2–L3 are future improvements and must not be cited as current failures.
No measure authorizes installation, backup deletion, process restart, commit,
push, merge, or release.
