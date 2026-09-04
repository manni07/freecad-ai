# Implementation Dossier: Security Remediation

## Control record and hard gates

- Workflow: TCCode PD→ID conversion inside Agent Workflow v4 `thorough`, quality `critical`, fixed team size 4.
- Worktree: `/Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation`
- Branch/base: `agent-workflow/20260904-115556-security-remediation` at `15774022a1c981335135d95928bd6cb4f7ba0431`.
- Source audit: `docs/audits/security-audit-2026-09-04.html`, SHA-256 `d41a1861a11a366a07d4f966185fad8d8b2ae7c7cf87bf5f2a9c3957c43e1ad0`.
- Binding inputs: `ARD_security_remediation_2026-09-04.md`, `TRD_security_remediation_2026-09-04.md`, `PD_security_remediation_2026-09-04.md`.
- Never restart/reboot FreeCAD, a computer, or a server without explicit user confirmation. Never revert unrelated work or merge automatically.
- Stop before the next phase if a security-focused test is skipped/failing, a simulation score is at or below 95%, a durable-data migration cannot prove preservation, or a fail-closed path gains a fallback.

## Dependency graph

```text
S0 tests/fixtures
├── S1 TLS ───────────────┐
├── S2 temp/preflight ────┼── S4 GUI raw-code gate
├── S3 registry policy ───┘
├── S5 instruction bundle ── S6 GUI project trust
├── S7 secure storage ────── S8 config/secret/log migration ── S9 HTTP token file
├── S3 registry policy ─────────────────────────────────────── S10 HTTP auth/bind/limits
└── S11 version policy ───── S12 runtime inventory/SBOM ───── S13 CI/docs/final gates
```

All implementation slices follow red → minimal green → focused regression. Tests are never weakened to accept insecure behavior.

## S0 — Isolated fixtures and baseline ledger

### Files and symbols

- Update `tests/conftest.py::tmp_config_dir` to redirect every managed path, including tools, hooks, backups, secrets, token, and trust config.
- Add reusable fake ParamGet and mock-FreeCAD fixtures only if two or more slices need them.
- Record the existing full-suite baseline in the TD, not in production code.

### TDD red

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_config.py tests/unit/test_conversation.py
```

Add a fixture test proving no resolved managed path begins with the real `CONFIG_DIR` after fixture activation. It must initially fail for the new constants.

### Minimal green

Patch all config module path constants in the fixture. Do not create a new fixture framework or touch real user state.

### Checkpoint

Report exact baseline counts and temporary paths. No subsequent persistence test may run without this isolation.

## S1 — SEC-04 verified provider TLS

### Files and interfaces

- `freecad_ai/llm/client.py::LLMClient.__init__`: initialize `_ssl_ctx` and `_ssl_context_error`.
- `LLMClient._check_ssl(url)`: reject HTTPS when `_HAS_SSL` is false or `_ssl_context_error` is not `None`.
- Existing `_http_post` and `_http_stream` remain the only request edges and keep calling `_check_ssl` first.
- Extend `tests/unit/test_llm_client.py` or add `tests/unit/test_llm_tls.py`.

### TDD red

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_llm_tls.py
```

Tests patch `ssl.create_default_context` to raise and assert: constructor itself still supports local HTTP; HTTPS post and stream raise `LLMError`; `_create_unverified_context` is never called; error text contains no API key, Authorization header, or query string.

### Minimal green

Catch context initialization failure only to defer a clear failure until an HTTPS request. Set no substitute context. Preserve local Ollama HTTP behavior and current retry behavior after a verified connection exists.

### Failure/rollback

Certificate-store failure is terminal for HTTPS and visible to the UI. Rollback must never restore the unverified fallback.

## S2 — SEC-05 private preflight and explicit unvalidated path

### Types and exact state contract

Add to `freecad_ai/core/executor.py`:

