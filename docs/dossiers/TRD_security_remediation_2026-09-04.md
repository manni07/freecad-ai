# Technical Requirements Dossier: Security Remediation

## Traceability

| Audit | Required implementation | Primary verification |
|---|---|---|
| SEC-01 | session-only schema gate, per-call GUI confirmation, immutable HTTP exclusion, prompt alignment | schema, stale-call, reject, exactly-once, HTTP list/call tests |
| SEC-02 | canonical-root resolver, bounded includes, content fingerprint, preview/trust flow | traversal, symlink, cycle, size, changed-fingerprint, cancel tests |
| SEC-03 | mandatory installation Bearer token, private-only bind policy, rate/concurrency limits | live loopback HTTP status and dispatch-negative tests |
| SEC-04 | remove unverified TLS fallback | streaming/non-streaming SSL-failure tests |
| SEC-05 | private temporary directory and exclusive script creation | modes, cleanup, timeout/error tests |
| SEC-06 | private atomic persistence, verified secret migration, metadata logs | permissions, symlink, failure injection, redaction tests |
| SEC-07 | supported-runtime policy and CycloneDX runtime generator | schema, component, version-parity, incomplete-runtime tests |

## Concrete interfaces and change points

### Tool policy

- Add `freecad_ai/core/code_execution_access.py` with process-wide singleton accessor `get_code_execution_access()` and `CodeExecutionAccess.active/arm/disarm`. It survives dock recreation; New Chat does not reset it.
- Add a dedicated checkable raw-code control beside `danger_toggle` in `ChatDockWidget` with a default-No warning. It is synchronized from `CodeExecutionAccess` on dock construction but is otherwise independent of Dangerous mode.
- Extend `freecad_ai/tools/setup.py::create_default_registry` with `exclude_names`. Apply it to built-ins, user tools, connected MCP tools, and extras before registration.
- In `ChatDockWidget._continue_send`, exclude `execute_code` unless the session gate is active; intersect the reranker result with the permitted registry names.
- In `ChatDockWidget._execute_tool_call`, reject `execute_code` when disarmed; otherwise open a review dialog and return its already-produced result without invoking the registry handler a second time.
- In `ChatDockWidget._handle_act_mode`, ignore `auto_execute` for model-originated raw code and retain the existing review path.
- Extend `build_system_prompt(mode, agents_md, tools_enabled, override, code_tool_enabled=False)` and conditionally omit raw-code guidance/examples.
- In `mcp/gui_server.py::_default_backend`, call `create_default_registry(include_mcp=False, exclude_names={"execute_code"})`. The resulting missing-tool error is the HTTP dispatch backstop.

### Project instructions

- Replace string-only internal discovery with `discover_instruction_bundle() -> InstructionBundle | None`; retain `load_agents_md()` as a compatibility wrapper that returns content only for an already allowed current fingerprint.
- Resolver must use `os.path.realpath`, `os.path.commonpath`, `os.stat(..., follow_symlinks=False)`/equivalent regular-file checks, a visited set, and byte accounting.
- Add a GUI preparation method invoked in `_send_message` before clearing input or appending to the Conversation. Cache its exact result for compaction/retry of the same user turn.
- Persist `allow` or `ignore` only through normal secure config save. A resolver error is rendered locally and aborts send.
- Variable substitution occurs only after the bundle's raw-content fingerprint is accepted.

### HTTP MCP

