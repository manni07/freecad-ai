# Security Remediation Implementation Manual — 2026-09-04

## Decision and evidence boundary

The security remediation is **implemented, locally verified, and ready for
repository integration: PASS**. Release, deployment, and runtime acceptance
remain **HOLD**. Repository integration is separately authorized by the user;
it does not constitute a release. This distinction is mandatory: the available
environment did not provide a supported FreeCAD
AppImage/PySide runtime, a disposable live FreeCAD MCP instance, an approved
private-LAN target, a Windows host, or an actual-host SBOM scanner run.

The immutable source is the
[2026-09-04 security audit](../audits/security-audit-2026-09-04.html), SHA-256
`d41a1861a11a366a07d4f966185fad8d8b2ae7c7cf87bf5f2a9c3957c43e1ad0`.
The audit was not overwritten; the implementation result is reported separately
in the [remediation report](../audits/security-remediation-2026-09-04.html).

### Immutable implementation coordinates

- Repository: `/Volumes/ExtremePro/projects/freecad-ai`
- Isolated worktree:
  `/Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation`
- Branch: `agent-workflow/20260904-115556-security-remediation`
- Base: `15774022a1c981335135d95928bd6cb4f7ba0431`
- Implementation commit: `7ab3900f178ae8360c11da3933a30d263555e23f`
- Pull request: `https://github.com/manni07/freecad-ai/pull/1`, targeting
  `manni07/freecad-ai:master`
- Workflow: TCCode led the gated dossiers and implementation; Agent Workflow v4
  ran in thorough mode with a fixed team of four.
- Operational invariant: no computer, server, FreeCAD process, or other service
  was restarted or killed.

## Scope

The work addresses SEC-01 through SEC-07 from the immutable audit:

1. model-originated arbitrary Python;
2. project-instruction include disclosure;
3. unauthenticated HTTP MCP;
4. fail-open HTTPS certificate handling;
5. unsafe executable temporary files;
6. permissive secret, conversation, configuration, and log persistence; and
7. incomplete runtime/package inventory.

The implementation intentionally does not claim OS-level isolation for approved
Python, encrypted private-LAN HTTP, OAuth-based Internet MCP, OS-native secret
storage, Windows ACL equivalence, or a verified host-runtime matrix. Those are
explicit residuals or later hardening work, not silently omitted requirements.

## Architecture overview

### Model tool and code-execution flow

```text
process-only CodeExecutionAccess snapshot
              |
              +--> filtered registry/schema ----> provider request
              |          execute_code omitted while disarmed
              |
              +--> filtered system prompt
                         raw-code guidance omitted while disarmed

provider execute_code call
              |
              +--> execution-edge gate recheck
                       |
                       +-- disarmed/stale --> terminal rejection
                       |
                       +-- armed --> CodeReviewDialog
                                      |
                                      +-- Cancel --> terminal rejection
                                      +-- Execute --> reviewed bytes once
```

The session capability and Dangerous Mode are independent. A model-originated
denial terminates the current tool batch, records protocol-compatible skipped
results for later calls, emits the normal response-finished signal, and does not
start another provider turn. Manual Plan execution remains compatible.

### Project-instruction flow

```text
selected document directory / bounded parent search / config fallback
              |
              +--> canonical root and contained include resolver
              +--> strict UTF-8 and byte/depth/type limits
              +--> versioned, length-framed raw-byte fingerprint
              |
              +--> first/changed fingerprint preview
                         |
                         +-- allow  --> exact in-memory content snapshot
                         +-- ignore --> explicit empty snapshot
                         +-- cancel/error --> abort before input or conversation mutation
                                      |
                                      +--> request, compaction, and retry reuse snapshot
```

Omitted compatibility input and an explicitly empty approved/ignored snapshot
are distinct. The compatibility loader returns content only for a valid current
`allow` record.

### Authenticated HTTP MCP flow