```python
class PreflightStatus(str, Enum):
    PASSED = "passed"
    REJECTED = "rejected"
    UNAVAILABLE = "unavailable"
    ERROR = "error"

@dataclass(frozen=True)
class PreflightResult:
    status: PreflightStatus
    message: str
    code: str

    @property
    def passed(self) -> bool:
        return self.status is PreflightStatus.PASSED
```

- `_sandbox_test(...) -> PreflightResult`; static validation is converted to `REJECTED` by `validate_code(...) -> PreflightResult`.
- Missing FreeCADCmd returns `UNAVAILABLE`; harness/setup/missing-result failures return `ERROR`; unsafe code or subprocess validation failure returns `REJECTED`; only a complete successful result returns `PASSED`.
- `execute_code(..., allow_unvalidated: bool = False)` runs live code only for `PASSED`, except the one GUI path below. `REJECTED` is never overridable.
- Existing `ExecutionResult` remains the live-execution result type.

### Private files

- `_sandbox_test` creates one `TemporaryDirectory(prefix="freecad-ai-")`, verifies/chmods it to `0700`, and uses fixed `preflight.py`/`result.json` children.
- Create `preflight.py` using `os.open(path, O_WRONLY|O_CREAT|O_EXCL, 0o600)` and `os.fdopen`; result remains inside the private directory.
- Read and validate result before leaving the context. Cleanup is automatic for success, timeout, signal, malformed result, and exception.
- Keep the document-copy lifetime inside the same private directory; remove the separate global `mkstemp` copy.

### GUI-only override

- `CodeReviewDialog._check` renders all four statuses.
- For `UNAVAILABLE` or `ERROR`, the primary action label becomes “Execute without preflight”. Clicking it opens a second warning `QMessageBox` with default No. Only Yes calls `execute_code(code, allow_unvalidated=True)`.
- For `REJECTED`, Execute remains disabled; no override is shown.
- For `PASSED`, Execute calls normal `execute_code(code)`.
- No registry handler, MCP route, macro handler, hook, config field, or environment variable passes `allow_unvalidated=True`.
- The flag is an internal defense-in-depth contract, not an OS security boundary; tests verify every non-GUI immediate caller uses the default.

### TDD red

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_executor.py tests/unit/test_code_review_dialog.py
```

Add cases for all statuses, missing binary, malformed/missing result, private modes, cleanup, timeout, rejected-no-override, unavailable default denial, second warning No/Yes, and exactly one live call.

### Minimal green and compatibility

Adapt existing callers/tests from `ExecutionResult.success/stderr` to `PreflightResult.status/message`. Preserve live `ExecutionResult` shape. Dangerous Mode remains an explicit legacy bypass for its existing direct callers, but does not arm GUI LLM code access.

## S3 — SEC-01 immutable tool exposure policy

### Files and interfaces

- Extend `freecad_ai/tools/setup.py::create_default_registry(include_mcp=True, extra_tools=None, exclude_names=None)`.
- Normalize `exclude_names` once to `frozenset`; skip matching names before registering built-ins, user tools, upstream MCP tools, and extras.
- `freecad_ai/mcp/gui_server.py::_default_backend` always passes `exclude_names={"execute_code"}`.
- Do not add an environment or config override.

### TDD red

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_registry.py tests/unit/test_mcp_gui_server.py tests/unit/test_mcp_server.py
```

Add tests proving exclusion from all registration sources, HTTP `tools/list`, and direct HTTP-backend `tools/call`. A user tool named `execute_code` must not reintroduce the name.

### Minimal green

Implement the optional filter without changing `ToolRegistry` public schema methods. This is physical omission, not only schema filtering.

### Accepted compatibility

STDIO entrypoint continues using the unfiltered default registry. Authenticated HTTP retains `run_macro`.

## S4 — SEC-01 GUI session access, prompt parity, and per-call approval

### Files and exact control

