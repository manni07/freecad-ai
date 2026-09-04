# Test Dossier: Security Remediation

## Control record

- Scope: SEC-01 through SEC-07 on base `15774022a1c981335135d95928bd6cb4f7ba0431`.
- Workflow: TCCode with Agent Workflow v4 thorough/critical, fixed team size 4.
- Worktree: `/Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation`.
- Baseline in Python 3.11 with PySide6: `1228 passed, 1 failed, 88 skipped in 113.16s`. The failure is `TestFindFreecadCmd::test_accepts_capitalised_binary_name`; integration skips are caused by the unavailable FreeCAD AppImage.
- Security target: every selected focused slice passes 100%; changed-line coverage exceeds 90%, with 100% targeted for pure policy/parser modules. No new skip or xfail may hide a failure.
- All filesystem/config tests use a temporary `FREECAD_AI_CONFIG_DIR`; no test reads or migrates the real user profile.
- No test restarts or reboots FreeCAD, a server, or a computer. A newly created in-test server/subprocess is stopped only by its owning fixture.

## Fixtures and evidence rules

- `tmp_config_dir`: reloads config modules after setting a temporary root and asserts every managed path stays below it.
- `registry_factory`: constructs GUI-locked, GUI-armed, HTTP and STDIO registries.
- `confirmation_spy`: supplies explicit Yes/No answers and captures the exact reviewed code without mocking the final observable result.
- `agents_project`: creates a canonical root, nested includes, outside targets and controlled symlinks.
- `running_mcp_server`: ephemeral loopback port and isolated token; teardown owns only the server it created.
- `fake_param_store`: records write ordering and injects failures without touching FreeCAD preferences.
- `insecure_config_tree`: deliberate `0755`/`0644` paths within a temporary directory.
- `fake_runtime`: complete FreeCAD/Python/PySide/Qt version structure.

Every test name states the production bug it catches. Expected values are hand-derived literals. Mocks stop only at unavailable external or GUI boundaries; assertions target registry contents, dispatch counts, status codes, persisted bytes, file modes and user-visible outcomes.

## Phase A — SEC-04/05 and immutable HTTP omission

Focused files: `test_llm_tls.py`, `test_executor.py`, `test_code_review_dialog.py`, `test_registry.py`, `test_mcp_gui_server.py`, `test_mcp_server.py`.

At least these cases are required:

1. Default SSL-context failure leaves local HTTP usable.
2. HTTPS POST fails before `urlopen` when no verified context exists.
3. HTTPS stream fails before `urlopen` under the same condition.
4. `_create_unverified_context` is never invoked.
5. TLS errors omit API keys, Authorization values and URL queries.
6. Preflight uses a private `0700` directory and `0600` regular files.
7. Concurrent preflights use distinct paths and cannot follow an injected symlink.
8. Success, timeout, malformed result and exception paths leave no artifacts.
9. Missing FreeCADCmd is `UNAVAILABLE`; harness failure is `ERROR`; unsafe code is `REJECTED`; only complete validation is `PASSED`.
10. `REJECTED` is never overridable; `UNAVAILABLE`/`ERROR` require the GUI-only second warning.
11. `exclude_names` blocks built-ins, user tools, MCP tools and extras with the same name.
12. HTTP `tools/list` omits `execute_code` and a direct call returns unknown tool; STDIO still lists it.
13. FreeCAD command discovery returns the real case-preserving `FreeCADCmd` path rather than constructing a lower-case sibling; this closes the sole Python-3.11/PySide6 baseline failure.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_llm_tls.py tests/unit/test_executor.py tests/unit/test_code_review_dialog.py tests/unit/test_registry.py tests/unit/test_mcp_gui_server.py tests/unit/test_mcp_server.py
```

Expected evidence: exit 0, no selected skip, no production `mktemp` or `_create_unverified_context`, and cleanup assertions for every failure branch.

## Phase B — SEC-01 GUI capability and per-call approval

Focused files: `test_code_execution_access.py`, `test_chat_widget_code_access.py`, `test_tool_routing.py`, `test_system_prompt.py`.

Required cases:

1. Process singleton starts disarmed.
2. Arm/disarm changes only in-memory state and is absent from serialized config.
3. New Chat and dock recreation preserve the process state; a fresh process starts locked.
4. Dangerous Mode never arms code access, and code access never changes Dangerous Mode.
5. Default GUI schema and prompt omit `execute_code` and its recommendations.
6. Armed GUI schema and prompt expose the capability consistently.
7. Reranker pins cannot restore a filtered name.
8. A stale/fabricated call after disarm never reaches the registry handler.
9. Dialog Cancel returns rejection and performs no document mutation.
10. Dialog approval executes the reviewed bytes exactly once.
11. A second call requires a fresh confirmation; denial terminates the current call without retry spam.
12. `auto_execute` cannot bypass review for either tool calls or generated raw code; manual Plan execution remains available.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_code_execution_access.py tests/unit/test_chat_widget_code_access.py tests/unit/test_tool_routing.py tests/unit/test_system_prompt.py
```

