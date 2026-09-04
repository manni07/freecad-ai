"""Process-wide controller for the MCP server hosted inside FreeCAD.

Three routes start this server, and all of them land in the same process:

  * ``FreeCAD.AppImage /path/to/mcp_server_http.py`` on the command line
  * ``exec(open(".../mcp_server_http.py").read())`` in the Python console
  * the FreeCAD AI toolbar toggle

They must share one object. Without it the toggle renders unchecked next to a
server that is already listening, and clicking it builds a second transport
that dies on EADDRINUSE inside a daemon thread — visible only as a console
traceback. Port-probing is not a substitute: "something is listening on 3000"
does not mean it is ours.
"""

import base64
import binascii
import ipaddress
import logging
import os
import secrets
import socket
import stat
import threading
from dataclasses import dataclass

from ..config import CONFIG_DIR
from ..secure_storage import ensure_private_dir

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3000


@dataclass(frozen=True)
class ResolvedBindAddress:
    """A private bind target resolved exactly once before socket creation."""

    display_host: str
    numeric_host: str
    family: int
    port: int


def _is_allowed_private_address(address):
    if address.is_unspecified or address.is_multicast:
        return False
    if isinstance(address, ipaddress.IPv4Address):
        return (address.is_loopback or address.is_link_local
                or address in ipaddress.ip_network("10.0.0.0/8")
                or address in ipaddress.ip_network("172.16.0.0/12")
                or address in ipaddress.ip_network("192.168.0.0/16"))
    if address.ipv4_mapped is not None or address.scope_id is not None:
        return False
    return (address.is_loopback or address.is_link_local
            or address in ipaddress.ip_network("fc00::/7"))


def resolve_private_bind(host: str, port: int) -> ResolvedBindAddress:
    """Resolve one private numeric listener address without a DNS re-check."""
    if not isinstance(host, str) or not host.strip():
        raise ValueError("MCP bind host must not be empty")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("MCP bind port must be an integer from 0 through 65535")
    host = host.strip()
    if host.casefold() == "localhost":
        return ResolvedBindAddress(host, "127.0.0.1", socket.AF_INET, port)

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        answers = socket.getaddrinfo(host, port)
        resolved = set()
        for family, socktype, _proto, _canonname, sockaddr in answers:
            if socktype not in (0, socket.SOCK_STREAM):
                continue
            if family not in (socket.AF_INET, socket.AF_INET6):
                raise OSError("MCP hostname resolved to an unsupported address family")
            numeric = sockaddr[0]
            try:
                candidate = ipaddress.ip_address(numeric)
            except ValueError as exc:
                raise OSError("MCP hostname did not resolve to a numeric address") from exc
            if not _is_allowed_private_address(candidate):
                raise OSError("MCP hostname resolved outside the supported private network scope")
            resolved.add((family, str(candidate)))
        if len(resolved) != 1:
            raise OSError("MCP hostname must resolve to exactly one private address")
        family, numeric = resolved.pop()
        return ResolvedBindAddress(host, numeric, family, port)

    if not _is_allowed_private_address(address):
        raise OSError("MCP bind address is outside the supported private network scope")
    family = socket.AF_INET if address.version == 4 else socket.AF_INET6
    return ResolvedBindAddress(host, str(address), family, port)


def resolve_token_file(cfg=None) -> tuple[str, bool]:
    """Return the canonical token path and whether it is app-managed."""
    configured = os.environ.get("MCP_TOKEN_FILE", "")
    if not configured and cfg is not None:
        configured = getattr(cfg, "mcp_server_token_file", "") or ""
    if configured:
        expanded = os.path.expandvars(os.path.expanduser(configured))
        if os.path.lexists(expanded) and stat.S_ISLNK(os.lstat(expanded).st_mode):
            raise ValueError("custom MCP token path must not be a symlink")
        return os.path.realpath(expanded), False
    return os.path.realpath(os.path.join(CONFIG_DIR, "mcp_server.token")), True