- Add `freecad_ai/core/code_execution_access.py` with process-wide singleton `get_code_execution_access()` and `CodeExecutionAccess.active/arm/disarm`.
- Add `self.code_access_toggle = QCheckBox("Allow AI Python")` in `ChatDockWidget._build_ui`, immediately before the existing `self.danger_toggle` in the header.
- Connect only to `_on_code_access_toggled`; its default-No warning calls `CodeExecutionAccess.arm()` on Yes or restores unchecked state on No. Uncheck calls `disarm()`.
- `_update_code_access_toggle()` reads only `CodeExecutionAccess.active`; `_on_danger_toggled` and `_update_danger_banner` never read or write it. Conversely, code-access methods never read/write `DangerousMode`.
- The process singleton deliberately survives New Chat and dock recreation; it ends only on manual disarm or process exit. Dock construction synchronizes the checkbox from the singleton.

### Schema and execution data flow

1. `_continue_send` obtains the gate state on the GUI thread.
2. It calls `create_default_registry(..., exclude_names=set() if active else {"execute_code"})`.
3. Reranker candidates come from that filtered registry; pinned names are intersected with present names.
4. `build_system_prompt(..., code_tool_enabled=active)` conditionally excludes every `execute_code` recommendation/example.
5. `_LLMWorker` receives only the filtered schema/registry.
6. `_execute_tool_call` rechecks the current singleton. If disarmed, it returns failure without registry dispatch.
7. If armed, it opens `CodeReviewDialog` on the main thread. Cancel returns `Rejected by user`; execution returns the dialog's existing result. It never calls the registry handler afterward.
8. Every subsequent model call repeats steps 6–7.

`_handle_act_mode` always uses `CodeReviewDialog` for model-produced raw code, even when `cfg.auto_execute` is true. Manual Plan-mode Execute remains unchanged.

### TDD red

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_code_execution_access.py tests/unit/test_tool_routing.py tests/unit/test_chat_widget_code_access.py
```

Test initial state, arm/disarm, non-persistence, New Chat survival, dock synchronization, independence from Dangerous Mode in both directions, default/armed schema, reranker intersection, prompt parity, stale call, cancel, exactly-once, repeat confirmation, Stop result, and `auto_execute` non-bypass.

### Minimal green

Use the existing checkbox/dialog patterns. Do not create a generic authorization framework. Translate all new UI strings through the existing translation path.

## S5 — SEC-02 bounded instruction bundle

### Files and interfaces

Refactor `freecad_ai/extensions/agents_md.py` around:

```python
@dataclass(frozen=True)
class InstructionBundle:
    root: str
    source_path: str
    content: str
    fingerprint: str
    manifest: tuple[str, ...]

class InstructionLoadError(ValueError):
    pass

def discover_instruction_bundle() -> InstructionBundle | None: ...
def load_agents_md() -> str: ...  # trusted-current compatibility wrapper
```

### Resolver algorithm

1. Preserve current filename priority and maximum parent search.
2. The selected file's canonical containing directory is `root`; config fallback uses canonical `CONFIG_DIR`.
3. Read raw bytes, enforce 64 KiB per file, decode strict UTF-8, and track expanded total up to 256 KiB.
4. For each include, reject absolute/NUL paths; join against the including file's directory; realpath it; require `commonpath((root, target)) == root`; reject symlink/non-regular targets and cycles.
5. Maintain encounter-order root-relative manifest. Maximum include depth is five.
6. Fingerprint a version prefix plus length-framed root-relative paths/raw bytes before variable substitution.
7. Substitute variables into the already captured snapshot after fingerprint creation.
8. Any nested failure raises `InstructionLoadError`; return no partial bundle.

### TDD red

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_agents_md.py
```

Add absolute, traversal, sibling-prefix, symlink, non-regular, NUL, invalid UTF-8, cycle, depth, per-file/aggregate size, nested failure, deterministic fingerprint, included-file change, variable-stability, root-selection, and config-fallback cases.

### Minimal green

Keep the existing search helpers where safe, but make bundle discovery the source of truth. Do not silently convert resolver errors to comments.

