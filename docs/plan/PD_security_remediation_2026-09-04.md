# Planning Document: Security Remediation

## Execution contract

- Lead process: TCCode; orchestration: Agent Workflow v4 thorough/critical; fixed team size 4.
- Source audit: `docs/audits/security-audit-2026-09-04.html`, SHA-256 `d41a1861a11a366a07d4f966185fad8d8b2ae7c7cf87bf5f2a9c3957c43e1ad0`.
- Base: `15774022a1c981335135d95928bd6cb4f7ba0431` in the isolated workflow worktree.
- Requirements: `docs/dossiers/ARD_security_remediation_2026-09-04.md` and `docs/dossiers/TRD_security_remediation_2026-09-04.md`.
- Never revert unrelated files, merge automatically, or restart/reboot a process, server, or computer without explicit user confirmation.

## Quick-Win-First order

| Rank | Slice | Coverage | Effort | Risk | Reversible | Dependency reason |
|---|---|---:|---:|---:|---:|---|
| 1 | TLS fail-closed | SEC-04 complete | low | low | high | isolated and blocks a credential/tool-call chain |
| 2 | HTTP omission of `execute_code` | SEC-01/03 partial | low | low | high | immediate immutable reduction before auth work |
| 3 | Private temp storage | SEC-05 complete | low | low | high | isolated executor fix |
| 4 | GUI raw-code capability and confirmation | SEC-01 complete | medium | medium | high | establishes central policy before prompt/UI docs |
| 5 | Instruction containment and trust | SEC-02 complete | medium | medium | high | prevents prompt exfiltration before persistence refactor |
| 6 | HTTP token, private bind, limits | SEC-03 complete | high | medium | medium | intentional client compatibility break |
| 7 | Secure persistence/migration/redaction | SEC-06 complete | high | high | medium | touches durable user state; requires prior atomic primitives |
| 8 | Runtime inventory and SBOM | SEC-07 complete | medium | low | high | release assurance after runtime behavior stabilizes |

## Phased implementation

### Phase 0 — Baseline and test dossier

Create the detailed TD before production edits. Record current unit results, the known missing-PySide and FreeCADCmd-case failures, and selected security commands. Define fixtures that redirect `FREECAD_AI_CONFIG_DIR` to temporary directories and never touch real user configuration.

Gate: test simulation scores greater than 95% for coverage completeness, isolation, assertion quality, maintainability, and risk targeting.

Risk: tests could touch user config, encode implementation details, or normalize existing failures.

Mitigations:

1. Force temporary config paths and mocked FreeCAD/ParamGet in every persistence test.
2. Assert security outcomes at public boundaries—schema, dispatch count, HTTP status, filesystem mode—not private line structure.
3. Preserve the baseline failure list verbatim and prohibit changing tests merely to obtain green output.

### Phase 1 — Fail-closed primitives

Implement verified provider TLS, private temporary execution storage, and unconditional HTTP registry exclusion for `execute_code`. Add focused tests first, then code.

Gate: all new TLS/temp/HTTP-tool tests and affected existing executor/MCP tests pass; no `_create_unverified_context` or `tempfile.mktemp` remains in production.

Risk: packaged FreeCAD loses cloud access, temp cleanup changes subprocess behavior, or HTTP exclusion is schema-only.

Mitigations:

1. Keep local HTTP provider behavior and raise only when HTTPS is attempted.
2. Keep script and result alive for the full subprocess/result-read context and test timeout/exception cleanup.
3. Physically omit the tool from HTTP registry and separately test both `tools/list` and direct `tools/call`.

### Phase 2 — GUI code-execution policy

Add the process-session gate, a dedicated chat-header control independent of Dangerous mode, schema filtering, conditional prompt text, toggle warning, execution-edge recheck, and one-call review flow. The state survives New Chat and dock recreation but is never persisted. Remove `auto_execute` as a bypass for model-originated raw code while retaining manual Plan execution.

Gate: initial/armed/disarmed schemas, prompt parity, rejection, stale call, interruption, and exactly-once execution pass; manual Plan flow is unchanged.

Risk: UI deadlock, double execution, or state/schema drift.

Mitigations:

1. Run the modal only on Qt's main thread and always return a terminal worker result.
2. Return the dialog's existing execution result instead of calling the registry handler afterward.
3. Combine physical schema exclusion with a fresh gate check immediately before every call.

### Phase 3 — Trusted project instructions

Implement bounded bundle discovery, canonical include containment, deterministic fingerprints, trust persistence, and pre-send preview. Make prompt construction consume only an approved snapshot.

Gate: the complete malicious-path matrix fails closed; allow/ignore/cancel and changed/unchanged fingerprint cases pass; no unapproved bytes reach a mocked provider request.

Risk: false root selection, TOCTOU, or partial-content leakage on nested failure.

Mitigations:

1. Define root solely from the selected instruction file's canonical directory and display it.
2. Fingerprint and send the same in-memory snapshot.
3. Treat any nested resolver error as failure of the entire bundle and test nested error propagation.

### Phase 4 — Authenticated private-network MCP

Provision the managed default installation token, treat a configured custom token path as read-only, enforce Bearer auth on every verb/path, reject public binds, resolve hostnames once and bind the validated numeric result, implement pre-thread concurrency and token-bucket rate gates, and update settings/toolbar/CLI documentation. Existing Host, Origin, protocol, body and timeout controls remain.

