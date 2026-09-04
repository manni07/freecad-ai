"""HTTP MCP authentication, admission and rotation security contracts."""

import http.client
import json
import socketserver
import threading
import time
import urllib.error
import urllib.request

import pytest

from freecad_ai.mcp import protocol
from freecad_ai.mcp.transport import MAX_REQUEST_BODY, HTTPServerTransport

TOKEN = "test-only-token-" + "A" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _echo(msg):
    if msg.get("id") is None:
        return None
    return protocol.make_response(msg["id"], {"ok": True})


class _Server:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        self.transport = HTTPServerTransport(
            host="127.0.0.1", port=0, bearer_token=TOKEN, **self.kwargs)
        self.transport._handler = _echo
        self.httpd = self.transport._make_server()
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


def _request(port, method="POST", path="/mcp", headers=None, data=None):
    merged = dict(headers or {})
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", method=method,
        headers=merged, data=data)
    try:
        response = urllib.request.urlopen(request, timeout=5)
        return response.status, response.read(), response.headers
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), exc.headers


def _ping(port, headers=None, path="/mcp"):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}).encode()
    merged = {"Content-Type": "application/json", **(headers or {})}
    return _request(port, data=body, headers=merged, path=path)


@pytest.mark.parametrize(
    "method", ["GET", "POST", "DELETE", "OPTIONS", "HEAD", "PUT", "PATCH"])
@pytest.mark.parametrize("path", ["/mcp", "/sse", "/messages", "/unknown"])
def test_every_verb_and_route_requires_bearer_before_routing(method, path):
    with _Server() as server:
        status, body, headers = _request(server.port, method=method, path=path)
    assert status == 401
    assert headers.get("WWW-Authenticate") == 'Bearer realm="FreeCAD AI MCP"'
    assert headers.get("Cache-Control") == "no-store"
    assert TOKEN.encode() not in body


@pytest.mark.parametrize("value", [
    "Bearer wrong", "Basic dGVzdA==", "Bearer", "Bearer a b", "Token wrong",
])
def test_wrong_or_malformed_authorization_is_401_without_dispatch(value):
    calls = []
    with _Server() as server:
        server.transport._handler = lambda msg: calls.append(msg)
        status, body, headers = _ping(
            server.port, {"Authorization": value})
    assert status == 401
    assert calls == []
    assert TOKEN.encode() not in body
    assert value.encode() not in body
    assert headers.get("Cache-Control") == "no-store"


def test_duplicate_authorization_headers_are_rejected():
    with _Server() as server:
        connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
        connection.putrequest("POST", "/mcp", skip_host=True)
        connection.putheader("Host", f"127.0.0.1:{server.port}")
        connection.putheader("Authorization", f"Bearer {TOKEN}")
        connection.putheader("Authorization", f"Bearer {TOKEN}")
        connection.putheader("Content-Length", "0")
        connection.endheaders()
        response = connection.getresponse()
        body = response.read()
        connection.close()
    assert response.status == 401
    assert response.getheader("WWW-Authenticate") is not None
    assert TOKEN.encode() not in body


def test_bearer_scheme_is_case_insensitive():
    with _Server() as server:
        status, _, _ = _ping(
            server.port, {"Authorization": f"bearer {TOKEN}"})
    assert status == 200


def test_authentication_precedes_oversized_body_parse_and_dispatch():
    calls = []
    with _Server() as server:
        server.transport._handler = lambda msg: calls.append(msg)
        status, _, _ = _request(
            server.port, data=b"{}",
            headers={"Content-Length": str(MAX_REQUEST_BODY + 1)})
    assert status == 401
    assert calls == []


@pytest.mark.parametrize("bad_header", [
    {"Host": "attacker.example"},
    {"Origin": "https://evil.example"},
])
def test_valid_token_does_not_bypass_host_or_origin_and_leaks_nothing(bad_header):
    headers = {**AUTH, **bad_header}
    with _Server() as server:
        status, body, _ = _ping(server.port, headers)
    assert status == 403
    assert TOKEN.encode() not in body
    assert all(value.encode() not in body for value in bad_header.values())


def test_invalid_host_precedes_invalid_authentication():
    with _Server() as server:
        status, body, _ = _ping(server.port, {
            "Host": "attacker.example", "Authorization": "Bearer wrong"})
    assert status == 403
    assert TOKEN.encode() not in body