## S6 — SEC-02 preview, trust store, and request snapshot

### Files and flow

- Add `AppConfig.project_instruction_trust: dict = field(default_factory=dict)`.
- Add `ChatDockWidget._prepare_project_instructions(text) -> tuple[str, InstructionBundle | None] | None` before `input_edit.clear()` and before `Conversation.add_user_message()`.
- Add a focused `ProjectInstructionsDialog` in `freecad_ai/ui/project_instructions_dialog.py` showing source, root, manifest, fingerprint, and read-only content.
- Actions: Trust and send → persist `allow`; Ignore this version → persist `ignore`; Cancel → return `None`, restore/preserve input, and do not mutate conversation.
- Cache the chosen exact bundle content as `_current_instruction_snapshot` for the current request, compaction continuation, and error retry.
- `build_system_prompt` receives that content explicitly. Non-GUI compatibility loading returns content only when the current fingerprint has an `allow` record; `ignore`, absent, malformed, or changed trust returns empty.

### Trust record validation

Require canonical-root string key, canonical source under root, `sha256:` plus 64 lowercase hex characters, decision exactly `allow|ignore`, and string timestamp. Invalid records are ignored fail-closed.

### TDD red

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_agents_md.py tests/unit/test_project_instruction_trust.py tests/unit/test_system_prompt.py
```

Assert first-use preview, unchanged allow no preview, include change re-preview, persisted ignore, cancel no conversation mutation, resolver failure local abort, and provider request containing only the approved snapshot even if disk changes afterward.

## S7 — SEC-06 secure-storage primitives

### File and APIs

Create `freecad_ai/secure_storage.py` with no import of `config.py`:

```python
def ensure_private_dir(path: str) -> None
def atomic_write_bytes(path: str, data: bytes, mode: int = 0o600) -> None
def atomic_write_json(path: str, value: object) -> None
def harden_managed_paths(directories: Iterable[str], files: Iterable[str]) -> list[str]
def redact_sensitive(value: object) -> object
def migrate_literal_secret(value: str, directory: str, stem: str) -> str
```

### Contracts

- Use `lstat`; reject symlink directory/file targets.
- Private dirs: create `0700`, chmod existing POSIX dirs, verify group/other bits are zero.
- Atomic writes: exclusive temporary sibling at `0600`, write/flush/fsync, `os.replace`, chmod/verify final, best-effort temp cleanup.
- Secret migration: leave empty, `file:`, and `cmd:` unchanged; write literal to a non-conflicting file, read back exact bytes, return only `file:<canonical-path>`.
- Recursive redaction replaces values whose case-insensitive keys contain `authorization`, `api_key`, `token`, `password`, or `secret`; it does not mutate input.
- Windows mode limitations return a warning for documentation; they are not claimed as ACL enforcement.

### TDD red

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_secure_storage.py
```

Test modes, atomicity, fsync/replace failure, symlink refusal, collision allocation, exact secret read-back, file/cmd preservation, recursive redaction, and no orphan on failure.

## S8 — SEC-06 config, secret, conversation, and log migration

### Config and ordering

- Add fields: `project_instruction_trust`, `session_log_content="metadata"`, `mcp_server_token_file=""`, `mcp_server_rate_limit_per_minute=60`, `mcp_server_rate_limit_burst=20`, `mcp_server_max_concurrent_requests=8`.
- Add `SECRETS_DIR` and managed token default path constants.
- `_ensure_dirs` delegates known paths to secure storage.
- `save_config`, `Conversation.save`, `_save_session_log`, and `_auto_save_log` use atomic private JSON.

Literal migration sequence in `load_config`:

1. Read JSON and apply ParamGet overrides without clearing anything.
2. For each literal provider/reranker secret, create a verified non-conflicting secret file.
3. Build a candidate config containing `file:` references.
4. Atomically save and read back the candidate config.
5. Only then mirror harmless references to ParamGet. If any step fails, retain old values and emit a visible warning.

