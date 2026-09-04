"""Security contract tests for the installation-scoped HTTP MCP token."""

import base64
import os
import stat

import pytest


def _api():
    from freecad_ai.mcp import gui_server

    required = ("resolve_token_file", "load_or_provision_token")
    missing = [name for name in required if not hasattr(gui_server, name)]
    if missing:
        pytest.fail("missing S9 token API: " + ", ".join(missing))
    return gui_server


def _mode(path):
    return stat.S_IMODE(os.lstat(path).st_mode)


@pytest.mark.skipif(os.name == "nt", reason="POSIX token-file contract")
def test_managed_token_is_exclusive_private_high_entropy_and_idempotent(
        tmp_path, monkeypatch):
    api = _api()
    monkeypatch.setattr(api, "CONFIG_DIR", str(tmp_path))
    generated = []
    real_generate = api.secrets.token_urlsafe

    def generate(byte_count):
        generated.append(byte_count)
        return real_generate(byte_count)

    monkeypatch.setattr(api.secrets, "token_urlsafe", generate)
    path, managed = api.resolve_token_file(None)

    first = api.load_or_provision_token(path, managed)
    before = os.lstat(path)
    second = api.load_or_provision_token(path, managed)

    assert managed is True
    assert os.path.realpath(path) == str(tmp_path / "mcp_server.token")
    assert first == second
    assert generated == [32]
    decoded = base64.urlsafe_b64decode(first + "=" * (-len(first) % 4))
    assert len(decoded) >= 32
    assert all(char.isalnum() or char in "-_" for char in first)
    assert _mode(path) == 0o600
    assert os.lstat(path).st_ino == before.st_ino
    with open(path, "rb") as stream:
        assert stream.read() == first.encode() + b"\n"


@pytest.mark.skipif(os.name == "nt", reason="POSIX token-file contract")
def test_existing_managed_token_is_tightened_without_replacement(tmp_path):
    api = _api()
    path = tmp_path / "mcp_server.token"
    token = "D" * 43
    path.write_text(token + "\n")
    os.chmod(path, 0o644)
    before = os.lstat(path)

    assert api.load_or_provision_token(str(path), True) == token

    after = os.lstat(path)
    assert after.st_ino == before.st_ino
    assert after.st_mtime_ns == before.st_mtime_ns
    assert path.read_bytes() == token.encode() + b"\n"
    assert stat.S_IMODE(after.st_mode) == 0o600


@pytest.mark.skipif(os.name == "nt", reason="POSIX token-file contract")
@pytest.mark.parametrize("kind", ["symlink", "directory", "malformed"])
def test_managed_default_conflict_fails_without_replacing_target(
        tmp_path, kind):
    api = _api()
    path = tmp_path / "mcp_server.token"
    outside = tmp_path / "outside"
    outside.write_bytes(b"do-not-touch")
    if kind == "symlink":
        path.symlink_to(outside)
    elif kind == "directory":
        path.mkdir()
    else:
        path.write_text("predictable")
        os.chmod(path, 0o600)

    with pytest.raises((OSError, ValueError)):
        api.load_or_provision_token(str(path), True)

    assert outside.read_bytes() == b"do-not-touch"
    if kind == "malformed":
        assert path.read_text() == "predictable"


@pytest.mark.skipif(os.name == "nt", reason="POSIX token-file contract")
@pytest.mark.parametrize(
    "kind", ["missing", "symlink", "directory", "broad", "empty", "malformed"])
