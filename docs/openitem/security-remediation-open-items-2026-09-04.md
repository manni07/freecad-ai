# Security Remediation Open Items — 2026-09-04

Status: implementation evidence is strong, but runtime/release approval remains **HOLD**. This register contains exactly three High, three Medium, and three Low measures. An item may move to `PASS` only when its acceptance commands and evidence requirements are complete; lack of an available environment is not a pass.

The source audit is immutable at `docs/audits/security-audit-2026-09-04.html`, SHA-256 `d41a1861a11a366a07d4f966185fad8d8b2ae7c7cf87bf5f2a9c3957c43e1ad0`.

## High measures

### H1 — Supported FreeCAD integration and GUI acceptance

- Owner: Runtime QA
- Status: `HOLD` — no supported FreeCAD/PySide runtime is available in the current environment.
- Risk/measure: verify the default-locked AI-Python toggle, No-default warning, per-call approval, Cancel-without-mutation, exactly-once approved mutation in a disposable document, second-call re-prompt, New Chat/dock recreation process-session semantics, AGENTS preview/reapproval, and a fresh-process locked state.
- Acceptance commands:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' -m integration tests/integration -rs
```

Then run the GUI matrix in an explicitly confirmed supported FreeCAD process against a disposable document and attach the observed results. Any skip keeps this item on `HOLD`.

### H2 — Actual-host runtime BOM and external vulnerability scan

- Owner: Release Security
- Status: `HOLD` — mocked inventory tests pass, but the actual FreeCAD/Python/PySide/Qt host inventory has not been generated or scanned.
- Risk/measure: generate the CycloneDX 1.5 BOM inside the supported FreeCAD runtime, verify exactly five components and no local identity/secrets, then scan the same immutable BOM with an available external scanner.
- Acceptance commands:

```bash
test -n "$FREECAD_AI_SUPPORTED_FREECADCMD"
"$FREECAD_AI_SUPPORTED_FREECADCMD" -c "import sys; from freecad_ai.runtime_inventory import main; sys.exit(main(['--output','build/runtime.cdx.json']))"
.venv/bin/python -c "import json; p='build/runtime.cdx.json'; b=json.load(open(p, encoding='utf-8')); assert b['bomFormat']=='CycloneDX' and b['specVersion']=='1.5' and len(b['components'])==5"
grype sbom:build/runtime.cdx.json
trivy sbom build/runtime.cdx.json
```

Do not run these commands until the supported executable and scanner policy are confirmed. A missing scanner, missing component, incomplete BOM, or Critical/High result without explicit triage remains `HOLD`.

### H3 — Live authenticated MCP acceptance in FreeCAD

- Owner: MCP Security QA
- Status: `HOLD` — only fixture-owned loopback transports have been exercised; no live FreeCAD MCP server may be started or restarted without confirmation.
- Risk/measure: in a confirmed disposable FreeCAD session, prove an unauthenticated request returns 401 with zero dispatch, an authenticated structured tool succeeds once, `execute_code` remains absent from HTTP, and `run_macro` remains available. Never print or persist the token value.
- Acceptance commands:

```bash
test -n "$FREECAD_AI_MCP_URL"
test -n "$FREECAD_AI_MCP_TOKEN_FILE"
test -f "$FREECAD_AI_MCP_TOKEN_FILE"
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' -X POST "$FREECAD_AI_MCP_URL" -H 'Content-Type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
{ printf 'header = "Authorization: Bearer '; tr -d '\r\n' < "$FREECAD_AI_MCP_TOKEN_FILE"; printf '"\n'; } |
  curl --config - --silent --show-error -X POST "$FREECAD_AI_MCP_URL" -H 'Content-Type: application/json' --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

The first status must be 401; the authenticated response must be inspected without recording its header. Starting, stopping, or restarting the server requires separate user confirmation.

## Medium measures

### M1 — Isolated private-LAN bind validation