Expected evidence: exit 0, handler count zero for every denial and exactly one for each approval.

## Phase C — SEC-02 instruction containment and trust

Focused files: `test_agents_md.py`, `test_project_instruction_trust.py`, `test_system_prompt.py`.

Required cases:

1. Absolute include is rejected.
2. Parent traversal and sibling-prefix tricks are rejected.
3. Symlink escape and non-regular target are rejected.
4. Cycles and depth above five reject the whole bundle.
5. Per-file size above 64 KiB and aggregate size above 256 KiB reject the whole bundle.
6. NUL paths and invalid UTF-8 fail closed.
7. Fingerprint is deterministic and changes when any included raw byte or manifest path changes.
8. Variable substitution does not alter the approval fingerprint.
9. First use previews; unchanged `allow` does not; changed content previews again.
10. `ignore` sends no project content and remains scoped to the exact fingerprint.
11. Cancel preserves input and conversation state.
12. Disk changes after approval cannot change the in-memory request snapshot; unapproved bytes never reach the provider.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_agents_md.py tests/unit/test_project_instruction_trust.py tests/unit/test_system_prompt.py
```

Expected evidence: all hostile paths raise the documented load error and no partial content is returned.

## Phase D — SEC-06 secure persistence, migration and logs

Focused files: `test_secure_storage.py`, `test_config.py`, `test_conversation.py`, `test_session_logs.py`.

Required cases:

1. New managed directories/files use `0700`/`0600` on POSIX.
2. Existing overly broad managed modes are tightened idempotently.
3. Directory and target symlinks are rejected.
4. Atomic replace preserves the previous file on write, fsync or replace failure.
5. Parent directory is fsynced after a successful POSIX replacement.
6. Literal provider and reranker secrets are written and read back before config changes.
7. ParamGet is updated only after candidate config read-back; every injected failure preserves the legacy literal.
8. Existing `file:` and `cmd:` references remain unchanged.
9. Conflicting destination content creates a unique file and overwrites nothing.
10. Metadata logs omit arguments, results and messages while retaining name/success/duration/turn/error class.
11. Full opt-in recursively redacts known keys and exact configured secret values without deleting ordinary content.
12. Conversations stay complete but private; migration changes neither retention values nor file counts.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_secure_storage.py tests/unit/test_config.py tests/unit/test_conversation.py tests/unit/test_session_logs.py
```

Expected evidence: exit 0, exact modes on POSIX, no real config paths, no deleted files, and old values retained for every injected failure.

## Phase E — SEC-03 authenticated private-network MCP

Focused files: `test_mcp_token.py`, `test_mcp_auth.py`, `test_mcp_gui_server.py`, `test_mcp_streamable_server.py`, `test_mcp_sse_transport.py`, `test_initgui_commands.py`.

Required cases:

1. Managed token creation is exclusive, `0600`, high entropy and idempotent.
2. Default-path symlink/conflict fails closed.
3. A custom token path is never created, chmodded, replaced or truncated.
4. Missing, symlinked, non-regular, wrong-owner, broad-mode, empty or malformed custom token fails before bind/backend.
5. Missing, wrong, duplicate and malformed Bearer returns 401 with required headers on every verb/path.
6. Auth occurs before body parsing and handler dispatch; oversized unauthenticated bodies do no MCP work.
7. Valid token plus invalid Host/Origin returns 403; failures never leak token/header values.
8. Loopback and each allowed private/link-local/ULA family pass; wildcard, unspecified, multicast and public addresses fail.
9. Hostname lookup occurs once; mixed or multiple unique answers fail; transport binds only the validated numeric address.
10. Token bucket allows burst 20, refills at 60/minute and returns 429 with `Retry-After` when empty.
11. More than eight active requests are rejected before worker creation with 503; slots release in `finally` after errors.
12. Streamable HTTP and legacy SSE succeed with auth; SSE occupies a slot; HTTP still omits `execute_code` and retains `run_macro`.
13. Token rotation atomically invalidates the old token; concurrent requests use a consistent token snapshot.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_mcp_token.py tests/unit/test_mcp_auth.py tests/unit/test_mcp_gui_server.py tests/unit/test_mcp_streamable_server.py tests/unit/test_mcp_sse_transport.py tests/unit/test_initgui_commands.py
```

Expected evidence: exit 0, live loopback positive/negative requests within fixture ownership, zero dispatch on every rejected request, and no real LAN bind.

## Phase F — SEC-07 metadata, packaging and SBOM

Focused files: `test_release_metadata.py`, `test_runtime_inventory.py`.

Required cases:

1. Package and `package.xml` expose `0.23.1-alpha`; `pyproject.toml` exposes equivalent `0.23.1a0`.
2. All policy and packaging sources require Python `>=3.11`.
3. Runtime dependencies are explicitly empty; host-provided FreeCAD/PySide/Qt are documented separately.
4. Setuptools discovery contains only `freecad_ai*`; editable installation metadata generation succeeds.
5. Supported-runtime policy has FreeCAD minimum `1.0` and no unverified tested versions.
6. Runtime collector finds FreeCAD, Python, active PySide binding and Qt versions.
7. CycloneDX output is 1.5 JSON with the five required components and stable dependency references.
8. Missing any required version exits non-zero and writes no apparently complete BOM.
9. Output contains no username, hostname, executable/config path, environment value or secret.
10. Explicit output rejects symlinks and uses atomic private writes.
11. MCP client version imports the package version rather than maintaining a divergent literal.
12. CI deterministic slice contains no assertion that zero PyPI runtime dependencies proves the host vulnerability-free.

Commands:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_release_metadata.py tests/unit/test_runtime_inventory.py
.venv/bin/python -m pip install --no-deps -e .
```

Expected evidence: both commands exit 0; generated BOM validates structurally and incomplete runtime collection exits non-zero.

## Regression, coverage, static and runtime gates

After every green phase, rerun that phase plus all previous security phases. Final deterministic commands:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit -rs
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider --cov=freecad_ai --cov-branch --cov-report=xml:build/security-coverage.xml -o addopts='' tests/unit
.venv/bin/diff-cover build/security-coverage.xml --compare-branch=15774022a1c981335135d95928bd6cb4f7ba0431 --fail-under=90
.venv/bin/ruff check freecad_ai tests
.venv/bin/bandit -r freecad_ai -ll -ii
requirement_file="$(mktemp)"
.venv/bin/pip-audit --strict --disable-pip --no-deps -r "$requirement_file"
trash "$requirement_file"
git diff --check
```

The full integration command is:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' -m integration tests/integration -rs
```

The release gate remains `HOLD` if FreeCAD is unavailable, any selected test is skipped/failing, changed-line coverage is at most 90%, a Critical/High finding remains unaccepted, or the actual host SBOM cannot be generated and scanned. The Session Transfer Protocol must record the exact blocked command. Private-LAN testing requires a separately confirmed isolated network; it is not inferred from permission to run loopback fixtures.

The full-unit command is expected to become green in Phase A by fixing the case-preserving FreeCAD command lookup. The baseline test is never ignored, quarantined, skipped, xfailed, or removed.

## Mandatory Red–Green evidence ledger

This dossier is approved before test implementation, so new security tests do not yet exist and cannot honestly have RED output. During implementation, each phase must append its actual evidence here before the related production patch may be retained:

| Phase | RED revision/state | RED command and intended failure | GREEN revision/state | GREEN command/result | Regression result |
|---|---|---|---|---|---|
| Baseline | `15774022a1c981335135d95928bd6cb4f7ba0431` | Full unit/integration command: case-preserving FreeCADCmd assertion fails; 88 FreeCAD-runtime cases skip | pending Phase A | pending | pending |
| A | Test-only working-tree state, 2026-09-04 | Initial focused command exited 1: 10 failed, 113 passed. After cross-review expansion it exited 1: 1 failed, 138 passed; the remaining defect was `result.json` mode `0644` instead of `0600`. | Final Phase-A production state, 2026-09-04 | Exact focused command above exited 0: 139 passed in 5.38s, no skips. | Exact full command `PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit -rs` exited 0: 1254 passed in 103.18s, no skips. Final cross-review `PASS`. |
| B | Test-only working-tree state, 2026-09-04 | Exact Phase-B command exited 1: 13 failed, 9 passed in 0.16s. Intended REDs: missing process-wide `CodeExecutionAccess`; absent dedicated/synchronized GUI toggle; no execution-edge recheck/review path; `auto_execute` still bypasses review; GUI registry lacks capability filtering and reranker intersection; `build_system_prompt` lacks `code_tool_enabled` parity. Corrective RED later exited 1: 2 failed, 29 passed because denial retried the provider and dispatched a later batch tool. | Final S4 production state with terminal denial, 2026-09-04 | Exact focused command exits 0: 31 passed in 0.15s. Independent cross-review rerun exits 0: 31 passed in 0.18s. | Exact full-unit command exits 0: 1277 passed in 89.07s, no skips. Cancel emits `terminal=True`; the worker records one result for the rejected call plus an explicit skipped result for every remaining call, preserving ordered OpenAI tool-call/result protocol and UI trace while dispatching neither the later tool nor another provider turn. Ordinary tool failure remains non-terminal. Phase-B security/test and regression gates `PASS`. |
| C | Test-only working-tree state, 2026-09-04 | Initial exact Phase-C command exited 1: 21 failed, 28 passed in 0.36s. After S5/S6 and cross-review expansion, the exact command exited 1: 1 failed, 64 passed in 0.18s; unsafe resolver failure cleared input and continued the send path instead of aborting locally. | Final S5/S6 state with fail-closed resolver abort, 2026-09-04 | Root exact focus exited 0: 65 passed in 0.18s. Independent final cross-review rerun exited 0: 65 passed in 0.20s. | Root exact full-unit command exited 0: 1315 passed in 104.06s, no skips. Phase-C security/test and regression gates `PASS`. |
| D | Test-only working-tree state, 2026-09-04 | Exact Phase-D command exited 1: 17 failed, 138 passed in 0.46s, no skips. Intended REDs: missing S7 secure-storage module and private/atomic/migration/redaction primitives; missing metadata-log default and literal provider/reranker migration; conversations/logs remain `0644`; metadata logs expose assistant text, arguments and results; full logs expose configured secrets. | Stabilized S7/S8 working-tree state plus isolated test fixture, 2026-09-04 | Root exact focused command exited 0: 170 passed in 0.48s, no skips; independent run: 170 passed in 0.42s, no skips. | Root full `tests/unit -rs`: 1348 passed in 103.91s, no skips; critical Ruff and `git diff --check` passed; real-config metadata fingerprint unchanged after both post-fix runs |
| E | Test-only working-tree state, 2026-09-04 | Exact Phase-E command exited 1: 135 failed, 37 passed in 5.76s, no skips. Intended REDs: absent S9 token resolution/provisioning; absent S10 private one-shot bind resolution; HTTP transport rejects the required Bearer/rate/burst/concurrency arguments and therefore lacks every-request authentication, token-bucket, pre-thread slot and rotation controls. Expanded adversarial run later exposed three genuine residual REDs: mapped-loopback and scoped-link-local binds were accepted, and InitGui reflected token-bearing exception text. | Stabilized S9/S10 working-tree state, 2026-09-04 | Independent adversarial focus exited 0: 191 passed in 47.60s, no skips; Root repeated the exact focus with 191 passed in 48.16s, no skips. | First full unit run: 1437 passed, 4 failed in 65.75s because the legacy SSE-client test fixture did not supply the newly mandatory Bearer token. Systematic root-cause analysis confirmed test-contract drift; a test-only fixture correction then passed 15/15 in 63.34s. Root final full unit run: 1441 passed in 127.38s, no skips. Architecture and adversarial reviews, critical Ruff and `git diff --check` passed. Real-config metadata hash stayed `a68d8516d2919afa16a474a53d960a724125e44d7421545c14f5ba9f508e98ba`; no real token/secrets path or non-fixture LAN listener was created. FreeCAD GUI/runtime acceptance remains unavailable and unverified. |
| F | Test-only working-tree state, 2026-09-04 | Root initial exact Phase-F command exited 1: 28 failed in 0.47s, no skips/errors. Two corrective RED rounds then exited 1 with 12/26 and 7/48 because parent validation, version grammar, package discovery, CI scope, pinned `dir_fd` operations, temp-inode identity and parent-swap resistance were incomplete. Every probe was mocked or temporary. | Final S11/S12 state with pinned POSIX parent descriptors and raw strict version grammar, 2026-09-04 | Final exact focus exited 0: 55 passed, no skips. Synthetic CycloneDX 1.5 validation passed with exactly five components and five dependency entries. Independent architecture review 97% PASS; test simulation 97.6% PASS. Editable `--no-deps` install reported `0.23.1a0`, no dependencies and only `freecad_ai`. | Final plain unit run: 1556 passed in 113.68s; final coverage run: 1556 passed in 131.40s; neither skipped. Diff-cover: 97% over 862 changed lines, 24 missing. Critical Ruff PASS; full Ruff intentionally non-green at 561 legacy/quality findings, with four new broad exception boundaries retained for fail-closed rollback/error sanitization. Bandit: 3 High/7 Medium/89 Low with exact contextual triage and no `#nosec`. Scoped empty-declaration pip-audit PASS; integration selected 88 tests but all skipped because FreeCAD AppImage is absent. Actual-host SBOM/CVE and FreeCAD GUI/integration remain HOLD. |