`_write_to_param_store` never writes a literal key after successful migration. Existing `file:`/`cmd:` references are preserved. No pruning is triggered by migration.

### Logging

- Metadata mode records timestamp, tool name, success, elapsed, turn, and error class only.
- Full mode uses recursive redaction and an explicit settings warning; Authorization/token values remain redacted even in full mode.
- Conversations remain semantically complete but mode `0600`.

### TDD red

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_config.py tests/unit/test_conversation.py tests/unit/test_session_logs.py
```

Test default/roundtrip fields, literal migration, ParamGet ordering, collision, injected failures at every step, idempotence, no deletion/pruning, modes, metadata omissions, and full-mode redaction.

## S9 — SEC-03 token path and provisioning

### Exact path policy

In `freecad_ai/mcp/gui_server.py` add:

```python
def resolve_token_file(cfg=None) -> tuple[str, bool]:
    """Return (canonical_path, is_managed_default)."""

def load_or_provision_token(path: str, managed_default: bool) -> str: ...
```

- Empty config resolves to canonical `<CONFIG_DIR>/mcp_server.token`, `managed_default=True`.
- The managed default may be exclusively created with `secrets.token_urlsafe(32)`, trailing newline, mode `0600`, then read back and validated as at least 256 bits of URL-safe entropy.
- A non-empty custom path is `managed_default=False` and read-only: expand, canonicalize, `lstat`, require a non-symlink regular file owned by the current POSIX user with no group/other permission bits, and read it. Never create, replace, truncate, or chmod it.
- Missing, empty, malformed, unsafe, or unreadable custom token prevents server startup.
- Token content never enters config, URL, console, status bar, log, or exception.

### TDD red

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_mcp_gui_server.py tests/unit/test_mcp_token.py
```

Test managed create/mode/entropy/idempotence, default conflict/symlink, custom missing/read-only/no-chmod/no-create, custom unsafe permissions/owner, empty token, and error redaction.

## S10 — SEC-03 one-resolution private bind, Bearer, rate and concurrency

### Bind interface

Add immutable `ResolvedBindAddress(display_host, numeric_host, family, port)` and:

```python
def resolve_private_bind(host: str, port: int) -> ResolvedBindAddress: ...
```

- Normalize `localhost` directly to `127.0.0.1`/`AF_INET`.
- Numeric inputs use `inet_pton` and no DNS.
- Other hostnames call `getaddrinfo` exactly once. Deduplicate stream addresses; every result must be allowed private/link-local/ULA/loopback and there must be exactly one unique numeric address. Public, wildcard, unspecified, multicast, mixed, empty, or multi-address answers fail.
- Pass `numeric_host` and `family` to `HTTPServerTransport`; its HTTPServer subclass sets `address_family` before binding. It never receives the hostname for bind and therefore cannot resolve again.
- Keep `display_host` only for UI and allowed-Host derivation; URL may show the numeric address to be unambiguous.

### Authentication and admission

Extend `HTTPServerTransport.__init__` with required in-memory `bearer_token` and safe numeric limits. Invalid/zero limits use defaults with a warning, never unlimited.

Request order for every verb/path:

1. Pre-thread semaphore admission: max 8; otherwise raw minimal HTTP/1.0 503 with `Retry-After: 1`, then close.
2. Host and Origin: 403 on failure.
3. Exactly one Authorization header, two tokens split once, case-insensitive Bearer scheme, constant-time token compare: 401 with `WWW-Authenticate: Bearer realm="FreeCAD AI MCP"` and `Cache-Control: no-store`.
4. Locked monotonic token bucket: 429 with integer `Retry-After`.
5. Existing version/body parse and MCP dispatch exactly once.

Override `process_request` to acquire before worker creation and `process_request_thread` to release in `finally`. Authentication code never logs header values. SSE occupies one admitted slot until disconnect.

