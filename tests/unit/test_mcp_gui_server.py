"""Tests for the process-wide MCP server controller.

Three routes start this server in one FreeCAD process — the
mcp_server_http.py command-line argument, the documented
exec(open(...).read()) console snippet, and the toolbar toggle. They share
one controller so the toggle cannot misreport a server it did not start.
"""

import socket
import time

import pytest

from freecad_ai.mcp.gui_server import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    ServerController,
    get_server_controller,
    resolve_allowed_hosts,
    resolve_server_address,
)


@pytest.fixture(autouse=True)
def _isolated_mcp_token_path(tmp_path, monkeypatch):
    """No controller test may provision or read the developer's real token."""
    import freecad_ai.config as config_mod
    from freecad_ai.mcp import gui_server

    monkeypatch.setattr(gui_server, "CONFIG_DIR", str(tmp_path), raising=False)
    monkeypatch.setattr(config_mod, "CONFIG_DIR", str(tmp_path), raising=False)
    monkeypatch.delenv("MCP_TOKEN_FILE", raising=False)


def _free_port():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


class _FakeRegistry:
    """Minimal stand-in for ToolRegistry.

    MCPServer.run() logs ``len(registry.list_tools())`` on the way up, so a
    bare object() would raise inside the serve thread and the controller would
    report not-running for reasons that have nothing to do with the lifecycle
    being tested.
    """

    def list_tools(self):
        return []

    def to_mcp_schema(self):
        return []


def _fake_backend():
    """Stand in for the FreeCAD tool registry and Qt executor.

    Lifecycle tests must not depend on tool loading; a failure there should
    break tool tests, not these.
    """
    return _FakeRegistry(), object()


def _controller():
    return ServerController(backend_factory=_fake_backend)


def test_http_backend_physically_excludes_execute_code(monkeypatch):
    """HTTP must omit raw code even when a caller fabricates tools/call."""
    from freecad_ai.mcp import gui_server

    registry = _FakeRegistry()
    captured = {}

    def _registry_factory(**kwargs):
        captured.update(kwargs)
        return registry

    class _Executor:
        def set_registry(self, value):
            assert value is registry

    monkeypatch.setattr(
        "freecad_ai.tools.setup.create_default_registry", _registry_factory)
    monkeypatch.setattr(
        "freecad_ai.tools.executor_utils.QtMainThreadToolExecutor", _Executor)

    actual_registry, _ = gui_server._default_backend()

    assert actual_registry is registry
    assert captured.get("include_mcp") is False
    assert captured.get("exclude_names") == {"execute_code"}


# --- address resolution ----------------------------------------------------


def _private_bind_api():
    from freecad_ai.mcp import gui_server
    if not hasattr(gui_server, "resolve_private_bind"):
        pytest.fail("missing S10 resolve_private_bind API")
    return gui_server


@pytest.mark.parametrize("host", ["", "   ", None])
def test_bind_rejects_empty_or_non_string_host(host):
    api = _private_bind_api()
    with pytest.raises(ValueError, match="host"):
        api.resolve_private_bind(host, 3131)


@pytest.mark.parametrize("port", [True, "3131", -1, 65536])
def test_bind_rejects_non_integer_or_out_of_range_port(port):
    api = _private_bind_api()
    with pytest.raises(ValueError, match="port"):
        api.resolve_private_bind("127.0.0.1", port)


def test_localhost_is_pinned_to_numeric_ipv4_without_dns(monkeypatch):
    api = _private_bind_api()
    monkeypatch.setattr(
        api.socket, "getaddrinfo",
        lambda *args: pytest.fail("localhost unexpectedly used DNS"))

    resolved = api.resolve_private_bind(" localhost ", 3131)

    assert resolved.display_host == "localhost"
    assert resolved.numeric_host == "127.0.0.1"
    assert resolved.family == socket.AF_INET