The raw command `.venv/bin/pip-audit --strict` is not authoritative for this
editable checkout: it attempts to resolve the local alpha project as a PyPI
distribution and fails because that distribution is not published. The scoped
empty-requirement command above is the declared-dependency check. Neither form
audits host-provided FreeCAD, PySide or Qt; only an actual-runtime BOM plus an
external vulnerability scan can close that gate.

An implementation phase is `HOLD` if its test-only patch was not observed failing for the intended missing behavior, or if its final GREEN and previous-phase regression outputs are absent. These fields are execution evidence, not values to fabricate during test planning.

Phase-A final cross-review, 2026-09-04: cleanup after timeout, malformed output and harness exception; all four preflight statuses; rejection despite `allow_unvalidated=True`; concurrent unique workspaces; injected-symlink refusal; and `0600` modes for script, document copy and pre-created result are bound by tests. Absence searches found no production `_create_unverified_context` or `tempfile.mktemp`, exactly one `allow_unvalidated=True` assignment in the GUI review dialog, `_check_ssl` at both HTTP request edges, and immutable HTTP `exclude_names={"execute_code"}` while compatibility tests retain STDIO `execute_code` and HTTP `run_macro`. Phase A is `GREEN`; no Phase-A security/test rest gap remains.

Phase-C RED, 2026-09-04: the exact focused command collected 49 tests without import, fixture, Qt, syntax, or collection errors. The 21 production-behavior failures bind absolute, traversal, sibling-prefix, symlink and non-regular includes; cycles and depth above five; 64 KiB per-file and 256 KiB aggregate limits; NUL and invalid UTF-8; deterministic raw-byte/manifest fingerprints and substitution neutrality; config-AGENTS trust scoped to the exact fingerprint; preview decision/order contracts; and the in-memory approved-or-empty snapshot/provider boundary. Existing explicit-approved-snapshot prompt behavior remains green. Phase C stays `HOLD` until S5/S6 GREEN and regression evidence exist.

Phase-C corrective cross-review, 2026-09-04: behavior tests now cover first-use `allow` and `ignore`, unchanged `allow` without a dialog, changed-fingerprint re-preview, Cancel without persistence or snapshot replacement, exact in-memory content after a disk change, invalid trust-record shapes, main-source symlink/non-regular rejection, canonical parent-root selection, and config fallback. The exact expanded focus collected 65 tests without skips or infrastructure errors and exited 1 with 1 failed, 64 passed in 0.18s. The sole genuine production RED is resolver failure: `_prepare_project_instructions` catches `InstructionLoadError` and returns `(text, None)`, so `_send_message` clears the input and continues rather than locally aborting before user state, attachments, conversation, and provider dispatch. Phase C remains `HOLD`; after correcting this path, rerun the exact focus and full unit suite.