- Owner: Network Security QA
- Status: `HOLD` — loopback fixtures are not private-LAN evidence.
- Risk/measure: on a separately approved isolated LAN, prove one-resolution numeric binding, mandatory Bearer auth, Host/Origin enforcement, 429/503 behavior, and no public/wildcard/multicast/unspecified bind. Internet exposure is unsupported. Plaintext HTTP permits same-LAN token capture and remains an accepted residual.
- Acceptance commands:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_mcp_token.py tests/unit/test_mcp_auth.py tests/unit/test_mcp_gui_server.py tests/unit/test_mcp_streamable_server.py tests/unit/test_mcp_sse_transport.py tests/unit/test_initgui_commands.py
```

After that deterministic prerequisite, execute and document the same positive/negative requests from a confirmed isolated-LAN client. No LAN listener may be created without explicit approval.

### M2 — Windows ACL and atomic-write equivalence

- Owner: Windows Platform QA
- Status: `HOLD` — POSIX `chmod`, `dir_fd`, `O_DIRECTORY`, and `O_NOFOLLOW` evidence does not prove Windows ACL or race resistance.
- Risk/measure: verify fail-closed symlink/reparse-point handling, owner-only ACLs for managed secrets/config/logs/conversations, complete-file atomic replacement, and safe BOM output on a supported Windows FreeCAD host.
- Acceptance commands:

```powershell
python -m pytest -q -p no:cacheprovider -o "addopts=" tests/unit/test_secure_storage.py tests/unit/test_config.py tests/unit/test_conversation.py tests/unit/test_session_logs.py tests/unit/test_runtime_inventory.py
```

Skipped POSIX-only cases must be replaced by explicit Windows evidence before this item can pass; current Windows behavior must not be described as equivalent.

### M3 — Retained privileged capability boundaries

- Owner: Product Security
- Status: `ACCEPTED RESIDUAL / HOLD FOR PERIODIC REVIEW`.
- Risk/measure: STDIO MCP intentionally retains `execute_code`; authenticated HTTP intentionally retains `run_macro`; user-approved Python executes with the FreeCAD user's OS privileges. Keep these boundaries documented, fail-closed, and regression-tested without adding an unauthenticated fallback.
- Acceptance commands:

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_tool_routing.py tests/unit/test_mcp_server.py tests/unit/test_mcp_gui_server.py tests/unit/test_chat_widget_code_access.py tests/unit/test_code_review_dialog.py
```

Any HTTP exposure of `execute_code`, loss of per-call GUI approval, or loss of `run_macro` authentication reopens the remediation.

## Low measures

### L1 — GitHub Action SHA and transitive tool pinning

- Owner: CI Maintainers
- Status: `OPEN` — action SHAs/transitive hashes were not guessed or fetched in the offline remediation scope.
- Risk/measure: resolve trusted immutable SHAs for referenced actions and lock transitive test tooling using an approved online provenance workflow.
- Acceptance commands:

```bash
rg -n 'uses: [^#[:space:]]+@v[0-9]+' .github/workflows
rg -n 'uses: [^#[:space:]]+@[0-9a-f]{40}([[:space:]]|$)' .github/workflows
```

The first command must return no floating major tags, and every action must be accounted for by the second command plus recorded provenance. Do not substitute unverified SHAs.

### L2 — Project-wide Ruff baseline

- Owner: Code Quality Maintainers
- Status: `OPEN` — final full Ruff reports 561 project-wide legacy/quality findings; the critical subset is green and broad unrelated cleanup was intentionally avoided. Exact delta review left no new test finding and retained four new production `BLE001` boundaries for fail-closed rollback/error sanitization.
- Risk/measure: reduce the baseline in separately scoped work without mixing formatting/refactoring into this security change.
- Acceptance commands:

```bash
.venv/bin/ruff check freecad_ai tests
.venv/bin/ruff check freecad_ai tests --select E9,F63,F7,F82
```

The second command must remain green. This item passes only when the first command is green or a separately approved ratcheting policy is implemented.

### L3 — Remaining Bandit backlog and accepted scanner triage

- Owner: Security Maintainers
- Status: `OPEN WITH ACCEPTED HIGHS` — current `-ll -ii` result is 3 High, 7 Medium, 89 Low and exits non-zero.
- Risk/measure: retain the immutable manual triage: B324 SHA-1 in `core/executor.py` tags backup filenames; B324 MD5 in `extensions/skills.py` detects changes; B602 `shell=True` in `llm/client.py` implements the explicit user-managed `cmd:` token feature. Review the seven Medium and 89 Low findings separately; do not add blanket `#nosec` suppressions.
- Additional defense-in-depth note: the AGENTS resolver validates symlink/type
  before a path-based `open` rather than pinning and `fstat`-verifying the
  opened descriptor. A concurrent local path swap could alter what appears in
  the preview, but the exact snapshot fingerprint and explicit preview decision
  prevent unreviewed provider transmission. Add descriptor-pinned reads in a
  separate hardened-filesystem slice rather than expanding this remediation.
- Acceptance commands:

```bash
.venv/bin/bandit -r freecad_ai -ll -ii
shasum -a 256 docs/audits/security-audit-2026-09-04.html
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' tests/unit/test_agents_md.py tests/unit/test_project_instruction_trust.py
```

The audit hash must remain `d41a1861a11a366a07d4f966185fad8d8b2ae7c7cf87bf5f2a9c3957c43e1ad0`; any new or changed High requires explicit re-triage.

## Release control

Git commit, push, PR, merge, release, process restart, live-server start, destructive cleanup, and any real secret migration remain unauthorized. Generated `.coverage`, `build/`, and `.DS_Store` entries are not deliverables and must not be staged. Resume through the Session Transfer Protocol at `docs/sessions/STP_security_remediation_2026-09-04.md`.