def test_hostname_ignores_non_stream_answers(monkeypatch):
    api = _private_bind_api()
    monkeypatch.setattr(api.socket, "getaddrinfo", lambda host, port: [
        (socket.AF_INET, socket.SOCK_DGRAM, 17, "", ("10.0.0.8", port)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.7", port)),
    ])

    resolved = api.resolve_private_bind("cadbox.lan", 3131)

    assert resolved.numeric_host == "10.0.0.7"


def test_hostname_rejects_unsupported_address_family(monkeypatch):
    api = _private_bind_api()
    monkeypatch.setattr(api.socket, "getaddrinfo", lambda host, port: [
        (socket.AF_UNIX, socket.SOCK_STREAM, 0, "", ("local", port)),
    ])
    with pytest.raises(OSError, match="address family"):
        api.resolve_private_bind("cadbox.lan", 3131)


def test_hostname_rejects_non_numeric_resolver_answer(monkeypatch):
    api = _private_bind_api()
    monkeypatch.setattr(api.socket, "getaddrinfo", lambda host, port: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("not-an-ip", port)),
    ])
    with pytest.raises(OSError, match="numeric"):
        api.resolve_private_bind("cadbox.lan", 3131)


@pytest.mark.parametrize("host", [
    "127.0.0.1", "10.0.0.7", "172.16.1.2", "192.168.1.9",
    "169.254.12.3", "::1", "fc00::7", "fd12:3456::9", "fe80::1",
])
def test_private_numeric_bind_families_are_allowed_without_dns(monkeypatch, host):
    api = _private_bind_api()
    monkeypatch.setattr(
        api.socket, "getaddrinfo",
        lambda *args: pytest.fail("numeric bind unexpectedly used DNS"))
    resolved = api.resolve_private_bind(host, 3131)
    assert resolved.display_host == host
    assert resolved.numeric_host == host
    assert resolved.port == 3131
    assert resolved.family in (socket.AF_INET, socket.AF_INET6)


@pytest.mark.parametrize("host", [
    "0.0.0.0", "::", "8.8.8.8", "2001:4860:4860::8888",
    "224.0.0.1", "ff02::1", "255.255.255.255", "100.64.0.1",
    "198.18.0.1", "192.0.2.1", "240.0.0.1", "fec0::1",
    "::ffff:127.0.0.1", "::ffff:10.0.0.1", "fe80::1%en0",
])
def test_public_wildcard_unspecified_and_multicast_binds_fail_closed(host):
    api = _private_bind_api()
    with pytest.raises((OSError, ValueError)):
        api.resolve_private_bind(host, 3131)


@pytest.mark.parametrize("answers", [
    [(socket.AF_INET, "10.0.0.5"), (socket.AF_INET, "10.0.0.6")],
    [(socket.AF_INET, "10.0.0.5"), (socket.AF_INET, "8.8.8.8")],
    [(socket.AF_INET6, "fd00::5"), (socket.AF_INET6, "2001:4860::1")],
])
def test_hostname_is_resolved_once_and_ambiguous_or_mixed_answers_fail(
        monkeypatch, answers):
    api = _private_bind_api()
    calls = []

    def getaddrinfo(host, port, *args, **kwargs):
        calls.append((host, port))
        return [(family, socket.SOCK_STREAM, 6, "", (address, port))
                for family, address in answers]

    monkeypatch.setattr(api.socket, "getaddrinfo", getaddrinfo)
    with pytest.raises((OSError, ValueError)):
        api.resolve_private_bind("cadbox.lan", 3131)
    assert calls == [("cadbox.lan", 3131)]


def test_single_private_dns_answer_is_returned_for_numeric_transport_bind(
        monkeypatch):
    api = _private_bind_api()
    calls = []

    def getaddrinfo(host, port, *args, **kwargs):
        calls.append((host, port))
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.2.3.4", port))]

    monkeypatch.setattr(api.socket, "getaddrinfo", getaddrinfo)
    resolved = api.resolve_private_bind("cadbox.lan", 3131)
    assert calls == [("cadbox.lan", 3131)]
    assert resolved.display_host == "cadbox.lan"
    assert resolved.numeric_host == "10.2.3.4"
    assert resolved.family == socket.AF_INET


