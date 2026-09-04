# Product Proposal Dossier: Future macOS Installer Improvements

## Decision frame

The current installer is intentionally a small, dependency-free Bash 3.2 user-
workbench installer. The as-built root and independent focused runs each pass
56 tests with zero skips; the full unit suite passes 1,612 tests with zero
skips; the scoped security review passes at 97.4%. It refuses root/system
scope, serializes each target, validates staged link/copy content, claims final
destinations directly, and cleans race, failure, signal, and partial state.
The proposals below are optional future improvements, not retroactive defects
or authority to expand the current implementation.

## Quick-win-first ranking

| Rank | Proposal | Security/UX value | Effort | Compatibility risk |
|---|---|---:|---:|---:|
| 1 | Read-only target discovery listing | Medium | Low | Low |
| 2 | Pinned ShellCheck maintenance gate | Medium | Low | Low |
| 3 | Versioned copy manifest | Medium | Medium | Medium |
| 4 | Backup inventory and retention assistant | Medium | Medium | Medium |
| 5 | Native macOS/FreeCAD acceptance matrix | High | High | Medium |
| 6 | Signed/notarized distribution | High | High | High |

## P1 — Read-only target discovery listing

**Proposal:** add a command such as `--list-targets` that prints generic and
versioned candidates and an exact `--mod-dir` example without choosing one.

**Pros**

- Makes fail-closed ambiguity easier to resolve.
- Remains read-only and dependency-free.
- Reduces path transcription mistakes, especially with spaces.

**Cons**

- Expands the CLI and documentation surface.
- Displayed candidates may include stale FreeCAD directories.

**Risks**

- Users may mistake listing for validation or select the newest-looking path
  without confirming the intended FreeCAD release.

**Mitigations**

- Label every candidate as unselected; never infer a winner.
- Print quoted copyable commands and retain explicit absolute-path validation.
- Add snapshot tests proving zero mutation.

## P2 — Pinned ShellCheck maintenance gate

**Proposal:** run a provenance-pinned ShellCheck version in a separate quality
gate alongside Apple Bash syntax and behavior tests.

**Pros**

- Detects quoting, expansion, trap, and portability mistakes early.
- Small CI/documentation change with no runtime dependency.
- Complements tests for branches that are hard to inject.

**Cons**

- ShellCheck's portability model may prefer constructs unavailable or awkward
  in Apple Bash 3.2.
- Tool upgrades create review work.

**Risks**

- Blanket suppressions could hide meaningful findings.
- A GNU/Linux ShellCheck gate might encourage untested GNU behavior.

**Mitigations**

- Pin binary/action provenance, review every suppression individually, and keep
  `/bin/bash -n` plus real Darwin behavior tests authoritative.

## P3 — Versioned cryptographic copy manifest

**Proposal:** have copy mode publish an allowlisted manifest containing the
add-on version and hashes of shipped files; extend `--check` to validate it.

**Pros**

- Distinguishes a structurally valid older copy from the current source.
- Detects partial/manual changes and supports precise support reports.
- Enables reproducible release artifact verification.

**Cons**

- Manifest generation and exclusions add complexity.
- Development link mode cannot use the same immutable comparison.
- User-customized installed files would fail integrity checks.

**Risks**

- Hashing unintended files could inventory secrets, caches, or local identity.
- A stale manifest could produce false assurance.

**Mitigations**

- Use a strict shipped-file allowlist, semantic version field, deterministic
  ordering, and explicit “structural legacy copy” handling.
- Never include content outside the staged copy.

## P4 — Backup inventory and explicit retention assistant

**Proposal:** provide read-only backup inventory and a separate preview-first
cleanup action with exact target confirmation.

**Pros**

- Helps users understand disk use and available rollback points.
- Makes recovery paths discoverable.
- Can preserve newest/youngest backups under a transparent policy.

**Cons**

- Introduces destructive functionality absent from the current installer.
- Backup types may be files, directories, or symlinks.
- Age/count policy can conflict with organizational retention needs.

**Risks**

- Incorrect matching or symlink traversal could delete unrelated data.
- Automatic pruning could remove the only working installation.

**Mitigations**

- Default to inventory only; require a separate explicit cleanup command.
- Pin the exact selected `Mod` directory, reject symlinks/foreign names, show a
  complete preview, and keep at least one verified rollback candidate.
- Develop under a new destructive-action dossier and failure-injection suite.

## P5 — Native macOS and FreeCAD acceptance matrix

**Proposal:** add approved macOS runners or lab hosts covering supported macOS,
FreeCAD, Python, PySide, Qt, generic/versioned paths, and link/copy modes.

**Pros**

- Converts the current live FreeCAD HOLD into evidence.
- Catches host directory and embedded-Python changes.
- Validates first-load and disposable-document behavior, not only filesystem
  structure.

**Cons**

- GUI automation and FreeCAD artifacts are expensive to maintain.
- Multiple architectures/releases increase matrix time.
- Hosted runners may not reflect user security controls or filesystems.

**Risks**

- A passing synthetic GUI test could be overclaimed as all-host support.
- Tests might mutate a persistent profile or hang a runner.

**Mitigations**

- Publish the exact supported matrix; isolate HOME and documents; enforce hard
  timeouts; never reuse a real user profile; treat skips as HOLD, not pass.

## P6 — Signed and notarized installer distribution

**Proposal:** distribute a signed/notarized macOS artifact with published
checksums and provenance while retaining the auditable shell script.

**Pros**

- Improves origin and tamper assurance for non-developer users.
- Integrates with macOS trust expectations.
- Can bind release source, tests, artifact, and SBOM.

**Cons**

- Requires Apple credentials, secure signing operations, and renewal.
- Packaging can obscure the simple current filesystem transaction.
- Release operations and incident response become more complex.

**Risks**

- Credential compromise could sign malicious artifacts.
- A signed package may gain wider scope or encourage blind installation.
- Script and packaged behavior could drift.

**Mitigations**

- Use hardware-backed/short-lived signing, two-person release approval,
  reproducible manifest comparison, least-privilege user scope, and published
  source/checksums. Keep package tests behavior-equivalent to the script.

## Recommended sequence

Approve P1, then P2 as bounded quick wins. Design P3 and P4 only after defining
compatibility and destructive-action policy. P5 is the next evidence priority
because it closes the current runtime HOLD. P6 requires a separate release-
security architecture and operational authority.