- Add token-path resolution and provisioning helpers to `mcp/gui_server.py`; configuration beats the default path. The default managed path may be securely provisioned, while a custom path is read-only and must already exist as a non-symlink regular file. Token material is passed to `HTTPServerTransport` only in memory.
- Extend `HTTPServerTransport.__init__` with `bearer_token`, `rate_limit_per_minute`, `rate_limit_burst`, and `max_concurrent_requests`.
- Centralize all method authorization in one RequestHandler guard returning a reason/status, so a future verb cannot omit it silently.
- Authenticate before parsing request bodies or invoking handlers. Require exactly one Authorization header and exactly one Bearer credential.
- Override threaded-server request admission so the eight-request semaphore is acquired before thread creation and released in `process_request_thread(...): finally`.
- Token bucket state uses `time.monotonic()` and a lock. Do not count rejected Host/Origin/auth requests against an authenticated principal's rate.
- Add `validate_bind_scope(host)` before `transport.bind()`. Resolve host exactly once; reject wildcard/public/ambiguous results; return the selected numeric address and family and bind that numeric value so no second DNS lookup occurs. Preserve the configured display host and concrete allowed-Host checks separately.
- Update toolbar and CLI failure paths to surface token/scope errors without exposing token text. The success message prints URL and token-file path only.
- Settings exposes token-file path and the three numeric limits. It explains mandatory auth, private-only networking, and plaintext-LAN residual risk.

HTTP contract:

| Condition | Status/header | Dispatch |
|---|---|---|
| missing, malformed, duplicate, or wrong Bearer | `401`, `WWW-Authenticate`, `Cache-Control: no-store` | never |
| Host or Origin invalid | `403` | never |
| authenticated token bucket empty | `429`, `Retry-After` | never |
| active-handler limit reached | `503`, `Retry-After` | never |
| accepted | existing MCP semantics | once |

### TLS

- In `LLMClient.__init__`, store `_ssl_context_error` if default-context construction fails; never construct an unverified context.
- `_check_ssl()` rejects HTTPS when `_HAS_SSL` is false or `_ssl_context_error` is set.
- `_http_post` and `_http_stream` continue sharing `_check_ssl` and the verified `_ssl_ctx`.
- Error text identifies the certificate-store problem but excludes request URL query strings, headers, or keys.

### Secure persistence and migration

- Add `freecad_ai/secure_storage.py` with `ensure_private_dir`, `atomic_write_json/bytes`, `harden_managed_paths`, `migrate_literal_secret`, and `redact_sensitive`.
- Use same-directory temporary files, exclusive mode `0600`, flush/fsync, `os.replace`, and a final mode check. Reject symlink targets with `lstat`.
- `_ensure_dirs()` creates all managed directories with `0700` and hardens existing known paths. A permission failure is reported visibly; token creation remains a hard server-start failure.
- `save_config`, `Conversation.save`, manual logs, and automatic logs use atomic private writes.
- On config load after ParamGet overlay, migrate literal provider/reranker secrets. Verify stored bytes before changing config references. Only after atomic config success mirror the `file:` reference to ParamGet.
- Default `session_log_content="metadata"`: save tool name, success, elapsed time, turn, and error class only. Full mode is explicit and warned. Conversation persistence remains full and `0600`.
- Retention defaults stay unchanged; no migration invokes pruning merely because of upgrade.

### Temporary execution

- Enclose script creation, subprocess, result read, and cleanup in one `TemporaryDirectory` context.
- Set directory `0700`; create script via `os.open` with `O_WRONLY|O_CREAT|O_EXCL`, `0600`; place result at a fixed name within that private directory.
- Replace `(True, "")` fail-open infrastructure outcomes with `PreflightResult(status, message)`, where status is `passed`, `rejected`, `unavailable`, or `error`. `execute_code` accepts an internal `allow_unvalidated=False` flag; only the GUI review path may set it after the same dialog visibly labels its action “Execute without preflight”. Non-GUI callers cannot silently obtain this override.
- Never claim a missing result file or caught harness exception as successful validation. A rejected preflight cannot be overridden; only unavailable/error infrastructure status can receive the explicit unvalidated GUI approval.

### Runtime evidence

- Add `security/supported-runtime.json` with add-on `0.23.1-alpha`, FreeCAD minimum `1.0`, Python minimum `3.11`, host-provided PySide/Qt, and an initially empty `tested` list. Populate tested versions only from real runtime evidence.
- Add `freecad_ai/runtime_inventory.py` to emit CycloneDX 1.5 JSON without user paths or hostnames. Required components: add-on, FreeCAD, Python, PySide, Qt; add-on dependency edges reference host components.
- Keep the authoritative Python minimum at `>=3.11`, add explicit `dependencies=[]`, and align the PEP-440 project version to `0.23.1a0`; test semantic equivalence with `package.xml` and `freecad_ai.__version__`.
- Generator exits non-zero if required versions are unavailable. Release documentation distinguishes zero PyPI runtime dependencies from a vulnerability-free host runtime.