```text
configuration
  +--> resolve/provision token safely
  +--> resolve host exactly once to one private numeric address
              |
              +--> construct transport with numeric host and address family
                         |
incoming socket --> pre-thread semaphore (8 by default)
                         |
                         +--> Host/Origin validation
                         +--> exactly one Bearer credential
                         +--> global token bucket (60/minute, burst 20)
                         +--> route/body parsing and handler dispatch
```

Authentication applies to all routes and verbs. Rejected Host, Origin, or
authorization traffic does not reach body parsing or tool dispatch. HTTP tool
registration permanently excludes `execute_code` while retaining authenticated
`run_macro`. STDIO retains `execute_code` as an accepted compatibility residual.

### Durable-data flow

```text
legacy JSON + FreeCAD ParamGet
              |
              +--> snapshot old values
              +--> migrate literal provider and reranker secrets
              +--> exclusive private files + exact readback
              +--> atomic candidate config + exact readback
              +--> mirror harmless file: references to ParamGet
                         |
                         +-- any failure --> restore old config/ParamGet,
                                             clean owned orphan candidates,
                                             emit visible warning
```

Managed POSIX directories are `0700`; managed files are `0600`. Configuration,
conversations, session logs, and BOM output use same-directory exclusive
temporary files, file flush/fsync, atomic replacement, validation, parent fsync,
and owned-temp cleanup. A parent-directory fsync failure after replacement is
reported as durability uncertainty; it cannot promise rollback after commit.

## SEC-01 — Model-originated Python execution

### Before

`execute_code` was part of the normal model toolset. Act mode could dispatch it
without a dedicated capability grant, the regex safety list was not an OS
sandbox, and missing/broken preflight infrastructure could be treated too
optimistically.

### After

- `freecad_ai/core/code_execution_access.py`
  - `CodeExecutionAccess` is a process-wide, memory-only, default-disarmed
    capability with only manual `arm()` and `disarm()` transitions.
  - `get_code_execution_access()` provides the singleton across dock recreation
    and New Chat without persisting it across process exit.
- `freecad_ai/ui/chat_widget.py`
  - `code_access_toggle` appears before and independently from `danger_toggle`.
  - `_on_code_access_toggled()` uses an explicit warning whose default is No.
  - `_continue_send()` takes one GUI-thread state snapshot, filters the registry,
    intersects reranker output/pins with actually present names, and passes the
    same state to prompt construction.
  - `_execute_tool_call()` rechecks the live capability. Each armed call opens a
    new `CodeReviewDialog`; Cancel and stale/disarmed calls are terminal.
  - `_LLMWorker._tool_loop()` stops the rest of a terminally denied batch and
    does not retry the provider.
  - `_handle_act_mode()` cannot use `auto_execute` to bypass review.
- `freecad_ai/core/system_prompt.py`
  - `build_system_prompt(..., code_tool_enabled=False)` fails closed by default
    and removes raw-code guidance when the capability is unavailable.
- `freecad_ai/tools/setup.py`
  - `create_default_registry(..., exclude_names=...)` applies exclusions to
    built-ins, extras, user tools, and MCP-derived tools.
- `freecad_ai/mcp/gui_server.py`
  - `_default_backend()` always builds HTTP with
    `exclude_names={"execute_code"}`.

Approved code still runs with the FreeCAD user's OS privileges. The preflight is
a compatibility and validation check, not an isolation boundary.

## SEC-02 — Project instructions and includes

### Before

Absolute includes, traversal, and symlink escape could read arbitrary local
files, and project content could enter a provider prompt without fingerprinted
user trust.

### After