def test_custom_token_is_strictly_read_only_and_unsafe_inputs_fail_closed(
        tmp_path, monkeypatch, kind):
    api = _api()
    path = tmp_path / "custom.token"
    outside = tmp_path / "outside"
    outside.write_text("A" * 43 + "\n")
    if kind == "symlink":
        path.symlink_to(outside)
    elif kind == "directory":
        path.mkdir()
    elif kind != "missing":
        content = {"empty": "", "malformed": "short"}.get(kind, "B" * 43 + "\n")
        path.write_text(content)
        os.chmod(path, 0o644 if kind == "broad" else 0o600)

    mutations = []
    monkeypatch.setattr(api.os, "chmod", lambda *args: mutations.append("chmod"))
    monkeypatch.setattr(api.os, "replace", lambda *args: mutations.append("replace"))
    monkeypatch.setattr(api.os, "rename", lambda *args: mutations.append("rename"))
    monkeypatch.setattr(api.os, "unlink", lambda *args: mutations.append("unlink"))
    before = None
    if path.exists() and path.is_file():
        info = os.lstat(path)
        before = (path.read_bytes(), info.st_ino, stat.S_IMODE(info.st_mode),
                  info.st_mtime_ns)

    with pytest.raises((OSError, ValueError)):
        api.load_or_provision_token(str(path), False)

    assert mutations == []
    assert not path.exists() if kind == "missing" else True
    if before is not None:
        info = os.lstat(path)
        assert (path.read_bytes(), info.st_ino, stat.S_IMODE(info.st_mode),
                info.st_mtime_ns) == before


@pytest.mark.skipif(os.name == "nt", reason="POSIX token-file contract")
def test_custom_token_swap_between_lstat_and_open_is_rejected_on_same_fd(
        tmp_path, monkeypatch):
    api = _api()
    path = tmp_path / "custom.token"
    attacker = tmp_path / "attacker.token"
    path.write_text("E" * 43 + "\n")
    attacker.write_text("F" * 43 + "\n")
    os.chmod(path, 0o600)
    os.chmod(attacker, 0o600)
    real_lstat = api.os.lstat
    real_open = api.os.open
    swapped = False
    open_flags = []

    def swap_after_lstat(candidate):
        nonlocal swapped
        info = real_lstat(candidate)
        if os.fspath(candidate) == str(path) and not swapped:
            swapped = True
            os.replace(attacker, path)
        return info

    def record_open(candidate, flags, *args):
        open_flags.append(flags)
        return real_open(candidate, flags, *args)

    monkeypatch.setattr(api.os, "lstat", swap_after_lstat)
    monkeypatch.setattr(api.os, "open", record_open)

    with pytest.raises((OSError, ValueError)):
        api.load_or_provision_token(str(path), False)

    assert swapped is True
    assert open_flags
    assert open_flags[0] & getattr(os, "O_NOFOLLOW", 0)
    assert path.read_text() == "F" * 43 + "\n"


@pytest.mark.skipif(not hasattr(os, "getuid"), reason="POSIX ownership contract")
def test_custom_token_wrong_owner_fails_before_any_mutation(tmp_path, monkeypatch):
    api = _api()
    path = tmp_path / "custom.token"
    path.write_text("C" * 43 + "\n")
    os.chmod(path, 0o600)
    real_lstat = api.os.lstat

    def wrong_owner(candidate):
        info = real_lstat(candidate)
        values = list(info)
        values[4] = os.getuid() + 1
        return os.stat_result(values)

    monkeypatch.setattr(api.os, "lstat", wrong_owner)
    with pytest.raises((OSError, ValueError)):
        api.load_or_provision_token(str(path), False)
    assert path.read_text() == "C" * 43 + "\n"


def test_custom_path_resolves_canonically_but_is_never_provisioned(
        tmp_path, monkeypatch):
    api = _api()
    configured = tmp_path / "missing.token"
    cfg = type("Cfg", (), {"mcp_server_token_file": str(configured)})()
    path, managed = api.resolve_token_file(cfg)
    assert path == os.path.realpath(configured)
    assert managed is False
    assert not configured.exists()


def test_custom_token_path_symlink_is_rejected_during_resolution(
        tmp_path, monkeypatch):
    api = _api()
    outside = tmp_path / "outside.token"
    outside.write_text("A" * 43 + "\n")
    configured = tmp_path / "custom.token"
    configured.symlink_to(outside)
    monkeypatch.setenv("MCP_TOKEN_FILE", str(configured))

    with pytest.raises(ValueError, match="symlink"):
        api.resolve_token_file(None)