def test_rejected_host_and_auth_requests_do_not_consume_rate_capacity(
        monkeypatch):
    import freecad_ai.mcp.transport as transport_mod
    monkeypatch.setattr(transport_mod.time, "monotonic", lambda: 100.0)
    with _Server(rate_limit_per_minute=60, rate_limit_burst=20) as server:
        for _ in range(20):
            assert _ping(server.port, {"Authorization": "Bearer wrong"})[0] == 401
            assert _ping(server.port, {
                **AUTH, "Host": "attacker.example"})[0] == 403
        assert [_ping(server.port, AUTH)[0] for _ in range(20)] == [200] * 20
        assert _ping(server.port, AUTH)[0] == 429


def test_token_bucket_burst_refill_and_retry_after_are_deterministic(monkeypatch):
    import freecad_ai.mcp.transport as transport_mod
    now = [100.0]
    monkeypatch.setattr(transport_mod.time, "monotonic", lambda: now[0])
    with _Server(rate_limit_per_minute=60, rate_limit_burst=20) as server:
        assert [_ping(server.port, AUTH)[0] for _ in range(19)] == [200] * 19
        # The bucket is global to the transport, not separately reset per route.
        assert _ping(server.port, AUTH, path="/messages")[0] == 202
        status, _, headers = _ping(server.port, AUTH)
        assert status == 429
        assert int(headers["Retry-After"]) >= 1
        now[0] += 1.0
        assert _ping(server.port, AUTH)[0] == 200


def test_eight_sse_connections_reject_ninth_before_thread_creation(
        monkeypatch):
    import freecad_ai.mcp.transport as transport_mod
    starts = []
    real_process = socketserver.ThreadingMixIn.process_request
    real_sleep = time.sleep

    def count_process(self, request, client_address):
        starts.append(client_address)
        return real_process(self, request, client_address)

    monkeypatch.setattr(socketserver.ThreadingMixIn, "process_request", count_process)
    monkeypatch.setattr(
        transport_mod.time, "sleep", lambda seconds: real_sleep(min(seconds, 0.01)))
    with _Server(max_concurrent_requests=8) as server:
        streams = []
        try:
            for _ in range(8):
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.port}/sse", headers=AUTH)
                streams.append(urllib.request.urlopen(request, timeout=5))
            status, _, headers = _ping(server.port, AUTH)
            assert status == 503
            assert headers.get("Retry-After") == "1"
            assert len(starts) == 8
        finally:
            for stream in streams:
                stream.close()
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if server.transport._admission._value == 8:
                    break
                real_sleep(0.01)
            else:
                pytest.fail("SSE slots remained occupied after client cleanup")


def test_sse_disconnect_releases_slot_with_bounded_wait(monkeypatch):
    import freecad_ai.mcp.transport as transport_mod
    real_sleep = time.sleep
    monkeypatch.setattr(
        transport_mod.time, "sleep", lambda seconds: real_sleep(min(seconds, 0.01)))
    with _Server(max_concurrent_requests=1) as server:
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.port}/sse", headers=AUTH)
        stream = urllib.request.urlopen(request, timeout=5)
        assert _ping(server.port, AUTH)[0] == 503
        stream.close()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if server.transport._admission._value == 1:
                break
            real_sleep(0.01)
        else:
            pytest.fail("SSE slot was not released after disconnect")
        assert _ping(server.port, AUTH)[0] == 200


def test_thread_start_failure_releases_prethread_permit(monkeypatch):
    real_start = threading.Thread.start
    fail_next = [True]

    def injected_start(thread):
        if fail_next[0]:
            fail_next[0] = False
            raise RuntimeError("injected thread-start failure")
        return real_start(thread)

    with _Server(max_concurrent_requests=1) as server:
        monkeypatch.setattr(threading.Thread, "start", injected_start)
        with pytest.raises((OSError, urllib.error.URLError, http.client.HTTPException)):
            _ping(server.port, AUTH)
        monkeypatch.setattr(threading.Thread, "start", real_start)
        assert _ping(server.port, AUTH)[0] == 200