- `freecad_ai/extensions/agents_md.py`
  - `InstructionBundle` is frozen and contains canonical `root`, `source_path`,
    substituted `content`, `fingerprint`, and ordered root-relative `manifest`.
  - `discover_instruction_bundle()` rejects absolute/NUL includes, containment
    failure, sibling-prefix escape, symlinks, non-regular targets, cycles,
    invalid UTF-8, files above 64 KiB, expanded bundles above 256 KiB, and depth
    above five. A nested error rejects the whole bundle.
  - The SHA-256 fingerprint covers a version marker and length-framed manifest
    paths/raw bytes before variable substitution.
  - `_trusted_decision()` validates the canonical root key, exact source under
    root, lowercase `sha256:` value, `allow|ignore`, and string timestamp.
  - `load_agents_md()` is fail-closed and loads only the exact currently allowed
    fingerprint.
- `freecad_ai/ui/project_instructions_dialog.py`
  - Presents read-only source, root, manifest, fingerprint, and content with
    allow, ignore, and cancel decisions.
- `freecad_ai/ui/chat_widget.py`
  - `_prepare_project_instructions()` runs before clearing input, modifying the
    conversation, attachments, or provider state.
  - First use and changed fingerprints require preview; unchanged allow does
    not. Ignore supplies an exact empty snapshot. Cancel or resolver failure
    leaves the request state unchanged.
- `freecad_ai/config.py`
  - `project_instruction_trust` persists fingerprint-scoped decisions.

Defense-in-depth remains open: file validation precedes a path-based `open`
rather than pinning and `fstat`-verifying the opened descriptor. A concurrent
local path swap could change preview content, although the resulting exact
fingerprint and explicit preview decision prevent unreviewed provider delivery.

## SEC-03 — HTTP MCP authentication and resource control

### Before

The HTTP transport could intentionally bind beyond loopback without client
authentication, exported the full registry including `execute_code`, and lacked
global request-rate and pre-thread concurrency bounds.

### After

- `freecad_ai/mcp/gui_server.py`
  - `resolve_token_file()` distinguishes the managed default from a custom
    read-only path.
  - `load_or_provision_token()` provisions only the default with
    `token_urlsafe(32)`, newline, `O_EXCL`, `0600`, file and parent fsync, and
    exact safe readback. Existing malformed, symlinked, or non-regular paths
    fail closed.
  - Custom tokens are never created, renamed, replaced, truncated, or chmodded.
    They are opened with `O_NOFOLLOW`, checked through the same descriptor for
    regular type, owner, restrictive mode, and inode/device identity.
  - `resolve_private_bind()` accepts only one numeric loopback, RFC1918,
    link-local, or IPv6 ULA result. `localhost` maps directly; other hostnames
    use exactly one `getaddrinfo()` result set. Public, wildcard, unspecified,
    multicast, broadcast/reserved, CGNAT/site-local, mapped, scoped, mixed, and
    ambiguous results fail closed.
  - `ServerController.start()` resolves token and numeric bind before transport,
    socket, or backend construction; binds the numeric address and carries the
    address family without a second DNS lookup. Startup errors are sanitized.
- `freecad_ai/mcp/transport.py`
  - `HTTPServerTransport` requires a non-empty in-memory Bearer token.
  - `parse_request()` applies Host/Origin, exactly-one Authorization,
    constant-time Bearer comparison, and a locked global token bucket before
    route handling and body parsing.
  - Invalid or zero rate/burst/concurrency values use safe defaults.
  - A nonblocking bounded semaphore admits at most eight request threads by
    default. Excess requests receive raw 503 plus `Retry-After: 1`; every
    thread-start, handler, and SSE-close path releases its permit.
  - `rotate_bearer_token()` atomically changes future request snapshots without
    holding the token lock during `compare_digest`.
- `InitGui.py` and `mcp_server_http.py`
  - Load configuration fail-closed, report the URL and token-file path only,
    and never print token content.

HTTP remains plaintext on approved private LANs. Bearer authentication controls
access but does not protect the token from same-LAN capture. Internet exposure
is unsupported.

## SEC-04 — HTTPS certificate verification

### Before

Failure of `ssl.create_default_context()` caused an automatic fallback to an
unverified SSL context for provider requests.

### After

