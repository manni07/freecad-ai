# Development Diary v000 — Security Remediation

## 2026-09-04 — Scope and isolation

- Source audit frozen at SHA-256 `d41a1861a11a366a07d4f966185fad8d8b2ae7c7cf87bf5f2a9c3957c43e1ad0`.
- Base `15774022a1c981335135d95928bd6cb4f7ba0431`; isolated branch/worktree created.
- TCCode led requirements, architecture, technical design, implementation, test dossier and gates. Agent Workflow v4 used the fixed four-person thorough team.
- Baseline exposed one FreeCADCmd case-preservation failure plus 88 unavailable FreeCAD integration skips. They were retained as evidence, not normalized.

## Phases A–C — Execution and prompt boundaries

- Removed the unverified TLS fallback and converted HTTPS context failure to visible fail-closed behavior.
- Replaced unsafe executable temporary naming with private, exclusive workspaces and explicit preflight statuses.
- Made HTTP omission of `execute_code` a registry property, not a display-only filter.
- Added an in-memory, process-only AI-Python capability and a mandatory per-call review. Fixed a review-dispatch defect in which rejection could otherwise allow a retry/later batch call.
- Rebuilt project-instruction loading around canonical containment, bounded reads, deterministic fingerprints and user decisions. A cross-review caught a fail-open resolver path; it now aborts locally without clearing or sending the request.

## Phases D–E — Durable data and HTTP-MCP

- Added private atomic writes, permission hardening, collision-safe/read-back secret migration and default metadata-only logs.
- A full-suite run revealed incomplete test-path isolation that created an empty real-profile `secrets/` directory. It was verified empty and removed; the fixture now redirects every managed path before collection. Later real-config metadata hashes stayed unchanged.
- Added strict token file semantics, private one-shot address resolution, all-route Bearer auth, rate limiting and pre-thread concurrency limits. Adversarial review closed mapped/scoped address acceptance and secret-reflecting startup errors.
- A full regression found four stale SSE fixtures missing the now-mandatory test token. Contract-aligned test fixtures fixed this without weakening production auth.

## Phase F — Release assurance

- Aligned 0.23.1-alpha metadata and Python ≥3.11; made the empty PyPI runtime dependency set explicit and package discovery exact.
- Added a five-component CycloneDX 1.5 runtime inventory. Two independent HOLD reviews drove validation tightening and a POSIX component-by-component directory-FD writer resistant to parent swap/TOCTOU.
- Final focused Phase-F slice: 55 passed. Editable install metadata contained only `freecad_ai` and no dependencies.
- Added meaningful tests for all changed-line gaps. Final plain/coverage runs each passed 1,556 tests with no skips (113.68 s / 131.40 s); diff coverage 97% (862 changed lines, 24 missing).
- Critical Ruff is green. Full Ruff remains a recorded legacy/quality backlog. Bandit remains 3 High/7 Medium/89 Low; all three High reports have exact contextual audit triage and no scanner suppression.
- Scoped pip-audit passes for the explicitly empty declared PyPI set. It is deliberately not called a real-host scan.

## Pre-integration decision

Implementation and documentation are complete enough for review, but release remains `HOLD`. The exact integration selection produced 88 `FreeCAD AppImage not found` skips and is not a pass. Missing evidence: supported FreeCAD GUI/integration; real disposable-document approval; live authenticated FreeCAD MCP positive/negative handshake; actual-host SBOM plus CVE scan; isolated private-LAN test; Windows ACL/POSIX equivalence; workflow Action SHA/transitive pins. At this checkpoint, no process was restarted and no release/merge had been performed.

## Repository integration

- Fresh pre-PR verification passed all 1,556 unit tests in 129.03 seconds with no skips; critical Ruff, scoped declared-dependency audit, documentation structure/links, credential-pattern scan, and staged-diff checks passed.
- Commit `7ab3900f178ae8360c11da3933a30d263555e23f` was pushed to `manni07/freecad-ai` on branch `agent-workflow/20260904-115556-security-remediation`.
- Pull request `https://github.com/manni07/freecad-ai/pull/1` targets the fork's `master`. The upstream repository `ghbalf/freecad-ai` was not modified.
- The first GitHub security-regression run failed during collection because its pinned test-tool installation omitted PySide while two selected security tests import the UI compatibility layer. After pinning the locally verified `PySide6==6.11.2`, Ubuntu exposed a second missing prerequisite, `libEGL.so.1`; the workflow now installs the minimal `libegl1` runtime package before test tooling. Runtime dependencies remain empty because FreeCAD supplies the GUI binding in production.
- The user explicitly authorized commit, PR, and merge. This repository integration does not resolve the runtime/release HOLDs above and does not authorize a process restart or deployment.