`ServerController.start` resolves private numeric bind and token before constructing/binding transport. No half-initialized registry is created on failure. Toolbar and CLI print only URL and token-file path.

### TDD red

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_mcp_streamable_server.py tests/unit/test_mcp_sse_transport.py tests/unit/test_mcp_gui_server.py tests/unit/test_initgui_commands.py
```

Add every verb/path auth matrix, duplicate/malformed/wrong/right Bearer, no-dispatch counters, Host/Origin precedence, monotonic refill, 429, pre-thread 503/release, SSE occupancy, all private families, public/wildcard/unspecified/multicast, single DNS call, multi-answer rejection, numeric transport bind, and existing protocol/body-limit regressions.

### Compatibility and residuals

- All HTTP clients now require a header, including loopback clients.
- STDIO is unchanged.
- Private-LAN HTTP remains plaintext; Internet bind is technically rejected. Same-LAN token capture remains documented.
- A valid token authorizes `run_macro`; HTTP still never offers `execute_code`.

## S11 — SEC-07 authoritative runtime policy and version discovery

### Files

- Add `security/supported-runtime.json` with schema version 1, add-on `0.23.1-alpha`, FreeCAD minimum `1.0`, Python minimum `3.11`, host-provided PySide/Qt, and `tested: []` until real evidence exists.
- Update `pyproject.toml`: `version="0.23.1a0"`, `requires-python=">=3.11"`, `dependencies=[]`, and explicit setuptools discovery limited to `freecad_ai*`. This closes the observed baseline failure where `pip install -e .` rejects the flat layout because it discovers unrelated top-level directories.
- Add stdlib version normalization helpers within `freecad_ai/runtime_inventory.py`; do not add `packaging` as a runtime dependency.

### TDD red

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_runtime_inventory.py tests/unit/test_mcp_server.py
```

Assert semantic parity of `0.23.1-alpha`, `0.23.1a0`, and `freecad_ai.__version__`; Python minimum parity; valid policy shape; absence of unverified tested claims; and successful editable-install metadata discovery without treating `hooks`, `skills`, `Resources`, `resources`, or `translations` as Python packages.

## S12 — SEC-07 actual-runtime CycloneDX inventory

### Interface and output

Implement `freecad_ai/runtime_inventory.py` as stdlib-only:

```python
def collect_runtime_components() -> list[dict]: ...
def build_cyclonedx_bom(components: list[dict]) -> dict: ...
def write_runtime_bom(path: str) -> None: ...
def main(argv: list[str] | None = None) -> int: ...
```

- Discover FreeCAD via `FreeCAD.Version()`, Python via `sys.version_info`, PySide2/6 via the active compatibility binding, and Qt from its exposed version constant.
- Components: application FreeCAD AI plus framework/runtime components FreeCAD, Python, PySide, Qt; stable bom-refs and dependency edges from the application.
- CycloneDX `bomFormat="CycloneDX"`, `specVersion="1.5"`, version 1, random `urn:uuid` serial.
- Never include usernames, hostnames, executable paths, config paths, environment, or secrets.
- Missing any required version returns non-zero and writes no apparently complete BOM.
- Output uses secure atomic write when under a user-selected path but does not silently overwrite a symlink.

