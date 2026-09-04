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