def test_handler_error_releases_slot_for_the_next_request():
    with _Server(max_concurrent_requests=1) as server:
        server.transport._handler = lambda msg: (_ for _ in ()).throw(
            RuntimeError("injected"))
        assert _ping(server.port, AUTH)[0] == 200
        server.transport._handler = _echo
        assert _ping(server.port, AUTH)[0] == 200


def test_rotation_invalidates_old_token_and_inflight_compare_uses_one_snapshot(
        monkeypatch):
    import freecad_ai.mcp.transport as transport_mod
    entered = threading.Event()
    release = threading.Event()
    real_compare = transport_mod.hmac.compare_digest

    def blocked_compare(left, right):
        entered.set()
        assert release.wait(5)
        return real_compare(left, right)

    with _Server() as server:
        monkeypatch.setattr(transport_mod.hmac, "compare_digest", blocked_compare)
        result = []
        request_thread = threading.Thread(
            target=lambda: result.append(_ping(server.port, AUTH)[0]), daemon=True)
        request_thread.start()
        assert entered.wait(5)
        new_token = "test-only-token-" + "B" * 32
        rotation_done = threading.Event()
        rotation_thread = threading.Thread(
            target=lambda: (
                server.transport.rotate_bearer_token(new_token),
                rotation_done.set()),
            daemon=True,
        )
        rotation_thread.start()
        release.set()
        request_thread.join(timeout=5)
        rotation_thread.join(timeout=5)
        assert not request_thread.is_alive()
        assert not rotation_thread.is_alive()
        assert rotation_done.is_set()
        monkeypatch.setattr(transport_mod.hmac, "compare_digest", real_compare)
        assert result == [200]
        assert _ping(server.port, AUTH)[0] == 401
        assert _ping(server.port, {"Authorization": f"Bearer {new_token}"})[0] == 200


@pytest.mark.parametrize("kwargs", [
    {"bearer_token": ""},
    {"bearer_token": TOKEN, "address_family": socketserver.socket.AF_UNIX},
])
def test_transport_rejects_missing_token_and_unsupported_family(kwargs):
    with pytest.raises(ValueError):
        HTTPServerTransport(**kwargs)


@pytest.mark.parametrize("name,value,attribute,expected", [
    ("rate", 0, "_rate_limit_per_minute", 60),
    ("burst", True, "_rate_limit_burst", 20),
    ("concurrency", "8", "_admission", 8),
])
def test_invalid_limits_fail_to_safe_defaults(name, value, attribute, expected):
    kwargs = {"bearer_token": TOKEN}
    key = {
        "rate": "rate_limit_per_minute",
        "burst": "rate_limit_burst",
        "concurrency": "max_concurrent_requests",
    }[name]
    kwargs[key] = value
    transport = HTTPServerTransport(**kwargs)

    actual = getattr(transport, attribute)
    if attribute == "_admission":
        actual = actual._value
    assert actual == expected


def test_rotation_rejects_empty_token_without_changing_current_token():
    transport = HTTPServerTransport(bearer_token=TOKEN)
    with pytest.raises(ValueError, match="token"):
        transport.rotate_bearer_token("")
    assert transport._bearer_token == TOKEN


def test_malformed_http_request_is_rejected_before_handler_dispatch():
    calls = []
    with _Server() as server:
        server.transport._handler = lambda message: calls.append(message)
        client = __import__("socket").create_connection(
            ("127.0.0.1", server.port), timeout=5)
        try:
            client.sendall(b"NOT HTTP\r\n\r\n")
            response = client.recv(1024)
        finally:
            client.close()

    assert b"Error code: 400" in response
    assert calls == []


def test_overload_send_failure_still_closes_rejected_connection():
    transport = HTTPServerTransport(
        host="127.0.0.1", port=0, bearer_token=TOKEN,
        max_concurrent_requests=1)
    server = transport._make_server()

    class BrokenConnection:
        def __init__(self):
            self.shutdown_called = False
            self.close_called = False

        def sendall(self, data):
            raise OSError("peer disappeared")

        def shutdown(self, how):
            self.shutdown_called = True

        def close(self):
            self.close_called = True

    rejected = BrokenConnection()
    assert transport._admission.acquire(blocking=False)
    try:
        server.process_request(rejected, ("127.0.0.1", 1))
    finally:
        transport._admission.release()
        server.server_close()

    assert rejected.shutdown_called is True
    assert rejected.close_called is True