- `freecad_ai/llm/client.py`
  - Records verified-context construction failure without constructing any
    unverified context.
  - `_check_ssl()` blocks both ordinary POST and streaming HTTPS before network
    access when the verified context is unavailable.
  - Local HTTP providers remain compatible.
  - Reported failures redact API keys, Authorization values, and URL queries.

Repository absence checks found no production `_create_unverified_context`.

## SEC-05 — Preflight temporary workspace

### Before

The executor used `tempfile.mktemp()` names for Python later consumed by
FreeCAD, leaving a name/open race.

### After

- `freecad_ai/core/executor.py`
  - `PreflightStatus` and `PreflightResult` distinguish `PASSED`, `REJECTED`,
    `UNAVAILABLE`, and `ERROR`; unavailable infrastructure is never success.
  - `_sandbox_test()` uses a private `TemporaryDirectory` with `0700` and
    exclusive `0600` script, document-copy, and pre-created result files.
  - The active document copy stays inside that private workspace.
  - Setup, execution, timeout, malformed output, and harness failures clean up
    and return explicit status.
- `freecad_ai/ui/code_review_dialog.py`
  - `REJECTED` is never overrideable.
  - Only GUI `UNAVAILABLE` or `ERROR` may continue through a second warning
    whose default is No.
  - The approved bytes are executed once after review.

The existing case-preserving `FreeCADCmd` lookup defect was also corrected;
tests were not skipped or weakened.

## SEC-06 — Secrets, configuration, conversations, and logs

### Before

Literal keys could be duplicated into JSON and ParamGet, managed paths relied on
ambient umask, and session logs could persist messages, tool arguments, and
results by default.

### After

- `freecad_ai/secure_storage.py`
  - `ensure_private_dir()`, `atomic_write_bytes()`, `atomic_write_json()`, and
    `harden_managed_paths()` reject symlink/non-directory/file targets and apply
    private POSIX modes.
  - `migrate_literal_secret()` leaves empty, `file:`, and `cmd:` values intact;
    literal values move to collision-safe exclusive files, are fsynced and read
    back exactly, and reuse only exact existing content.
  - `redact_sensitive()` recursively returns a new structure and redacts
    sensitive keys plus already-known exact literal values.
- `freecad_ai/config.py`
  - Adds `project_instruction_trust`, `session_log_content="metadata"`, token
    file, rate, burst, and concurrency settings without changing retention
    defaults.
  - `_ensure_dirs()` hardens every managed directory.
  - `_migrate_config_secrets()` snapshots old ParamGet, migrates provider then
    reranker keys into a candidate, atomically saves and reads it back before
    mirroring harmless `file:` references. Failure attempts explicit config and
    ParamGet rollback and cleans owned orphan secret files.
  - A successful migration never writes the literal API key back to ParamGet.
- `freecad_ai/core/conversation.py`
  - Conversation saves are complete JSON but private and atomic.
- `freecad_ai/ui/chat_widget.py`
  - Default session logs contain timestamp and metadata-only tool entries:
    name, success, duration, turn, and optional error class.
  - Full content requires explicit opt-in and is recursively redacted with
    known provider/reranker literal secrets; logging never executes a `cmd:`
    resolver merely to discover a value.

Windows mode bits are not claimed to provide owner-only ACLs. ParamGet rollback
is best effort, and post-commit parent-fsync uncertainty is surfaced rather than
misrepresented as lossless rollback.

## SEC-07 — Runtime and release inventory

### Before

`package.xml` and `pyproject.toml` disagreed on release/Python metadata, package
discovery was not explicit, and an empty dependency audit could be mistaken for
a vulnerability-free FreeCAD host.

### After

- `pyproject.toml`
  - Version `0.23.1a0`, Python `>=3.11`, explicit `dependencies=[]`, and
    setuptools discovery restricted to `freecad_ai*` with non-package trees
    excluded.