def test_token_validation_rejects_non_ascii_and_invalid_base64(monkeypatch):
    api = _api()
    with pytest.raises(ValueError, match="malformed"):
        api._validate_token_bytes("é".encode())
    with pytest.raises(ValueError, match="malformed"):
        api._validate_token_bytes(b"A" * 45)

    monkeypatch.setattr(api.base64, "b64decode", lambda *args, **kwargs: b"x" * 31)
    with pytest.raises(ValueError, match="entropy"):
        api._validate_token_bytes(b"A" * 43)


@pytest.mark.skipif(os.name == "nt", reason="POSIX same-FD token contract")
@pytest.mark.parametrize("failure", ["nonregular", "owner", "mode"])
def test_token_same_fd_revalidates_type_owner_and_mode(
        tmp_path, monkeypatch, failure):
    api = _api()
    path = tmp_path / "custom.token"
    path.write_text("A" * 43 + "\n")
    os.chmod(path, 0o600)
    real_fstat = api.os.fstat

    def changed_fstat(fd):
        info = real_fstat(fd)
        values = list(info)
        if failure == "nonregular":
            values[0] = stat.S_IFDIR | 0o700
        elif failure == "owner":
            values[4] = os.getuid() + 1
        else:
            values[0] = stat.S_IFREG | 0o644
        return os.stat_result(values)

    monkeypatch.setattr(api.os, "fstat", changed_fstat)
    with pytest.raises((OSError, ValueError)):
        api.load_or_provision_token(str(path), False)


@pytest.mark.skipif(os.name == "nt", reason="POSIX managed-mode contract")
def test_existing_managed_token_fails_if_same_fd_mode_cannot_be_tightened(
        tmp_path, monkeypatch):
    api = _api()
    path = tmp_path / "managed.token"
    path.write_text("A" * 43 + "\n")
    os.chmod(path, 0o644)
    monkeypatch.setattr(api.os, "fchmod", lambda fd, mode: None)

    with pytest.raises(OSError, match="permissions"):
        api.load_or_provision_token(str(path), True)


def test_managed_creation_race_loads_exclusively_created_winner(
        tmp_path, monkeypatch):
    api = _api()
    path = tmp_path / "managed.token"
    path.write_text("R" * 43 + "\n")
    real_lexists = api.os.path.lexists
    checks = 0

    def absent_on_precheck(candidate):
        nonlocal checks
        checks += 1
        if checks == 1:
            return False
        return real_lexists(candidate)

    monkeypatch.setattr(api.os.path, "lexists", absent_on_precheck)
    assert api.load_or_provision_token(str(path), True) == "R" * 43


@pytest.mark.skipif(os.name == "nt", reason="POSIX cleanup contract")
def test_failed_managed_write_removes_only_the_created_token(
        tmp_path, monkeypatch):
    api = _api()
    path = tmp_path / "managed.token"
    real_fdopen = api.os.fdopen

    class FailingStream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def write(self, data):
            raise OSError("injected token write failure")

    monkeypatch.setattr(
        api.os, "fdopen",
        lambda fd, *args, **kwargs: FailingStream(
            real_fdopen(fd, *args, **kwargs)))

    with pytest.raises(OSError, match="injected token write failure"):
        api.load_or_provision_token(str(path), True)

    assert not path.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor cleanup contract")
def test_creation_failure_closes_descriptor_even_if_cleanup_unlink_fails(
        tmp_path, monkeypatch):
    api = _api()
    path = tmp_path / "managed.token"
    real_fstat = api.os.fstat
    closed = []
    real_close = api.os.close

    def insecure_mode(fd):
        info = real_fstat(fd)
        values = list(info)
        values[0] = stat.S_IFREG | 0o644
        return os.stat_result(values)

    def recording_close(fd):
        closed.append(fd)
        return real_close(fd)

    with monkeypatch.context() as scoped:
        scoped.setattr(api.os, "fstat", insecure_mode)
        scoped.setattr(api.os, "fchmod", lambda fd, mode: None)
        scoped.setattr(api.os, "close", recording_close)
        scoped.setattr(
            api.os, "unlink",
            lambda candidate: (_ for _ in ()).throw(OSError("unlink blocked")))
        with pytest.raises(OSError, match="permissions"):
            api.load_or_provision_token(str(path), True)

    assert closed
    path.unlink()
