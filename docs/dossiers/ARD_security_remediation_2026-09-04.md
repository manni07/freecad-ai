# Architecture Requirements Dossier: Security Remediation

## Control record

- Workflow: TCCode lead with Agent Workflow v4, `thorough`, quality `critical`, fixed team size 4.
- Worktree: `/Volumes/ExtremePro/projects/freecad-ai-agent-worktrees/20260904-115556-security-remediation`
- Branch: `agent-workflow/20260904-115556-security-remediation`
- Base commit: `15774022a1c981335135d95928bd6cb4f7ba0431`
- Audit: `docs/audits/security-audit-2026-09-04.html`
- Audit SHA-256: `d41a1861a11a366a07d4f966185fad8d8b2ae7c7cf87bf5f2a9c3957c43e1ad0`
- Operational invariant: never restart or reboot FreeCAD, a computer, or a server without explicit user confirmation.

## Goals and acceptance boundaries

The implementation shall remediate SEC-01 through SEC-07 without weakening the existing loopback, Host, Origin, request-size, timeout, undo, backup, and HTML-escaping controls. Security decisions must be enforced at execution edges, not only in GUI text or LLM schemas.

Success requires:

1. `execute_code` is absent from the default GUI LLM schema, appears only after an in-memory session unlock, and still requires one explicit GUI confirmation per call.
2. HTTP MCP never lists or executes `execute_code`; non-loopback startup fails without a valid installation token; every HTTP request is authenticated.
3. Project instructions are previewed at first use and after content changes; every include remains inside the canonical instruction root.
4. HTTPS never falls back to an unverified TLS context.
5. Sandbox artifacts use private, race-free temporary storage.
6. Managed secrets and persisted user data receive restrictive permissions, atomic writes, migration without deletion, and metadata-only diagnostic logs by default.
7. The supported host runtime is machine-readable and a runtime CycloneDX SBOM can be generated from the actual FreeCAD process.

Non-goals:

- No general-purpose OS sandbox is introduced in this change. Explicit user approval remains the boundary for free-form GUI code.
- No OAuth service, Internet-facing HTTP MCP, automatic certificate authority, or remote deployment is added.
- No redesign of structured FreeCAD tools, external MCP client tools, hooks, user tools, or macros.
- No automatic deletion of existing conversations, logs, secrets, backups, or trust decisions.

## Architectural decisions

### AD-01: Two-layer raw-code capability gate

`CodeExecutionAccess` is a process-wide in-memory singleton, initially disarmed and never serialized. It deliberately survives New Chat and dock destruction/recreation and ends only on manual disarm or process exit. A dedicated checkable control beside the existing Dangerous-mode control in the chat header owns the user-visible arm/disarm action; the two controls never imply or modify each other's state. `create_default_registry(..., exclude_names=...)` physically excludes forbidden tool names. GUI dispatch rechecks the gate immediately before execution. A stale or fabricated call therefore fails even if its schema was produced while the gate was armed.

The GUI session toggle controls schema visibility only for `execute_code`. Every model-originated raw-code call is shown in `CodeReviewDialog`; only the dialog's Execute action runs it, exactly once. `auto_execute` cannot bypass this confirmation. System-prompt construction receives `code_tool_enabled` and must not recommend a missing tool.

HTTP MCP's backend always excludes `execute_code`. This rule has no configuration or environment override. STDIO MCP retaining `execute_code` is an explicitly accepted residual because the user limited the prohibition to HTTP MCP.

### AD-02: Content-addressed project trust

Instruction discovery returns an immutable `InstructionBundle` containing canonical root, source, expanded snapshot, include manifest, and SHA-256 fingerprint. The root is the real path of the directory containing the selected `AGENTS.md` or `FREECAD_AI.md`; the global fallback root is the real path of `CONFIG_DIR`.

Includes reject absolute paths, traversal, symlink escape, non-regular files, invalid UTF-8, cycles, more than five levels, more than 64 KiB per file, or more than 256 KiB expanded. Any violation rejects the entire bundle. The fingerprint covers versioned framing, canonical root-relative filenames, and raw bytes in include order before live-variable substitution.

The GUI presents source, root, manifest, fingerprint, and expanded content before a first or changed version is sent. `allow` and `ignore` decisions are stored per canonical root and fingerprint. Cancel preserves the unsent input. The exact approved byte snapshot is used for that request to remove the check/use race.

### AD-03: Installation-bound HTTP identity

HTTP MCP uses one 256-bit installation token stored outside JSON at `<CONFIG_DIR>/mcp_server.token`, or at the explicitly configured token-file path. Only the default managed path may be provisioned or permission-hardened automatically. A custom path is read-only input: if it is missing, unsafe, or unreadable, startup fails without creating, replacing, or chmodding it. The default token is generated with exclusive creation and mode `0600`; failure to provision or read it prevents startup. Every method and path requires exactly one Bearer header and compares it with `hmac.compare_digest`.

Host/Origin validation remains independent. Public, wildcard, unspecified, multicast, or ambiguously resolved bind targets are rejected. Accepted targets are loopback, RFC1918, IPv4 link-local, IPv6 ULA, or IPv6 link-local only. A hostname is resolved exactly once, every answer is validated, and the transport binds the selected numeric address returned by that validation rather than resolving the hostname again. The same token is required on loopback, intentionally requiring existing HTTP clients to add a header.