## Migration, failure and rollback rules

1. New config fields are optional on load and receive secure defaults.
2. Token provisioning and literal-secret migration are idempotent.
3. Existing data is not deleted. A conflicting destination causes a unique new secret filename.
4. If verified migration cannot complete, keep the original key and report the exact stage; never clear ParamGet first.
5. Project trust records with invalid shapes are ignored fail-closed, not coerced to allow.
6. Invalid rate/concurrency values fall back to documented safe defaults with a warning; zero never means unlimited.
7. Rollback uses prior code with retained `file:` references and tightened permissions. It must not introduce an auth bypass.

## Test requirements

At least ten meaningful tests are required for each implementation phase, combining unit cases where a single subsystem is small. Mandatory cases include:

- Gate initial state, arm/disarm, non-persistence, default schema, armed schema, prompt parity, stale call, reject, exactly once, HTTP list/call denial, raw-code auto-execute bypass prevention.
- Instruction absolute/traversal/symlink/cycle/depth/per-file/aggregate/encoding failures; deterministic fingerprint; changed include; allow/ignore/cancel; unchanged trust; snapshot TOCTOU.
- Token generation entropy/mode/idempotence/read failure; all verbs and routes; malformed/duplicate/wrong/right header; Host/Origin order; private/public bind; 429 refill; 503 release; no log leakage; legacy SSE and Streamable compatibility.
- TLS context success/failure for local HTTP, HTTPS post, HTTPS stream, and error redaction.
- Temp directory/script modes, exclusive creation, result verification, timeout, process error, harness error, missing binary, cleanup in every branch.
- Config/conversation/log atomicity and modes; symlink refusal; permission hardening; secret read-back; conflicting destination; injected write failure; ParamGet sequencing; recursive redaction; metadata/full behavior.
- SBOM schema/version/components/edges, no local identity leakage, incomplete runtime hard failure, supported-runtime parsing, three-way semantic version parity.

No completion claim is permitted with skipped selected tests. FreeCAD/PySide-unavailable tests must be reported as blocked with the exact next command in a supported runtime.

## Accepted residuals

- HTTP on a private LAN does not provide transport confidentiality; token capture by a same-LAN observer remains possible.
- STDIO MCP continues to expose `execute_code`.
- Authenticated HTTP clients can still invoke `run_macro`.
- Explicitly approved free-form code still executes with the FreeCAD user's OS privileges; the preflight is not an OS sandbox.
- Windows `chmod` behavior cannot be presented as a complete ACL guarantee.

## As-built delta — 2026-09-04

- `freecad_ai/runtime_inventory.py` emits exactly five CycloneDX 1.5
  components and five dependency records, rejects missing/unsafe versions and
  omits host identity/path/environment data. POSIX output uses a pinned
  component-by-component `dir_fd` chain; Windows is explicitly best effort.
- `pyproject.toml`, `package.xml`, `freecad_ai.__version__` and
  `security/supported-runtime.json` agree on 0.23.1-alpha/Python 3.11 semantics.
  Runtime PyPI dependencies are explicitly empty; FreeCAD/PySide/Qt are
  host-provided and never inferred safe from pip-audit.
- HTTP MCP requires a private token at startup and a valid Bearer header per
  request, binds only one validated private numeric address, globally bounds
  rate and concurrent handlers, and permanently excludes `execute_code`.
- Project instructions use bounded exact-byte fingerprints and a pre-send GUI
  decision. Raw Python uses a distinct process-only gate and per-call review.
- Managed persistence uses private atomic files, verified secret migration and
  metadata-only logs by default.

Verification: 1,556 unit tests passed with no skips; changed-line branch
coverage is 97%. Runtime/system verification remains `HOLD` as enumerated in
the STP.