Phase-C final cross-review, 2026-09-04: resolver failure now returns `None` while preserving the prior request snapshot, input, attachments and conversation and performs no later dispatch. Reads are bounded to 64 KiB plus one byte per file and 256 KiB aggregate; canonical containment, symlink/non-regular rejection and strict UTF-8 remain fail-closed. Fingerprints length-frame the version, encounter-order relative manifest paths and pre-substitution raw bytes; trust requires the exact canonical root/source/fingerprint, lowercase SHA-256 form, `allow|ignore`, and a string timestamp. Absence review found no caller of the legacy `_search_directory_chain`, `_load_from_directory`, or `_resolve_includes` path outside their compatibility definitions; active GUI discovery uses `discover_instruction_bundle`, and omitted non-GUI prompt loading passes through the trust-validating `load_agents_md`. Dialog review confirms source/root/manifest/fingerprint/content preview, two read-only text widgets, and distinct allow/ignore/cancel actions. `_continue_send` captures the request snapshot before prompt construction, passes it explicitly on both tool and non-tool paths, and retries reuse the same snapshot. Phase C is `PASS`.

Phase-D RED, 2026-09-04: the exact focused command collected 155 tests without import, fixture, Qt, syntax, collection errors or skips and exited 1 with 17 failed, 138 passed in 0.46s. Tests use only pytest temporary directories and fake ParamGet state. The failures bind POSIX `0700`/`0600` creation and tightening; directory/target symlink rejection; previous-file preservation across write/fsync/replace failure and parent fsync; lossless verified literal migration, untouched `file:`/`cmd:` references and collision-safe destinations; exact provider/reranker migration ordering before JSON/ParamGet mutation with retention inventory preserved; recursive known-key and exact-secret redaction without ordinary-data loss; complete `0600` conversations; metadata-only name/success/duration/turn/error-class logs; and full opt-in recursive redaction. Phase D remains `HOLD` until S7/S8 GREEN and full regression evidence exist.

Phase-D adversarial GREEN, 2026-09-04: the expanded exact focused command exited 0 with 170 passed in 0.42s and no skips; Root repeated it after the final isolation repair with 170 passed in 0.48s and no skips. Added failure-injection and invariant coverage proves pre-commit write/file-fsync/replace failures preserve the exact prior file and leave no temporary or secret orphans; a failure of the second parent-directory fsync is surfaced while the target remains one complete old or new value, explicitly retaining the accepted post-commit durability uncertainty. Tests also bind symlink-ancestor rejection and managed-path hardening; provider-then-reranker, candidate-save, final-readback and ParamGet rollback; final readback before ParamGet mutation; retention inventories above configured caps; private atomic config and conversation writes; canonical `duration` mapping plus real-shaped failure `error_class`; and metadata/full redaction without resolving `file:` or executing `cmd:` references. The full Unit regression then passed 1348 tests in 103.91 seconds with no skips; critical Ruff and `git diff --check` also passed.

Phase-D isolation correction, 2026-09-04: the first full run exposed that the pre-existing `tmp_config_dir` fixture redirected only config, conversation, skill and log paths. Because S8 now manages additional directories, that gap created one empty `secrets/` directory under the real FreeCAD-AI configuration. Root verified it was a newly created, empty, non-symlink directory and removed that test artifact. `tests/conftest.py` now forces configuration resolution during collection into a process-private canonical temporary directory and redirects every managed path, including tools, hooks, backups, secrets and the MCP token path. A metadata-only fingerprint of the real configuration tree was identical before and after both corrected test runs (`9a18ee883f9e1341b645d07ac06c7e42a780b7315051a9c67af67f2265a6c981`), and the unintended directory remained absent. Phase-D test and architecture reviews are `PASS`; the master end-gate remains authoritative for promotion to Phase E.