- `package.xml`
  - Semantic version `0.23.1-alpha`, FreeCAD minimum 1.0, Python minimum 3.11.
- `security/supported-runtime.json`
  - Schema 1, matching add-on version, explicit FreeCAD/Python minima,
    host-provided PySide/Qt, and an intentionally empty tested-runtime list.
- `freecad_ai/mcp/client.py`
  - `CLIENT_INFO` imports package `__version__` instead of carrying a divergent
    literal.
- `freecad_ai/runtime_inventory.py`
  - Collects exactly FreeCAD AI, FreeCAD, Python, PySide, and Qt from the active
    runtime; validates bounded non-secret numeric-first version strings; emits a
    privacy-minimal CycloneDX 1.5 graph with five components and five dependency
    entries.
  - POSIX output pins each parent with non-following `dir_fd` operations, checks
    temporary inode identity before replace, validates final identity/mode,
    fsyncs file and parent, confines parent swaps, and cleans only the owned
    temporary entry. Windows is explicitly a best-effort fallback.
- `.github/workflows/security-regression.yml`
  - Runs deterministic Python 3.11 unit/security checks, states that
    host-provided components are out of scope, and makes no vulnerability-free
    host claim. Immutable Action SHA/transitive tool pinning remains open.

The scoped empty-declaration `pip-audit` proves only that the project declares
no PyPI runtime dependencies. Raw `pip-audit --strict` against this editable,
unpublished alpha checkout fails while trying to resolve it through PyPI and is
not an actual-host vulnerability result.

## Red–green and review history

| Phase | Intended RED evidence | Final GREEN/regression evidence |
|---|---|---|
| Baseline | 1,228 passed, one case-preserving `FreeCADCmd` failure, 88 unavailable integration skips | Baseline failure assigned to Phase A; skips retained as a runtime gap |
| A — TLS, preflight, registry | 10 failed/113 passed; expanded review then 1 failed/138 passed because `result.json` was `0644` | 139 focused passed; 1,254 full unit passed; cross-review PASS |
| B — AI-Python gate | 13 failed/9 passed; corrective RED 2 failed/29 passed for denial retry/later dispatch | 31 focused passed; 1,277 full unit passed; terminal denial review PASS |
| C — project trust | 21 failed/28 passed; corrective RED 1 failed/64 passed because resolver failure continued sending | 65 focused passed; 1,315 full unit passed; snapshot/abort review PASS |
| D — storage and logs | 17 failed/138 passed | 170 focused passed; 1,348 full unit passed; transactional/isolation review PASS |
| E — authenticated MCP | 135 failed/37 passed; adversarial review also found mapped/scoped binds and startup exception reflection | 191 focused passed twice; corrected authenticated SSE fixture 15/15; 1,441 full unit passed |
| F — metadata and inventory | 28 failed initially; corrective rounds 12/26 and 7/48 exposed writer/path/version gaps | 55 focused passed; CycloneDX schema passed; architecture 97%, simulation 97.6% |

Review HOLDs were resolved rather than waived. In particular:

- Phase A pre-created `result.json` exclusively at `0600`.
- Phase B terminal rejection stopped all remaining dispatch and provider retry.
- Phase C resolver failure stopped before user-state mutation.
- Phase D failure injection bound pre-commit preservation, cleanup, migration
  ordering, and post-commit durability uncertainty.
- Phase E adversarial tests covered token swaps, Host/auth precedence, no ninth
  thread, permit release, one-resolution numeric bind, and error sanitation.
- Phase F required two corrective architecture rounds before the POSIX writer
  pinned parent descriptors and temporary inode identity.

## Migration and test-isolation incident

During the first Phase-D full-suite run, the pre-existing test fixture redirected
only some configuration paths. New S8 directory management therefore created an
empty `secrets/` directory in the real FreeCAD AI profile. Root verified that it
was new, empty, and not a symlink, then removed that test artifact. The fixture
now resolves configuration during collection into a process-private canonical
temporary root and redirects tools, hooks, backups, secrets, and the MCP token
path as well as the earlier paths.