Gate: authenticated live loopback handshake passes; all unauthenticated/malformed routes fail without dispatch; public/wildcard bind, 429 and 503 cases pass; legacy SSE regressions pass.

Risk: existing clients are locked out, token leaks, or thread exhaustion precedes the limiter.

Mitigations:

1. Document the intentional header migration and print only the token-file path; preserve STDIO.
2. Keep token out of config, URLs, errors and logs; use `0600` and constant-time compare.
3. Acquire the concurrency semaphore before creating a worker thread and retain request-size/time limits.

Accepted residual at this gate: private-LAN plaintext can expose a token to a same-network observer. Internet exposure is unsupported and technically rejected. Authenticated HTTP `run_macro` and STDIO `execute_code` remain intentional.

### Phase 5 — Durable-data hardening

Introduce secure atomic writes, permission hardening, verified literal-secret migration, ParamGet de-duplication, and metadata-only diagnostic logs. Do not change retention defaults or delete existing data.

Gate: failure-injection tests prove the old secret survives every incomplete migration; all managed new files/directories have expected POSIX modes; default logs contain no payloads or secrets.

Risk: migration loses credentials, symlink targets are overwritten, or platform permission claims are false.

Mitigations:

1. Write, read back, and atomically persist the new reference before changing/removing the old source.
2. Reject symlinks with `lstat`, use same-directory exclusive temp files, and allocate a new name on conflict.
3. Verify POSIX modes; document Windows limitations and retain data with a visible warning on any hardening failure.

### Phase 6 — Runtime inventory, system verification and documentation

Add the supported-runtime policy with Python `>=3.11` and no unverified tested-host claims, CycloneDX generator, semantic metadata tests, README/security manual updates, audit remediation status, open-item report, STP, diary, project manual, live worktree report, commit, push, and PR preparation.

Gate: generated SBOM validates and contains every required runtime component without local identity data; unit suite and supported FreeCAD integration/GUI matrix are fully reported. Security agent score must be at least 90 and implementation/test simulations must each exceed 95%.

Risk: incomplete SBOM is treated as assurance, metadata drifts, or unavailable GUI/runtime checks are hidden.

Mitigations:

1. Fail generation when a required version is missing and label external scan availability separately.
2. Add a three-way semantic version/minimum-runtime parity test.
3. Report blocked/skipped runtime tests with exact commands and keep completion fail-closed; never call partial evidence a live pass.

## Verification sequence

After every phase, run its focused TD slice and the relevant previous slices. Final order:

1. Pure unit tests excluding PySide/FreeCAD runtime requirements.
2. Full configured pytest suite with exact pass/fail/skip/deselect counts.
3. Static security scan and targeted absence searches.
4. Live token-authenticated loopback MCP handshake and negative request, without restarting a running server.
5. FreeCAD/PySide GUI and integration tests only in an available supported runtime; otherwise record a hard validation gap.
6. Runtime SBOM generation and schema/CVE scan evidence where the scanner is available.
7. Dirty-worktree review proving only workflow-owned files are staged.

The workflow must stop rather than implement around an unresolved security veto, a simulation result at or below 95%, unsafe durable-data ambiguity, failure to create the isolated worktree, or any action requiring an unapproved restart.

## Planning reviews and baseline evidence

- Python 3.11/PySide6 baseline command: `PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit tests/integration -rs`.
- Baseline result: `1228 passed, 1 failed, 88 skipped in 113.16s`. The one failure is `TestFindFreecadCmd::test_accepts_capitalised_binary_name`; all 88 integration skips report that the FreeCAD AppImage is unavailable. This is evidence, not an accepted green gate.
- Implementation simulation iteration 1 scored 93.6% and blocked source edits. Its four corrections—independent process-wide GUI control, explicit preflight status contract, numeric post-validation bind, and read-only custom token paths—were incorporated.
- Implementation simulation iteration 2 scored C1 97%, C2 97%, C3 97%, C4 96%, C5 96%, aggregate 96.6%: `PROCEED` to ID/TD definition.
- The first `agy` call produced no review because its headless sandbox denied the command permission. The review was rerun by embedding the already-inspected dossier content, with tool access disabled.
- Final `agy` scores: correctness 98%, completeness 98%, security 99%, testability 98%, rollback 97%, consistency 99%; verdict `PASS`, zero blocking defects.
- Accepted review feedback: the four simulation corrections above. Rejected feedback: none; the final reviewer proposed no additional changes.

## Completion artifacts

- Updated ARD/TRD/ID/PD/TD with final implementation truth.
- Exactly one open-item report under `docs/openitem/` with three High, three Medium and three Low measures.
- Session Transfer Protocol under `docs/sessions/`.
- Development Diary under `docs/diaries/`, respecting the 1000-line/version rule.
- HTML project/security manual under `docs/manuals/`.
- Runtime inventory/SBOM instructions and worktree validation report.
- Focused commit, pushed branch and PR when credentials/network allow; no merge.

## Execution result — 2026-09-04

Phases 0–6 were executed in the planned Quick-Win-First order in the isolated
worktree. Each production slice followed observed RED, minimal GREEN,
regression and independent review. Review HOLDs in Phase B/C/D/E/F were
resolved rather than waived. Final code evidence is 1,556 unit tests with zero
skips/failures and 97% changed-line branch coverage; final Phase-F architecture
and simulation scores are 97% and 97.6%.

Documentation is complete. Git commit/push/PR, merge and release have not been
performed because the authoritative master gate still requires external
FreeCAD/host/network evidence. The STP is the continuation authority.