## 2026-09-04 — macOS installer workflow

- Began a new isolated TCCode/Agent Workflow v4 worktree at base `04fc3ba94d7882684369a9cd2b8a4999a39811c9` for a user-scoped macOS installer; no FreeCAD or system process was started or restarted.
- Defined 38 subprocess behavior cases with temporary HOME/TMPDIR/PATH and a fixture-owned `uname`. The intentional pre-implementation run failed all 38 cases solely because `scripts/install_macos.sh` was absent, with no skips or harness errors after selecting the validated test interpreter.
- Implemented the Bash 3.2 installer contract: Darwin/source gates, deterministic versioned/generic/explicit target choice, sibling-staged link/copy publication, idempotence, fail-closed conflicts, explicit collision-safe backups, rollback, spaces, and read-only dry-run/check modes.
- Final focused evidence: `38 passed in 4.49s`, zero skips. Final complete unit regression: `1594 passed in 132.87s`, zero skips.
- The required time-bounded `agy` review attempt was permission-blocked after 9.1 seconds and produced no review; unrestricted permissions were not enabled and no external PASS was claimed.
- Filesystem implementation/tests are PASS. Live loading remains HOLD because no supported FreeCAD application or CLI exists on the validation host; automated structure checks are not substituted for runtime evidence.

## 2026-09-04 — macOS installer final security closure

- Three adversarial review cycles expanded the installer contract to include early effective-root refusal, canonical rejection of macOS system paths and symlink-parent bypasses, a per-target lock, validated sibling staging, exclusive direct `ln`/`mkdir` destination claims, and the final copy `rsync`.
- Failure injection now proves destination-reappearance handling, correct-source link races, fresh-install cleanup independent of backup state, second-copy failure cleanup, and TERM-aware restoration without stage, partial, or lock residue.
- Final evidence is `56 passed in 14.70s` from the root focused run, an independent `56 passed in 21.40s`, and `1612 passed in 149.15s` for the full unit suite; all three runs had zero skips.
- The final security review is PASS at 97.4% (C1 99%, C2 98%, C3 97%, C4 97%, C5 96%). The first headless `agy` attempt was permission-blocked; a later independent architecture review could run it correctly, incorporated concrete findings, and completed the final scoped review.
- Filesystem code and automated tests are PASS. A real-host dry run is not yet recorded here, and supported live FreeCAD loading remains HOLD. No process was started or restarted.

## 2026-09-04 — macOS installer read-only host evidence correction

- Subsequent authorized evidence completed the previously pending real Darwin gate: `scripts/install_macos.sh --dry-run` returned rc 0, resolved `/Users/turgay/Library/Application Support/FreeCAD/Mod/freecad-ai`, and the real profile remained `ABSENT` before and after.
- Real `--check` returned the expected rc 1 for the absent installation and likewise preserved `ABSENT` before/after. This closes the read-only host gate only; no installation or FreeCAD process was started, and live FreeCAD loading remains HOLD.

## 2026-09-04 — macOS installer pre-commit verification

- The exact staged tree repeated the complete unit suite immediately before commit: `1612 passed in 145.05s`, zero skips. This supersedes the earlier timing as the final integration gate without invalidating either successful run.

## 2026-09-04 — macOS installer PR CI correction

- The first two PR security-regression runs exposed a real cross-platform canonicalization defect: when a protected macOS top-level directory is absent on Linux, joining physical root `/` to a slash-prefixed unresolved suffix produced `//...` and missed the protected-prefix match. A local RED reproduced it; root joining now emits exactly one leading slash.
- The same runs exposed an unrelated, pre-existing race in the MCP admission test. The ninth request is intentionally rejected before a thread is created, but `urllib` could still be sending its POST body when the server closed. The test now reads the raw 503 response through a bodyless request and retains the eight-thread assertion; production MCP behavior is unchanged.
- Corrected evidence: `60 passed in 17.29s` for the installer suite, `20/20` repeated MCP admission runs, `366 passed in 43.28s` for the exact CI-equivalent security slice, and `1616 passed in 144.81s` for the complete unit suite; zero skips throughout.

## 2026-09-04 — macOS double-leading-root security closure

- Final review reproduced that macOS preserves an explicitly supplied `//System` physical path, which still bypassed single-slash protected-prefix patterns after the first CI correction. Eight parameterized RED cases captured every protected prefix; the installer now collapses all multi-leading-slash physical ancestors before matching.
- Final local evidence on the corrected code: `69 passed in 18.30s` for the installer suite, `375 passed in 46.43s` for the exact CI-equivalent security slice, and `1625 passed in 150.79s` for the complete unit suite, all with zero skips. GitHub-hosted status remains HOLD until this correction is committed and pushed.