Phase-E RED, 2026-09-04: the exact focused command collected 172 tests and exited 1 with 135 failed, 37 passed in 5.76s, without skips, collection, import, fixture, syntax or Qt failures. All failures are genuine missing S9/S10 production behavior: `resolve_token_file`/`load_or_provision_token` and `resolve_private_bind` do not exist, while `HTTPServerTransport` rejects the required in-memory `bearer_token`, rate, burst and concurrency parameters. The test-only delta binds exclusive high-entropy managed provisioning and strict custom-path non-mutation; startup ordering before bind/backend; every verb/path including unknown methods; duplicate/malformed/wrong Bearer and no-dispatch/body-parse precedence; Host/Origin rejection without secret reflection; one DNS lookup and numeric private-only results; a deterministic global 60/minute burst-20 bucket; eight pre-thread SSE slots plus finally release; authenticated Streamable and legacy SSE compatibility; HTTP `execute_code` omission with `run_macro` retained; and atomic token rotation with a consistent in-flight snapshot. All token/config paths are temporary and every socket is fixture-owned loopback. Phase E remains `HOLD` pending S9/S10 GREEN and regression evidence.

Phase-E adversarial expansion and final GREEN, 2026-09-04: tests now decode base64url token material to require at least 32 bytes and observe `token_urlsafe(32)`; cover managed-mode tightening without inode/content replacement; preserve custom-token inode, bytes, mode and mtime while forbidding truncate/unlink/rename; and inject a token swap between `lstat` and `open` to require `O_NOFOLLOW`, same-FD `fstat`, and inode/device equality. HTTP tests isolate duplicate Authorization with exactly one Host, accept lowercase Bearer, pin Host-before-auth precedence, prove rejected Host/auth traffic does not consume the global cross-route bucket, count that no ninth request thread is created, and bind permit release after thread-start failure, handler error and SSE disconnect with bounded waits. Controller tests carry one DNS result through numeric host/address family into the fake transport and keep token/bind failures before backend creation. CLI/InitGui tests require fail-closed config loading and token-free console/dialog errors; reserved, CGNAT, site-local, IPv4-mapped and scoped IPv6 forms are rejected. The first expanded run had three genuine residual production failures plus stale fixture failures; after production correction and fixture alignment to the authenticated `cfg`/token-path controller contract, the exact 191-test focus exited 0 in 47.60s with no skips, and Root independently repeated it with 191 passed in 48.16s. The first full-unit regression exposed four stale SSE-client fixture failures: those tests instantiated the now-authenticated server and client without the mandatory test Bearer token. Systematic root-cause analysis traced the failures to that test boundary, not to a production bypass; the minimal test-only correction passed all 15 tests in that file. Root then passed the full unit suite with 1441 tests in 127.38 seconds and no skips. Architecture and adversarial reviews, critical Ruff and `git diff --check` passed. The real configuration metadata hash remained `a68d8516d2919afa16a474a53d960a724125e44d7421545c14f5ba9f508e98ba` before and after, no real token/secrets path was created, and every test listener was fixture-owned loopback. Phase E is technically `PASS`; GUI/runtime acceptance inside FreeCAD is unavailable and remains explicitly unverified for the final release gate.

## GUI acceptance in a supported FreeCAD process

Manual or automated Qt/FreeCAD evidence must demonstrate: default locked toggle; warning defaults No; arm makes schema available; Cancel mutates no document; approval mutates only the disposable test document once; every second call prompts again; New Chat/dock recreation preserves the session state; a new process is locked; AGENTS preview and changed-fingerprint reapproval; authenticated loopback structured tool succeeds and unauthenticated request has no effect. If the supported process is unavailable, every item stays explicitly unverified.

## Accepted residual regression assertions

Tests deliberately preserve and document these boundaries rather than silently treating them as fixes: STDIO exposes `execute_code`; authenticated HTTP exposes `run_macro`; private-LAN bearer traffic has no transport confidentiality; explicitly approved Python has the FreeCAD user's OS privileges; Windows mode bits are not claimed as full ACL enforcement.

## Independent review record

- Local test simulation: T1 98%, T2 98%, T3 97%, T4 97%, T5 98%, aggregate 97.6%, `PROCEED`.
- First `agy` review: `HOLD` because coverage used a partial test selection, RED evidence lacked a binding execution ledger, and the known baseline failure was not assigned to a remediation slice.
- Corrections accepted: coverage now runs all `tests/unit`; Phase A fixes the case-preserving `FreeCADCmd` lookup without ignore/skip/xfail; the mandatory ledger blocks production retention until real RED, GREEN and regression outputs exist.
- Second `agy` review: coverage 99%, isolation 99%, assertions 98%, maintainability 98%, risk governance 99%; `PASS`, no blockers.
- Rejected review feedback: none. The prospective dossier intentionally does not fabricate RED output before test implementation.