Subsequent evidence found no real token or secrets path. The final metadata-only
manifest of the real profile contained six entries and hashed to
`baacca82f7b1b09f74d66270a7fa1e06ac711f8478ead76ed929cf04be41b871`.
It records relative path, kind, mode, and size only—not file content. An earlier
Phase-E hash used a different serializer and must not be compared directly.

## Final verification evidence

- Plain unit suite: **1,556 passed**, zero failures/skips, 113.68 seconds.
- Coverage suite: **1,556 passed**, zero failures/skips, 131.40 seconds.
- Diff coverage: **97%**, 862 changed lines, 24 missing.
- Phase-F focused suite: **55 passed**.
- CycloneDX 1.5 schema probe: five components and five dependency entries.
- Critical Ruff `E9,F63,F7,F82`: **PASS**.
- Full Ruff: **561 findings**, intentionally non-green. Four branch-new
  `BLE001` catches remain at fail-closed migration rollback, preflight error
  classification, and token-error sanitation boundaries.
- Bandit: **3 High, 7 Medium, 89 Low**, non-zero, no `#nosec`. Highs are the
  audit-triaged SHA-1 backup filename, MD5 change detection, and explicit
  user-managed `cmd:` secret execution contexts.
- Scoped declared-PyPI audit: **PASS for the explicit empty dependency set
  only**; it is not a host scan.
- Editable metadata/install check: `0.23.1a0`, no dependencies, only the
  `freecad_ai` top-level package. It was a controlled venv mutation and is not
  part of read-only resume authority.
- `git diff --check`: **PASS**.
- Integration selection: **88 skipped**, all `FreeCAD AppImage not found`.
  Exit code zero is explicitly **not** a runtime pass.

## Compatibility and operating rules

- Structured GUI tools and STDIO MCP retain their interfaces.
- Existing HTTP clients must add a Bearer header after upgrade. Startup reports
  the token-file path, never the value.
- HTTP binds only to one validated private numeric address. Internet exposure is
  unsupported; private-LAN plaintext is an accepted confidentiality residual.
- HTTP omits `execute_code`; STDIO retains it; authenticated HTTP retains
  `run_macro`.
- Tightened file permissions are never automatically relaxed on rollback.
- Migrated secret/trust files are retained; rollback does not delete user data.
- If authenticated HTTP cannot be configured after rollback, use STDIO rather
  than enabling an unauthenticated fallback.
- Never start, stop, restart, or kill a server or FreeCAD process without
  explicit confirmation.

Historical unauthenticated/free-bind MCP documents are marked as superseded by
this remediation so their old instructions are not mistaken for current policy.

## Residuals and mandatory HOLDs

### Accepted product/security residuals

- Approved Python has the FreeCAD user's OS privileges.
- STDIO exposes `execute_code`.
- Authenticated HTTP exposes `run_macro`.
- Private-LAN HTTP has no transport confidentiality; same-LAN token capture is
  possible.
- Windows POSIX-mode equivalence is not claimed.
- ParamGet restoration is best effort.
- A failure of the second parent-directory fsync may report uncertainty after a
  complete old-or-new value has already been committed.

### Release HOLDs

- Supported FreeCAD/PySide GUI and integration acceptance, including one
  explicitly approved mutation of a disposable document.
- Positive and negative authenticated MCP handshake in a live FreeCAD process.
- Isolated private-LAN validation of auth, Host/Origin, rate, concurrency, and
  bind behavior.
- Actual-host runtime BOM and external Grype/Trivy or equivalent CVE scan.
- Windows ACL, reparse-point, and atomic-write equivalence.
- Immutable GitHub Action SHA and transitive test-tool pins.
- Project-wide Ruff and remaining Bandit debt.
- Descriptor-pinned AGENTS file reads as additional path-swap hardening.

No unit, mock, schema, or loopback result may substitute for these external
acceptance gates.