### TDD red

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_runtime_inventory.py
```

Mock every runtime; assert structure, components, edges, no identity strings, deterministic semantic content excluding UUID, explicit output, and hard failure for each missing component.

## S13 — CI, documentation, and final regression

### CI

Add `.github/workflows/security-regression.yml` for Python 3.11. It installs pinned test tooling and runs only the deterministic security/unit slices that do not require FreeCAD/PySide GUI. It validates policy/SBOM unit output and runs `git diff --check`. It must not claim FreeCAD integration or host-runtime CVE coverage.

Do not make the existing untriaged Bandit baseline a false green by blanket suppression. Record Bandit/pip-audit separately; `pip-audit` over explicit `dependencies=[]` means only that there are no PyPI runtime dependencies.

### Documentation

Update README and generated TCCode artifacts with:

- AI Python session toggle and per-call confirmation.
- Project-instruction trust/preview and canonical-root rule.
- HTTP token discovery/header migration, private-only bind, rate/concurrency defaults, plaintext-LAN warning, no Internet support.
- Strict provider TLS errors and secure secret references.
- Preflight status wording and explicit unvalidated execution warning.
- Runtime SBOM command and external Grype/Trivy scan as optional evidence.
- Accepted residuals: STDIO `execute_code`, authenticated HTTP `run_macro`, approved code OS privileges, Windows ACL limitation.

### Final commands and evidence

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit -rs
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/integration -rs
.venv/bin/python -m bandit -r freecad_ai
.venv/bin/python -m pip_audit . --strict --progress-spinner off
git diff --check
git status --short
```

Run a real token-authenticated loopback handshake and negative request only if no server is already running; never restart or kill one. Run GUI/FreeCAD integration only in an available supported runtime and report every skip/blocker exactly.

## Phase checkpoints and rollback package

After each slice record:

1. Files/symbols changed and why.
2. Focused red evidence, minimal green result, and previous-slice regression result.
3. Current config/data migration state and whether any real user path was touched; expected answer during tests is no.
4. Open failures, skipped evidence, and exact next command.

Rollback is commit-by-commit. Never relax HTTP auth, restore unverified TLS, undo restrictive permissions, or delete migrated secret/trust files as a shortcut. Additive config fields are ignored by older builds; `file:` secret references remain consumable. If an older build cannot use authenticated HTTP, use STDIO rather than enabling an unauthenticated fallback.

## Audit closure matrix

| Finding | Closed when |
|---|---|
| SEC-01 | default schema/prompt omit raw code; GUI session gate and every-call approval pass; HTTP list/call impossible |
| SEC-02 | all containment failures are fail-closed and first/changed snapshot requires user decision |
| SEC-03 | mandatory token, private numeric bind, every-request auth, rate and pre-thread concurrency tests pass |
| SEC-04 | no unverified TLS path exists and both HTTPS edges fail visibly on context error |
| SEC-05 | no production `mktemp`; private artifacts and all cleanup/status branches pass |
| SEC-06 | verified no-loss secret migration, private atomic persistence, and default metadata-only logs pass |
| SEC-07 | policy/version parity and actual-runtime CycloneDX generator pass without overstating CVE coverage |

## Independent ID review

The final `agy` review scored correctness, completeness, security, testability, rollback, and consistency at 100% and returned `PASS` with no blockers.

- Accepted: fsync the parent directory after atomic replacement on POSIX so the new directory entry is durable.
- Rejected: changing the process umask in the shared test process. Every security-sensitive creation uses an explicit restrictive mode, and global umask mutation adds cross-test coupling.
- Rejected: adding a bespoke SIGTERM/SIGKILL escalation loop. The current bounded subprocess API already owns timeout cleanup; introducing new process-termination behavior is outside this remediation and would require separate operational review.
- Added from local baseline evidence after the review: explicit setuptools discovery restricted to `freecad_ai*`, because editable installation currently fails by discovering unrelated top-level directories.

## Final implementation checkpoint — 2026-09-04

All S1–S12 slices are implemented. Three review cycles on S11/S12 converted a
first-pass path validator into a descriptor-pinned POSIX commit protocol and
tightened runtime version inputs. Coverage-only review then added meaningful
failure-branch tests without production exclusions or pragmas. The full unit
coverage run passed 1,556 tests and diff-cover reports 97%.

Static delta review found no branch-new test findings after correction. Three
semantically neutral production formatting findings were corrected; four
intentional broad catches remain documented architecture boundaries. Critical
Ruff is green. The project-wide Ruff backlog and Bandit Medium/Low results are
not represented as green.

Implementation status is `PASS`; the release status is `HOLD` until the exact
external-runtime items in the Session Transfer Protocol are proven.