def test_token_failure_precedes_transport_bind_and_backend_creation(
        tmp_path, monkeypatch):
    from freecad_ai.mcp import gui_server
    from freecad_ai.mcp import transport as transport_mod

    missing = tmp_path / "missing-custom-token"
    backend_calls = []
    controller = ServerController(
        backend_factory=lambda: backend_calls.append(True))
    if not hasattr(gui_server, "resolve_token_file"):
        pytest.fail("missing S9 token startup gate")
    monkeypatch.setattr(
        gui_server, "resolve_token_file", lambda cfg=None: (str(missing), False))
    monkeypatch.setattr(
        transport_mod.HTTPServerTransport, "bind",
        lambda self: pytest.fail("transport bound before token validation"))

    with pytest.raises((OSError, ValueError)):
        controller.start("127.0.0.1", 3131)
    assert backend_calls == []


def test_invalid_bind_scope_precedes_transport_and_backend(monkeypatch):
    from freecad_ai.mcp import gui_server
    from freecad_ai.mcp import transport as transport_mod

    backend_calls = []
    controller = ServerController(
        backend_factory=lambda: backend_calls.append(True))
    monkeypatch.setattr(
        transport_mod, "HTTPServerTransport",
        lambda **kwargs: pytest.fail("transport constructed for public bind"))
    with pytest.raises((OSError, ValueError)):
        controller.start("8.8.8.8", 3131)
    assert backend_calls == []
    assert controller.is_running() is False
    assert hasattr(gui_server, "resolve_private_bind")


def test_controller_binds_validated_numeric_address_and_family_after_one_dns(
        tmp_path, monkeypatch):
    import freecad_ai.config as config_mod
    from freecad_ai.mcp import gui_server
    from freecad_ai.mcp import transport as transport_mod

    calls = []
    token_path = tmp_path / "token"
    token_path.write_text("G" * 43 + "\n")
    cfg = type("Cfg", (), {
        "mcp_server_token_file": str(token_path),
        "mcp_server_rate_limit_per_minute": 60,
        "mcp_server_rate_limit_burst": 20,
        "mcp_server_max_concurrent_requests": 8,
    })()
    monkeypatch.setattr(config_mod, "get_config", lambda: cfg)
    monkeypatch.setattr(
        gui_server, "resolve_token_file", lambda value=None: (str(token_path), False),
        raising=False)
    monkeypatch.setattr(
        gui_server, "load_or_provision_token", lambda path, managed: "G" * 43,
        raising=False)

    def getaddrinfo(host, port, *args, **kwargs):
        calls.append((host, port))
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.9.8.7", port))]

    monkeypatch.setattr(gui_server.socket, "getaddrinfo", getaddrinfo)
    captured = {}

    class FakeTransport:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def bind(self):
            captured["bound"] = True

        def stop(self):
            pass

    class FakeThread:
        def __init__(self, *args, **kwargs):
            self.alive = False

        def start(self):
            self.alive = True

        def is_alive(self):
            return self.alive

        def join(self, timeout=None):
            self.alive = False

    monkeypatch.setattr(transport_mod, "HTTPServerTransport", FakeTransport)
    monkeypatch.setattr(gui_server.threading, "Thread", FakeThread)
    controller = _controller()

    controller.start("cadbox.lan", 3131)

    assert calls == [("cadbox.lan", 3131)]
    assert captured["host"] == "10.9.8.7"
    assert captured["address_family"] == socket.AF_INET
    assert captured["bearer_token"] == "G" * 43
    assert captured["bound"] is True
    assert "cadbox.lan" not in captured.values()


def test_resolve_falls_back_to_defaults_without_config_or_env(monkeypatch):
    monkeypatch.delenv("MCP_HOST", raising=False)
    monkeypatch.delenv("MCP_PORT", raising=False)
    assert resolve_server_address(None) == (DEFAULT_HOST, DEFAULT_PORT)


def test_resolve_prefers_config_over_defaults(monkeypatch):
    monkeypatch.delenv("MCP_HOST", raising=False)
    monkeypatch.delenv("MCP_PORT", raising=False)
    cfg = type("Cfg", (), {"mcp_server_host": "10.0.0.5", "mcp_server_port": 9000})()
    assert resolve_server_address(cfg) == ("10.0.0.5", 9000)


def test_resolve_prefers_env_over_config(monkeypatch):
    monkeypatch.setenv("MCP_HOST", "192.168.1.50")
    monkeypatch.setenv("MCP_PORT", "3131")
    cfg = type("Cfg", (), {"mcp_server_host": "10.0.0.5", "mcp_server_port": 9000})()
    assert resolve_server_address(cfg) == ("192.168.1.50", 3131)