def _validate_token_bytes(raw: bytes) -> str:
    data = raw[:-1] if raw.endswith(b"\n") else raw
    if not data or b"\n" in data or b"\r" in data:
        raise ValueError("MCP token file is malformed")
    try:
        token = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("MCP token file is malformed") from exc
    if len(token) < 43 or any(not (char.isalnum() or char in "-_") for char in token):
        raise ValueError("MCP token file is malformed")
    try:
        decoded = base64.b64decode(
            token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("MCP token file is malformed") from exc
    if len(decoded) < 32:
        raise ValueError("MCP token file has insufficient entropy capacity")
    return token


def _read_token_file(path: str, *, managed_default: bool) -> str:
    before = os.lstat(path)
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError("MCP token path must be a non-symlink regular file")
    if not managed_default and os.name != "nt":
        if hasattr(os, "getuid") and before.st_uid != os.getuid():
            raise ValueError("custom MCP token file must be owned by the current user")
        if stat.S_IMODE(before.st_mode) & 0o077:
            raise ValueError("custom MCP token file permissions are too broad")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        current = os.fstat(fd)
        if not stat.S_ISREG(current.st_mode):
            raise ValueError("MCP token path must be a regular file")
        if (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino):
            raise OSError("MCP token file changed while it was being opened")
        if os.name != "nt":
            if managed_default:
                os.fchmod(fd, 0o600)
                if stat.S_IMODE(os.fstat(fd).st_mode) != 0o600:
                    raise OSError(
                        "managed MCP token permissions could not be secured")
            else:
                if hasattr(os, "getuid") and current.st_uid != os.getuid():
                    raise ValueError(
                        "custom MCP token file must be owned by the current user")
                if stat.S_IMODE(current.st_mode) & 0o077:
                    raise ValueError(
                        "custom MCP token file permissions are too broad")
        with os.fdopen(fd, "rb") as stream:
            fd = -1
            raw = stream.read()
    finally:
        if fd != -1:
            os.close(fd)
    return _validate_token_bytes(raw)


def load_or_provision_token(path: str, managed_default: bool) -> str:
    """Load a safe token, exclusively provisioning only the managed path."""
    if not managed_default:
        return _read_token_file(path, managed_default=False)
    if os.path.lexists(path):
        return _read_token_file(path, managed_default=True)

    parent = os.path.dirname(os.path.abspath(path))
    ensure_private_dir(parent)
    raw = (secrets.token_urlsafe(32) + "\n").encode("ascii")
    fd = None
    created = False
    created_identity = None
    try:
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created = True
            opened = os.fstat(fd)
            created_identity = (opened.st_dev, opened.st_ino)
        except FileExistsError:
            return _read_token_file(path, managed_default=True)
        if os.name != "nt":
            os.fchmod(fd, 0o600)
            if stat.S_IMODE(os.fstat(fd).st_mode) != 0o600:
                raise OSError("managed MCP token permissions could not be secured")
        with os.fdopen(fd, "wb") as stream:
            fd = None
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        token = _read_token_file(path, managed_default=True)
        dir_fd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        return token
    except Exception:
        if created and os.path.lexists(path):
            try:
                current = os.lstat(path)
                if (stat.S_ISREG(current.st_mode)
                        and (current.st_dev, current.st_ino) == created_identity):
                    os.unlink(path)
            except OSError:
                pass
        raise
    finally:
        if fd is not None:
            os.close(fd)


def resolve_server_address(cfg=None):
    """Return ``(host, port)``: env beats config, config beats defaults.

    Env wins so every documented command-line recipe keeps working unchanged,
    including the wiki's ``MCP_PORT=…`` and Flatpak invocations.
    """
    host = DEFAULT_HOST
    port = DEFAULT_PORT
    if cfg is not None:
        host = getattr(cfg, "mcp_server_host", "") or DEFAULT_HOST
        port = getattr(cfg, "mcp_server_port", 0) or DEFAULT_PORT

    env_host = os.environ.get("MCP_HOST")
    if env_host:
        host = env_host

    env_port = os.environ.get("MCP_PORT")
    if env_port:
        try:
            port = int(env_port)
        except ValueError:
            logger.warning("Ignoring non-numeric MCP_PORT=%r", env_port)

    return host, port


def resolve_allowed_hosts(cfg=None):
    """Return the ``Host``-header allowlist, or ``None`` for the default.

    ``None`` is not the same as the loopback list. The transport derives its
    own default only when ``allowed_hosts is None``, and that branch is where
    a wildcard bind is rejected. Passing an explicit list — even one identical
    to the default — is the documented opt-in to a wider policy, so returning
    a list when the user configured nothing would silently disarm that guard
    and restore #60's every-client-gets-403 dead end.

    Env beats config, matching MCP_HOST / MCP_PORT. Entries are comma
    separated.

    Raises ValueError on a ``*`` entry because wildcard Host matching defeats
    the DNS-rebinding guard even when Bearer authentication is enabled.
    """
    raw = os.environ.get("MCP_ALLOWED_HOSTS")
    if raw:
        hosts = raw.split(",")
    elif cfg is not None:
        hosts = list(getattr(cfg, "mcp_server_allowed_hosts", None) or [])
    else:
        hosts = []

    hosts = [h.strip() for h in hosts if h and h.strip()]
    if any(h == "*" for h in hosts):
        raise ValueError(
            "'*' is not accepted in the MCP allowed-hosts list. The server "
            "only supports explicitly named private-network hosts. Name the "
            "concrete hosts "
            "clients dial instead.")
    return hosts or None


def _default_backend():
    """Build the tool registry and the Qt main-thread executor.

    ``include_mcp=False``: this registry is what we *serve*, so it must not
    re-export tools the workbench's own MCP client pulled in from elsewhere.
    The executor marshals every call onto the Qt main thread because FreeCAD's
    document API is not thread-safe.
    """
    from ..tools.executor_utils import QtMainThreadToolExecutor
    from ..tools.setup import create_default_registry

    registry = create_default_registry(
        include_mcp=False, exclude_names={"execute_code"})
    executor = QtMainThreadToolExecutor()
    executor.set_registry(registry)
    return registry, executor


class ServerController:
    """Owns the one MCP server that may run in this process."""

    def __init__(self, backend_factory=None):
        self._backend_factory = backend_factory or _default_backend
        self._transport = None
        self._thread = None
        self._registry = None
        self._executor = None
        self._url = None
        self._token_file_path = None

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    @property
    def url(self):
        return self._url if self.is_running() else None

    @property
    def token_file_path(self):
        return self._token_file_path if self.is_running() else None

    def start(self, host, port, allowed_hosts=None, cfg=None):
        """Start serving and return the URL.

        Raises OSError if the bind fails, or if ``host`` is a wildcard address
        while ``allowed_hosts`` is None — see HTTPServerTransport.

        Binds *before* building the registry: the bind is the only step that
        realistically fails, it is cheap, and failing first leaves no
        half-initialised backend behind.
        """
        if self.is_running():
            return self._url

        # A serve thread that died on its own leaves is_running() False while the
        # listening socket is still open. Reap it, or every later start() on this
        # port fails with EADDRINUSE until FreeCAD restarts.
        if self._transport is not None:
            self._transport.stop()
            self._transport = None
            self._url = None

        resolved = resolve_private_bind(host, port)
        token_path, managed = resolve_token_file(cfg)
        try:
            token = load_or_provision_token(token_path, managed)
        except Exception as exc:
            error_type = ValueError if isinstance(exc, ValueError) else OSError
            raise error_type(
                "MCP bearer token could not be loaded safely") from None

        from .transport import HTTPServerTransport

        transport_allowed_hosts = allowed_hosts
        if (transport_allowed_hosts is None
                and resolved.display_host.casefold()
                != resolved.numeric_host.casefold()):
            transport_allowed_hosts = [
                "127.0.0.1", "localhost", "::1",
                resolved.numeric_host, resolved.display_host,
            ]
        transport = HTTPServerTransport(
            host=resolved.numeric_host,
            port=resolved.port,
            address_family=resolved.family,
            allowed_hosts=transport_allowed_hosts,
            bearer_token=token,
            rate_limit_per_minute=getattr(
                cfg, "mcp_server_rate_limit_per_minute", 60),
            rate_limit_burst=getattr(cfg, "mcp_server_rate_limit_burst", 20),
            max_concurrent_requests=getattr(
                cfg, "mcp_server_max_concurrent_requests", 8),
        )
        transport.bind()  # raises OSError on the caller's thread — the point
        try:
            if self._registry is None or self._executor is None:
                self._registry, self._executor = self._backend_factory()

            from .server import MCPServer

            server = MCPServer(self._registry, transport=transport,
                               executor=self._executor)
            thread = threading.Thread(
                target=self._serve, args=(server,), daemon=True,
                name="mcp-http-server")
            thread.start()
        except Exception:
            transport.stop()
            raise

        self._transport = transport
        self._thread = thread
        self._token_file_path = token_path
        # The advertised URL is the Streamable HTTP endpoint: HTTP+SSE is
        # deprecated with a removal window (#65), so new configurations should
        # not be pointed at it. The legacy pair keeps serving regardless.
        url_host = (f"[{resolved.numeric_host}]"
                    if resolved.family == socket.AF_INET6
                    else resolved.numeric_host)
        self._url = "http://%s:%d/mcp" % (url_host, resolved.port)
        logger.info(
            "MCP server listening on %s (legacy HTTP+SSE also served at "
            "the same authenticated listener)", self._url)
        return self._url

    def _serve(self, server):
        # MCPServer.run() calls transport.run(), which is bind() + serve();
        # bind() is idempotent, so the socket we already secured is reused.
        try:
            server.run()
        except Exception:
            logger.exception("MCP server stopped unexpectedly")

    def stop(self):
        """Shut the server down and release the port. Idempotent."""
        transport, self._transport = self._transport, None
        thread, self._thread = self._thread, None
        self._url = None
        self._token_file_path = None
        if transport is not None:
            transport.stop()
        if thread is not None:
            thread.join(timeout=5)


_controller = None


def get_server_controller():
    """Return the process-wide controller, creating it on first use."""
    global _controller
    if _controller is None:
        _controller = ServerController()
    return _controller
