# Session Transfer Protocol — Security Remediation — 2026-09-04

## Immutable resume coordinates

- Repository: `/Volumes/ExtremePro/projects/freecad-ai`
- Isolated worktree: `/Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation`
- Branch: `agent-workflow/20260904-115556-security-remediation`
- Base commit: `15774022a1c981335135d95928bd6cb4f7ba0431`
- Implementation commit: `7ab3900f178ae8360c11da3933a30d263555e23f`
- Pull request: `https://github.com/manni07/freecad-ai/pull/1` against `manni07/freecad-ai:master`
- Source audit: `docs/audits/security-audit-2026-09-04.html`
- Source audit SHA-256: `d41a1861a11a366a07d4f966185fad8d8b2ae7c7cf87bf5f2a9c3957c43e1ad0`
- Open-item register: `docs/openitem/security-remediation-open-items-2026-09-04.md`
- Test dossier: `docs/tests/TD_security_remediation_2026-09-04.md`

Do not resume in the primary checkout. Do not reset, clean, stash, checkout, or overwrite the workflow worktree. The implementation is committed and pushed; `.DS_Store` remains intentionally untracked, while `.coverage`, generated egg-info, and `build/security-coverage.xml` are not deliverables.

## Current evidence checkpoint

- Audit findings SEC-01 through SEC-07 have implementation and focused-test coverage in the worktree.
- Fresh pre-PR unit gate: `1556 passed` in 129.03 seconds, with no failures or skips.
- Final plain unit run: `1556 passed` in 113.68 seconds, with no failures or skips. Final coverage run: `1556 passed` in 131.40 seconds; changed-line coverage is 97% over 862 changed lines with 24 missing.
- Independent diff-cover rerun passed at 97%; only `freecad_ai/ui/chat_widget.py` is below 100% among changed production files.
- Final Phase-F reviews: architecture 97%; simulation 97.6%; both `PASS`.
- Critical Ruff `E9,F63,F7,F82`: `PASS` (`All checks passed!`). Final full Ruff remains non-green with 561 project-wide legacy/quality findings; four branch-new broad exception boundaries are explicitly retained for fail-closed rollback/error sanitization.
- Declared PyPI dependency audit: `PASS` with the scoped empty requirement command. This does not scan host-provided FreeCAD, PySide, or Qt.
- Raw `.venv/bin/pip-audit --strict` is non-authoritative here because it tries to resolve the editable, unpublished local alpha project through PyPI. Do not treat that resolution failure as a host scan; use the scoped declaration command and keep the actual-host BOM/CVE gate separate.
- Bandit `-ll -ii`: 3 High, 7 Medium, 89 Low, non-zero. The three Highs match the source audit's accepted contextual triage; no `#nosec` suppressions were used.
- `git diff --check`: `PASS`.
- Phase-E isolation evidence recorded the real-config metadata hash as `a68d8516d2919afa16a474a53d960a724125e44d7421545c14f5ba9f508e98ba`, with no real token/secrets path or non-fixture LAN listener created. Reverify this rather than assuming it remains current.
- Final post-test recheck used a metadata-only JSON manifest of relative path, kind, mode and size (six entries; no file contents) and produced `baacca82f7b1b09f74d66270a7fa1e06ac711f8478ead76ed929cf04be41b871`; no `mcp_server.token` or `secrets/` directory exists. This serializer differs from the Phase-E checkpoint and the hashes are not directly comparable.
- FreeCAD GUI/integration, a live authenticated FreeCAD MCP handshake, isolated private-LAN acceptance, actual-host runtime BOM/scanning, and Windows behavior remain unverified.
- The exact integration selection was attempted and returned 88 skips, all `FreeCAD AppImage not found`; exit 0 is not accepted as a pass.

## Safe resume procedure

Run these read-only identity checks first:

```bash
cd /Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation
test "$(git branch --show-current)" = agent-workflow/20260904-115556-security-remediation
git merge-base --is-ancestor 7ab3900f178ae8360c11da3933a30d263555e23f HEAD
test "$(git merge-base HEAD 15774022a1c981335135d95928bd6cb4f7ba0431)" = 15774022a1c981335135d95928bd6cb4f7ba0431
test "$(shasum -a 256 docs/audits/security-audit-2026-09-04.html | awk '{print $1}')" = d41a1861a11a366a07d4f966185fad8d8b2ae7c7cf87bf5f2a9c3957c43e1ad0
git status --short
git diff --check
```

Review the authoritative artifacts before doing work:

```bash
sed -n '1,280p' docs/tests/TD_security_remediation_2026-09-04.md
sed -n '1,320p' docs/openitem/security-remediation-open-items-2026-09-04.md
git diff --stat 15774022a1c981335135d95928bd6cb4f7ba0431..HEAD
```

If the coordinates and hashes match, run deterministic local verification without starting a service:

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

Interpret Bandit's expected non-zero result only through the immutable audit triage; do not turn it green with blanket suppression. Diff coverage must be strictly greater than 90%, even though the command's numeric threshold is 90.

## Exact blocked commands and evidence

The following commands are deliberately blocked in the current environment. Record their exact output only after the required environment and authority exist.