def test_resolve_ignores_a_non_numeric_env_port(monkeypatch):
    monkeypatch.delenv("MCP_HOST", raising=False)
    monkeypatch.setenv("MCP_PORT", "not-a-port")
    cfg = type("Cfg", (), {"mcp_server_host": "10.0.0.5", "mcp_server_port": 9000})()
    assert resolve_server_address(cfg) == ("10.0.0.5", 9000)


# --- allowed-host resolution -----------------------------------------------
#
# Nothing configured must resolve to None, not to the loopback list. The
# transport's own ``allowed_hosts is None`` branch is what rejects a wildcard
# bind; handing it an explicit list — even the identical one — bypasses that
# guard and silently restores the every-client-gets-403 dead end of #60.

def test_allowed_hosts_is_none_when_nothing_is_configured(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    assert resolve_allowed_hosts(None) is None


def test_allowed_hosts_is_none_when_the_config_list_is_empty(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    cfg = type("Cfg", (), {"mcp_server_allowed_hosts": []})()
    assert resolve_allowed_hosts(cfg) is None


def test_allowed_hosts_prefers_config_over_default(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    cfg = type("Cfg", (), {
        "mcp_server_allowed_hosts": ["fileserver.local", "192.168.1.50"]})()
    assert resolve_allowed_hosts(cfg) == ["fileserver.local", "192.168.1.50"]


def test_allowed_hosts_prefers_env_over_config(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "box.lan, 10.0.0.7")
    cfg = type("Cfg", (), {"mcp_server_allowed_hosts": ["ignored.local"]})()
    assert resolve_allowed_hosts(cfg) == ["box.lan", "10.0.0.7"]


def test_allowed_hosts_drops_blank_entries(monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "box.lan, ,, 10.0.0.7,")
    assert resolve_allowed_hosts(None) == ["box.lan", "10.0.0.7"]


def test_allowed_hosts_rejects_a_wildcard_entry(monkeypatch):
    # "*" would re-open exactly the hole #60 declined to open: the Host
    # allowlist is the only thing standing between a wildcard bind and
    # unauthenticated remote tool execution until #59 lands a token.
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "box.lan, *")
    with pytest.raises(ValueError, match=r"\*"):
        resolve_allowed_hosts(None)


def test_allowed_hosts_rejects_a_wildcard_entry_from_config(monkeypatch):
    monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    cfg = type("Cfg", (), {"mcp_server_allowed_hosts": ["*"]})()
    with pytest.raises(ValueError, match=r"\*"):
        resolve_allowed_hosts(cfg)


# --- allowed hosts reach the transport -------------------------------------

def test_explicit_allowed_hosts_admit_a_non_loopback_client():
    # The escape hatch #66's own error message advertises: naming the host
    # clients actually dial makes a non-loopback bind usable.
    controller = _controller()
    port = _free_port()
    try:
        controller.start("127.0.0.1", port,
                         allowed_hosts=["fileserver.local"])
        transport = controller._transport
        assert transport._request_allowed("fileserver.local:%d" % port,
                                          None) is True
    finally:
        controller.stop()


def test_start_without_allowed_hosts_keeps_the_loopback_default():
    controller = _controller()
    port = _free_port()
    try:
        controller.start("127.0.0.1", port)
        transport = controller._transport
        assert transport._request_allowed("evil.example:%d" % port,
                                          None) is False
    finally:
        controller.stop()


# --- lifecycle -------------------------------------------------------------

def test_start_reports_running_and_returns_the_url():
    controller = _controller()
    port = _free_port()
    try:
        url = controller.start("127.0.0.1", port)
        assert url == "http://127.0.0.1:%d/mcp" % port
        assert controller.is_running() is True
        assert controller.url == url
    finally:
        controller.stop()


def test_a_fresh_controller_is_not_running():
    controller = _controller()
    assert controller.is_running() is False
    assert controller.url is None
    assert controller.token_file_path is None


def test_backend_failure_stops_bound_transport_and_leaves_controller_stopped(
        tmp_path, monkeypatch):
    from freecad_ai.mcp import gui_server
    from freecad_ai.mcp import transport as transport_mod

    stopped = []

    class FakeTransport:
        def __init__(self, **kwargs):
            pass

        def bind(self):
            pass

        def stop(self):
            stopped.append(True)

    monkeypatch.setattr(transport_mod, "HTTPServerTransport", FakeTransport)
    monkeypatch.setattr(
        gui_server, "resolve_token_file",
        lambda cfg=None: (str(tmp_path / "token"), True))
    monkeypatch.setattr(
        gui_server, "load_or_provision_token", lambda path, managed: "T" * 43)
    controller = ServerController(
        backend_factory=lambda: (_ for _ in ()).throw(RuntimeError("backend")))

    with pytest.raises(RuntimeError, match="backend"):
        controller.start("127.0.0.1", 3131)

    assert stopped == [True]
    assert controller.is_running() is False
    assert controller.url is None


def test_second_start_is_a_no_op_returning_the_same_url():
    controller = _controller()
    port = _free_port()
    try:
        first = controller.start("127.0.0.1", port)
        second = controller.start("127.0.0.1", port)  # must not raise EADDRINUSE
        assert first == second
    finally:
        controller.stop()


def test_start_on_a_taken_port_raises_and_stays_stopped():
    blocker = socket.socket()
    blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    blocker.bind(("127.0.0.1", 0))
    blocker.listen(1)
    port = blocker.getsockname()[1]
    controller = _controller()
    try:
        with pytest.raises(OSError):
            controller.start("127.0.0.1", port)
        assert controller.is_running() is False
        assert controller.url is None
    finally:
        blocker.close()
        controller.stop()


def test_stop_releases_the_port_for_a_later_start():
    controller = _controller()
    port = _free_port()
    controller.start("127.0.0.1", port)
    controller.stop()
    assert controller.is_running() is False
    try:
        controller.start("127.0.0.1", port)  # must not raise
    finally:
        controller.stop()


def test_stop_is_idempotent_and_safe_before_any_start():
    controller = _controller()
    controller.stop()
    controller.stop()
    assert controller.is_running() is False


def test_the_server_actually_listens_after_start():
    controller = _controller()
    port = _free_port()
    try:
        controller.start("127.0.0.1", port)
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            pass  # connecting is the assertion
    finally:
        controller.stop()


def test_is_running_is_false_once_the_serve_thread_exits():
    controller = _controller()
    port = _free_port()
    controller.start("127.0.0.1", port)
    controller._transport.stop()  # kill the server behind the controller's back
    deadline = time.time() + 5
    while controller.is_running() and time.time() < deadline:
        time.sleep(0.05)
    assert controller.is_running() is False
    controller.stop()


def test_start_reaps_the_socket_a_dead_serve_thread_left_open():
    """A serve thread that dies must not squat the port for the session.

    ``serve_forever()`` returning without ``server_close()`` is exactly what
    an exception inside the serve thread leaves behind: is_running() goes
    False while the listening socket is still open. Before the reap in
    start(), every later start() on that port raised EADDRINUSE until FreeCAD
    was restarted.
    """
    controller = _controller()
    port = _free_port()
    try:
        controller.start("127.0.0.1", port)
        controller._transport._httpd.shutdown()  # thread exits, socket stays
        deadline = time.time() + 5
        while controller.is_running() and time.time() < deadline:
            time.sleep(0.05)
        assert controller.is_running() is False

        controller.start("127.0.0.1", port)  # must not raise EADDRINUSE
        assert controller.is_running() is True
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            pass  # and the new server really owns the port
    finally:
        controller.stop()


def test_the_advertised_url_is_the_streamable_endpoint():
    """The toolbar writes this string to the Report view, so it is the URL
    users copy into a client config. Point it at the transport that is not
    on a removal clock; /sse keeps serving for anyone already on it."""
    controller = _controller()
    port = _free_port()
    try:
        url = controller.start("127.0.0.1", port)
        assert url.endswith("/mcp")
    finally:
        controller.stop()


def test_get_server_controller_returns_one_shared_instance():
    assert get_server_controller() is get_server_controller()