Per-token rate control is a token bucket of 60 requests/minute with burst 20. The server permits at most eight active handlers and rejects excess work before allocating another worker thread. Responses are 401 for authentication failure, 403 for Host/Origin failure, 429 for rate exhaustion, and 503 for concurrency exhaustion.

Accepted residual: private-LAN HTTP remains plaintext. Authentication prevents unauthorised use but not same-LAN token capture. Documentation must prohibit Internet exposure and recommend an SSH tunnel or future HTTPS/mTLS where network confidentiality is required. Authenticated HTTP still exposes `run_macro`; possession of the token is the authorization boundary for that capability.

### AD-04: Fail-closed provider TLS

`LLMClient` records default SSL-context construction failure and raises `LLMError` on any later HTTPS request. It never calls `_create_unverified_context`. Local HTTP providers continue to work. Both streaming and non-streaming paths use the same verified context decision.

### AD-05: Private persistence primitive

A small stdlib-only `secure_storage` module owns private-directory creation, atomic mode-`0600` file writes, symlink refusal, permission hardening, recursive diagnostic redaction, and verified literal-secret migration. It touches only known FreeCAD AI paths.

Literal provider and reranker keys migrate to verified files under `<CONFIG_DIR>/secrets/`, after which configuration and ParamGet contain a `file:` reference. No old value is removed before secret read-back and atomic configuration persistence succeed. Conflicting secret files are never overwritten; a unique file is allocated. Existing `file:` and `cmd:` references remain unchanged.

Conversations remain complete but private. Automatic diagnostic logs default to metadata only. Retention stays opt-in so an upgrade cannot silently delete user data.

### AD-06: Host-runtime evidence

A stdlib-only runtime-inventory module emits CycloneDX 1.5 JSON for FreeCAD AI, FreeCAD, Python, PySide, and Qt from the actual runtime. Missing required component versions make generation fail. A tracked supported-runtime policy records minimum and tested versions without pretending that FreeCAD-hosted components are PyPI dependencies.

## Configuration interface

Additive `AppConfig` fields and defaults:

```python
mcp_server_token_file: str = ""  # empty => CONFIG_DIR/mcp_server.token
mcp_server_rate_limit_per_minute: int = 60
mcp_server_rate_limit_burst: int = 20
mcp_server_max_concurrent_requests: int = 8
project_instruction_trust: dict = field(default_factory=dict)
session_log_content: str = "metadata"  # metadata|full
```

There is deliberately no persistent `execute_code` enablement and no HTTP-auth disable switch. Existing configs load through the dataclass unknown-key filter; older builds ignore these additive fields.

Trust records have the shape:

```json
{
  "/canonical/root": {
    "source": "/canonical/root/AGENTS.md",
    "fingerprint": "sha256:...",
    "decision": "allow",
    "approved_at": "ISO-8601"
  }
}
```

## Component and data flow

```text
project files -> safe instruction resolver -> fingerprint -> GUI preview
                                                        -> allow snapshot -> system prompt
                                                        -> ignore -> no project prompt

LLM schema <- filtered registry <- session raw-code gate
LLM tool call -> main-thread dispatch -> gate recheck -> code review
              -> preflight passed OR explicit execute-without-preflight warning -> executor once

HTTP request -> concurrency gate -> Host/Origin -> Bearer -> rate gate
             -> MCP dispatcher -> HTTP-filtered registry -> Qt executor

config/secret/log data -> secure storage -> private atomic files
FreeCAD runtime -> runtime inventory -> CycloneDX JSON -> external CVE scanner
```

## Security review and veto conditions

The security review approves this architecture only if all of the following remain fail-closed:

- An unarmed, rejected, stale, or HTTP-originated `execute_code` call never reaches its handler.
- Project-instruction resolution never returns partial content after a containment or size failure.
- Missing/unreadable HTTP token, public bind target, TLS-context failure, or unsafe managed-path symlink produces a visible failure, not a fallback.
- Tokens, authorization headers, literal secrets, and full tool arguments/results are absent from default logs and exception text.

Deployment/release is vetoed if focused security tests are not 100% green, if the whole-system simulation is at or below 95%, or if real FreeCAD/PySide validation remains falsely reported as complete.

## Compatibility and rollback

- Structured GUI tools and STDIO MCP preserve existing interfaces.
- Existing HTTP clients require a Bearer header after upgrade; this intentional break is documented with token-file discovery instructions.
- Tightened modes are never automatically relaxed during rollback. Operators may use STDIO if HTTP credentials cannot be configured.
- Restrictive permissions are not undone. Secret files and trust records are retained; rollback does not delete or rewrite user content.
- No phase may restart FreeCAD or another process without explicit confirmation.

## Final architecture decision — 2026-09-04

The implementation matches the approved trust boundaries and passed the final
architecture review at 97%. In particular, runtime BOM output on POSIX pins
every parent component with non-following directory descriptors and performs
create/stat/replace/unlink/fsync relative to the pinned parent. Four new Ruff
`BLE001` reports are accepted at exact fail-closed boundaries: the outer
secret-migration transaction, best-effort migration rollback, preflight
workspace infrastructure conversion to `ERROR`, and token-load error
sanitization. Narrowing those catches without redesign would permit partial
state, exception leakage, or an unclassified fail-open path.

Architecture is `PASS` for code review, but deployment remains `HOLD` pending
supported FreeCAD GUI/integration, live authenticated FreeCAD MCP, actual-host
SBOM/CVE scan, private-LAN isolation evidence and Windows ACL equivalence.
