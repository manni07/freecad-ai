# Live Worktree Validation Report

- Worktree: `/Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation`
- Branch: `agent-workflow/20260904-115556-security-remediation`
- Base: `15774022a1c981335135d95928bd6cb4f7ba0431`
- Audit SHA-256: `d41a1861a11a366a07d4f966185fad8d8b2ae7c7cf87bf5f2a9c3957c43e1ad0`
- Workflow: TCCode + Agent Workflow v4, thorough, fixed team of four

## Verified evidence

- Final plain unit command: 1,556 passed, zero skips/failures, 113.68 seconds.
- Final coverage command: 1,556 passed, zero skips/failures, 131.40 seconds.
- Diff-cover: 97%, 862 changed lines, 24 missing.
- Phase-F focused gate: 55 passed; schema probe validated CycloneDX 1.5, five components and five dependency nodes.
- Critical Ruff (`E9,F63,F7,F82`): PASS.
- Bandit: 3 High, 7 Medium, 89 Low; Highs mapped to immutable-audit contextual triage; no `#nosec`.
- Declared PyPI dependency audit: PASS only for the explicit empty set.
- Editable install: version `0.23.1a0`, no declared runtime dependencies, only `freecad_ai` top-level package.
- `git diff --check`: PASS at the documentation gate.
- Integration selection: 88/88 skipped with `FreeCAD AppImage not found`; this is a Runtime `HOLD`, not a pass.

## Isolation and generated files

Unit fixtures redirect all managed config/data paths to process-private temporary roots. No real token or secret path was created. `.coverage`, `build/security-coverage.xml`, `.DS_Store`, and any generated egg-info are not deliverables; egg-info was moved to Trash after verification. The parent checkout was not modified by this workflow.

The final post-test metadata-only manifest of the real
`~/.config/FreeCAD/FreeCADAI` tree (relative path, kind, mode and size; never
file contents) contains six entries and has SHA-256
`baacca82f7b1b09f74d66270a7fa1e06ac711f8478ead76ed929cf04be41b871`.
Neither `mcp_server.token` nor a `secrets/` directory is present. This current
manifest uses a documented serializer distinct from the earlier Phase-E
checkpoint hash; the two hash strings must not be compared as if their input
formats were identical.

## Status

Technical remediation: `PASS`. Runtime/release: `HOLD`. Git commit/push/PR/merge and release require a later explicit gate. Refer to the Session Transfer Protocol for exact blockers and resume commands.