### Supported FreeCAD integration and GUI

```bash
PYTHONDONTWRITEBYTECODE=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q -p no:cacheprovider -o addopts='' -m integration tests/integration -rs
```

Current blocker: no supported FreeCAD/PySide runtime. A skipped selection is not a pass. The GUI acceptance matrix in the open-item register must also run in a disposable document.

### Actual-host runtime inventory and scan

```bash
test -n "$FREECAD_AI_SUPPORTED_FREECADCMD"
"$FREECAD_AI_SUPPORTED_FREECADCMD" -c "import sys; from freecad_ai.runtime_inventory import main; sys.exit(main(['--output','build/runtime.cdx.json']))"
.venv/bin/python -c "import json; p='build/runtime.cdx.json'; b=json.load(open(p, encoding='utf-8')); assert b['bomFormat']=='CycloneDX' and b['specVersion']=='1.5' and len(b['components'])==5"
grype sbom:build/runtime.cdx.json
trivy sbom build/runtime.cdx.json
```

Current blocker: the supported FreeCAD host and external scanner evidence are unavailable. Unit tests use mocked runtimes and are not a substitute.

### Live authenticated MCP

```bash
test -n "$FREECAD_AI_MCP_URL"
test -n "$FREECAD_AI_MCP_TOKEN_FILE"
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' -X POST "$FREECAD_AI_MCP_URL" -H 'Content-Type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
{ printf 'header = "Authorization: Bearer '; tr -d '\r\n' < "$FREECAD_AI_MCP_TOKEN_FILE"; printf '"\n'; } |
  curl --config - --silent --show-error -X POST "$FREECAD_AI_MCP_URL" -H 'Content-Type: application/json' --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Current blocker: no authorized live disposable FreeCAD server. Do not start, stop, restart, or kill a server/process without confirmation. Never record the expanded Authorization header or token value.

### Isolated private-LAN acceptance

There is no approved LAN target in this session. First obtain explicit authorization for an isolated private address and client; then record the concrete address and commands in a new evidence artifact. Loopback tests do not satisfy this gate, and Internet exposure is prohibited.

### Windows acceptance

```powershell
python -m pytest -q -p no:cacheprovider -o "addopts=" tests/unit/test_secure_storage.py tests/unit/test_config.py tests/unit/test_conversation.py tests/unit/test_session_logs.py tests/unit/test_runtime_inventory.py
```

Current blocker: no supported Windows FreeCAD environment. POSIX modes and `dir_fd` behavior do not prove Windows ACL or reparse-point behavior.

## Stop rules

Stop immediately and keep the gate on `HOLD` if any of these occurs:

1. Worktree, branch, base commit, or audit hash differs from the immutable coordinates above.
2. A selected test fails, errors, skips, xfails, or is deselected unexpectedly.
3. Changed-line coverage is at most 90%, Critical Ruff fails, or a new/untriaged Bandit High appears.
4. A token, Authorization value, provider key, user path, hostname, or environment secret appears in logs, BOM, errors, or documentation.
5. A test or command touches a real config, secret, conversation, log, token, document, LAN listener, or other user path.
6. A real server/process is already running; do not restart or kill it. Obtain explicit confirmation before any lifecycle action.
7. FreeCAD/PySide, external scanners, Windows, or isolated-LAN prerequisites are unavailable. Record the blocker; do not substitute mocks for live evidence.
8. Action SHAs/transitive hashes remain unresolved for a requested release, or actual-host SBOM scanning is incomplete.
9. An independent security/architecture or simulation review scores below 95%, or a High blocker reappears after the final review iteration.
10. Any proposed continuation expands beyond the explicit resume authority below.

## Authority and handoff state

- Completed under the implementation authority: source/tests plus the complete TCCode documentation set in commit `7ab3900f178ae8360c11da3933a30d263555e23f`; do not broaden or rewrite them during resume without a new task.
- The user explicitly authorized commit, push, pull request, and merge. PR #1 records that repository-integration scope; repository integration does not authorize release, deployment, live runtime activity, or process lifecycle changes.
- Authorized on resume after repository integration: read-only identity/verification checks and documentation of their results.
- The already-completed editable install was a controlled venv mutation. Repeating `.venv/bin/python -m pip install --no-deps -e .` is not part of read-only resume authority; it requires a new implementation/release verification scope and cleanup of generated egg-info.
- Not authorized on resume: further source/test/config changes, real migration, live server activity, process termination/restart, destructive cleanup, or release.
- Accepted residuals that must remain visible: private-LAN HTTP has no transport confidentiality; STDIO exposes `execute_code`; authenticated HTTP exposes `run_macro`; approved Python has the FreeCAD user's OS privileges; Windows permission equivalence is unproven; ParamGet rollback is best effort; a post-commit parent-directory fsync failure can report uncertainty while leaving complete old-or-new bytes.
- Static/open residuals: full Ruff baseline, Bandit Medium/Low backlog, accepted three Bandit High contexts, and unresolved Action SHA/transitive pinning.

To resume implementation or release work, first provide the identity-check output and request a new explicit scope. Never infer authority for live runtime or release work from this handoff.