## Artifact map

- [Immutable audit](../audits/security-audit-2026-09-04.html)
- [Remediation report](../audits/security-remediation-2026-09-04.html)
- [Architecture requirements dossier](../dossiers/ARD_security_remediation_2026-09-04.md)
- [Technical requirements dossier](../dossiers/TRD_security_remediation_2026-09-04.md)
- [Implementation dossier](../dossiers/ID_security_remediation_2026-09-04.md)
- [Project plan](../plan/PD_security_remediation_2026-09-04.md)
- [Test dossier and RED/GREEN ledger](../tests/TD_security_remediation_2026-09-04.md)
- [Open-item register](../openitem/security-remediation-open-items-2026-09-04.md)
- [Session Transfer Protocol](../sessions/STP_security_remediation_2026-09-04.md)
- [Development diary](../diaries/Development_Diary_v000.md)
- [Security operations manual](security-operations-2026-09-04.html)
- [Worktree validation report](../reports/security-remediation-worktree-2026-09-04.md)
- [Future hardening proposals](../vision/security-hardening-proposals-2026-09-04.md)
- [Runtime support policy](../../security/supported-runtime.json)

## Safe verification and resume

Start with read-only identity and integrity checks:

```bash
cd /Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation
test "$(git branch --show-current)" = agent-workflow/20260904-115556-security-remediation
test "$(git rev-parse HEAD)" = 15774022a1c981335135d95928bd6cb4f7ba0431
test "$(git merge-base HEAD 15774022a1c981335135d95928bd6cb4f7ba0431)" = 15774022a1c981335135d95928bd6cb4f7ba0431
test "$(shasum -a 256 docs/audits/security-audit-2026-09-04.html | awk '{print $1}')" = d41a1861a11a366a07d4f966185fad8d8b2ae7c7cf87bf5f2a9c3957c43e1ad0
git status --short
git diff --check
```

Then review the authoritative continuation state:

```bash
sed -n '1,280p' docs/tests/TD_security_remediation_2026-09-04.md
sed -n '1,320p' docs/openitem/security-remediation-open-items-2026-09-04.md
sed -n '1,220p' docs/sessions/STP_security_remediation_2026-09-04.md
git diff --stat
```

With matching coordinates, these deterministic checks do not start a service:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_release_metadata.py tests/unit/test_runtime_inventory.py
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit -rs
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider --cov=freecad_ai --cov-branch --cov-report=xml:build/security-coverage.xml -o addopts='' tests/unit
.venv/bin/diff-cover build/security-coverage.xml --compare-branch=15774022a1c981335135d95928bd6cb4f7ba0431 --fail-under=90
.venv/bin/ruff check freecad_ai tests --select E9,F63,F7,F82
.venv/bin/bandit -r freecad_ai -ll -ii
.venv/bin/pip-audit --strict --disable-pip --no-deps -r /dev/null
git diff --check
git status --short
```

Bandit's known non-zero result must be interpreted through the immutable audit;
do not add blanket suppressions. Diff coverage must remain strictly greater than
90%, even though the command threshold is 90.

Do not repeat the editable install under read-only authority. It mutates the
venv and may generate egg-info; it requires a separately approved verification
scope and cleanup plan.

### Supported FreeCAD integration — currently blocked

Run only when the supported FreeCAD/PySide prerequisite is available:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' -m integration tests/integration -rs
```

The current attempt selected 88 tests and skipped all of them with
`FreeCAD AppImage not found`. Any skip keeps this gate on HOLD. The GUI matrix
must additionally use a disposable document and prove the default-locked
toggle, default-No warning, per-call review, Cancel without mutation, exactly
one approved mutation, second-call re-prompt, process reset, and project
instruction preview/reapproval.

### Live MCP acceptance — blocked until explicit approval

The following is recorded for a later disposable live FreeCAD session. It must
not be run merely because it appears in this manual:

```bash
test -n "$FREECAD_AI_MCP_URL"
test -n "$FREECAD_AI_MCP_TOKEN_FILE"
test -f "$FREECAD_AI_MCP_TOKEN_FILE"
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' -X POST "$FREECAD_AI_MCP_URL" -H 'Content-Type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
{ printf 'header = "Authorization: Bearer '; tr -d '\r\n' < "$FREECAD_AI_MCP_TOKEN_FILE"; printf '"\n'; } |
  curl --config - --silent --show-error -X POST "$FREECAD_AI_MCP_URL" -H 'Content-Type: application/json' --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

The first request must return 401 with zero dispatch. Inspect the authenticated
response without recording the header. The token is streamed through curl
configuration input and is not placed in process arguments.

### Actual-host inventory — blocked until prerequisites are approved

```bash
test -n "$FREECAD_AI_SUPPORTED_FREECADCMD"
"$FREECAD_AI_SUPPORTED_FREECADCMD" -c "import sys; from freecad_ai.runtime_inventory import main; sys.exit(main(['--output','build/runtime.cdx.json']))"
.venv/bin/python -c "import json; p='build/runtime.cdx.json'; b=json.load(open(p, encoding='utf-8')); assert b['bomFormat']=='CycloneDX' and b['specVersion']=='1.5' and len(b['components'])==5"
grype sbom:build/runtime.cdx.json
trivy sbom build/runtime.cdx.json
```

A missing component/scanner, incomplete BOM, or untriaged Critical/High result
keeps release on HOLD.

### Windows storage acceptance — currently blocked

```powershell
python -m pytest -q -p no:cacheprovider -o "addopts=" tests/unit/test_secure_storage.py tests/unit/test_config.py tests/unit/test_conversation.py tests/unit/test_session_logs.py tests/unit/test_runtime_inventory.py
```

POSIX mode and `dir_fd` results do not establish Windows ACL or reparse-point
equivalence. Platform-specific skips require explicit Windows evidence.

## Repository integration record

The curated implementation commit
`7ab3900f178ae8360c11da3933a30d263555e23f` was pushed to the workflow branch,
and pull request `https://github.com/manni07/freecad-ai/pull/1` was opened against
the fork's `master`. The user explicitly authorized commit, pull request, and
merge. The read-only upstream `ghbalf/freecad-ai` was not modified. The merge
result is verified through GitHub and reported separately because a commit
cannot record its own eventual merge commit. Repository integration does not
clear any release/runtime HOLD.

The first GitHub security-regression run exposed a CI-environment omission:
two selected security tests import the UI compatibility layer, but the pinned
test-tool installation did not provide PySide. CI now pins the locally verified
`PySide6==6.11.2` as test tooling. The production dependency list remains empty
because FreeCAD supplies PySide/Qt at runtime.

## Pre-integration Git state (historical)

At documentation time, `HEAD` still equals the base commit and all remediation
changes are uncommitted. Modified tracked files include the entrypoints,
configuration, conversation/executor/prompt, project loader, LLM/MCP clients and
transports, registry setup, chat/review UI, package metadata, README, shared test
fixture, and existing focused tests. New untracked deliverables include the
capability gate, secure storage, runtime inventory, project-instruction dialog,
security-focused unit tests, CI workflow, runtime policy, and the TCCode
documentation tree.

Generated `.coverage`, `build/`, `.DS_Store`, and generated egg-info are not
deliverables and must not be staged. The primary checkout was not modified by
this workflow. At the time of this pre-integration snapshot, no commit, push,
pull request, or merge had yet been performed. The user subsequently authorized
those repository-integration actions. That authorization does not include a
release, live server start, real secret migration, or process restart.

Resume only through the
[Session Transfer Protocol](../sessions/STP_security_remediation_2026-09-04.md).
If branch, `HEAD`, merge base, audit hash, test evidence, or authority differs,
stop and preserve the HOLD rather than improvising around it.
