"""Fail-closed tests for private atomic persistence primitives."""

import importlib
import os
import stat

import pytest


def _storage():
    try:
        return importlib.import_module("freecad_ai.secure_storage")
    except ModuleNotFoundError:
        pytest.fail("missing S7 freecad_ai.secure_storage primitives")


def _mode(path):
    return stat.S_IMODE(os.lstat(path).st_mode)


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode contract")
def test_private_create_and_idempotent_tightening(tmp_path):
    storage = _storage()
    directory = tmp_path / "private"
    storage.ensure_private_dir(str(directory))
    assert _mode(directory) == 0o700
    os.chmod(directory, 0o777)
    storage.ensure_private_dir(str(directory))
    assert _mode(directory) == 0o700

    target = directory / "value.json"
    storage.atomic_write_bytes(str(target), b"one")
    assert target.read_bytes() == b"one"
    assert _mode(target) == 0o600
    os.chmod(target, 0o666)
    storage.atomic_write_bytes(str(target), b"two")
    assert target.read_bytes() == b"two"
    assert _mode(target) == 0o600


@pytest.mark.parametrize("kind", ["directory", "target"])
def test_symlink_directory_and_target_are_rejected(tmp_path, kind):
    storage = _storage()
    real_dir = tmp_path / "real"; real_dir.mkdir()
    if kind == "directory":
        path = tmp_path / "linked"; path.symlink_to(real_dir, target_is_directory=True)
        with pytest.raises((OSError, ValueError)):
            storage.ensure_private_dir(str(path))
    else:
        target = real_dir / "target"; outside = tmp_path / "outside"
        outside.write_bytes(b"unchanged"); target.symlink_to(outside)
        with pytest.raises((OSError, ValueError)):
            storage.atomic_write_bytes(str(target), b"replacement")
        assert outside.read_bytes() == b"unchanged"


@pytest.mark.parametrize("failure", ["write", "fsync", "replace"])
def test_atomic_failures_preserve_previous_file(tmp_path, monkeypatch, failure):
    storage = _storage()
    target = tmp_path / "config.json"; target.write_bytes(b"previous")

    if failure == "write":
        original_fdopen = storage.os.fdopen

        class FailingWriter:
            def __init__(self, delegate):
                self.delegate = delegate

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.delegate.close()
                return False

            def write(self, data):
                raise OSError("injected write failure")

            def flush(self):
                self.delegate.flush()

            def fileno(self):
                return self.delegate.fileno()

        def fail_fdopen(fd, mode="r", *args, **kwargs):
            delegate = original_fdopen(fd, mode, *args, **kwargs)
            return FailingWriter(delegate) if "w" in mode else delegate

        monkeypatch.setattr(storage.os, "fdopen", fail_fdopen)
    elif failure == "fsync":
        monkeypatch.setattr(storage.os, "fsync", lambda fd: (_ for _ in ()).throw(
            OSError("injected fsync failure")))
    else:
        monkeypatch.setattr(storage.os, "replace", lambda *args: (_ for _ in ()).throw(
            OSError("injected replace failure")))

    with pytest.raises(OSError):
        storage.atomic_write_bytes(str(target), b"new")
    assert target.read_bytes() == b"previous"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["config.json"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory fsync contract")
def test_parent_fsync_failure_surfaces_without_partial_target(tmp_path, monkeypatch):
    storage = _storage()
    target = tmp_path / "config.json"; target.write_bytes(b"complete-old")
    calls = 0
    original_fsync = storage.os.fsync

    def fail_second_fsync(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected parent fsync failure")
        return original_fsync(fd)

    monkeypatch.setattr(storage.os, "fsync", fail_second_fsync)
    with pytest.raises(OSError, match="parent fsync"):
        storage.atomic_write_bytes(str(target), b"complete-new")
    assert target.read_bytes() in (b"complete-old", b"complete-new")
    assert sorted(path.name for path in tmp_path.iterdir()) == ["config.json"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory fsync contract")
def test_successful_replace_fsyncs_file_and_parent(tmp_path, monkeypatch):
    storage = _storage()
    calls = []
    monkeypatch.setattr(storage.os, "fsync", lambda fd: calls.append(fd))
    storage.atomic_write_bytes(str(tmp_path / "value"), b"content")
    assert len(calls) >= 2


def test_symlinked_parent_ancestor_is_rejected(tmp_path):
    storage = _storage()
    real = tmp_path / "real"; real.mkdir()
    linked = tmp_path / "linked"; linked.symlink_to(real, target_is_directory=True)
    target = linked / "nested" / "value"
    with pytest.raises((OSError, ValueError)):
        storage.atomic_write_bytes(str(target), b"must not be written")
    assert not (real / "nested").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode contract")
def test_harden_managed_paths_tightens_and_rejects_symlinks(tmp_path):
    storage = _storage()
    directory = tmp_path / "managed"; directory.mkdir(mode=0o777)
    target = directory / "data"; target.write_bytes(b"data")
    os.chmod(directory, 0o777); os.chmod(target, 0o666)
    assert storage.harden_managed_paths((str(directory),), (str(target),)) == []
    assert _mode(directory) == 0o700
    assert _mode(target) == 0o600

    outside = tmp_path / "outside"; outside.write_bytes(b"outside")
    linked = directory / "linked"; linked.symlink_to(outside)
    before = _mode(outside)
    with pytest.raises((OSError, ValueError)):
        storage.harden_managed_paths((), (str(linked),))
    assert _mode(outside) == before


def test_secret_references_are_untouched(tmp_path):
    storage = _storage()
    for value in ("", "file:/private/key", "cmd:security find-generic-password"):
        assert storage.migrate_literal_secret(value, str(tmp_path), "provider") == value
    assert list(tmp_path.iterdir()) == []


def test_literal_secret_is_lossless_and_conflict_allocates_without_overwrite(tmp_path):
    storage = _storage()
    conflict = tmp_path / "provider.secret"; conflict.write_bytes(b"existing")
    reference = storage.migrate_literal_secret(
        "literal-\N{SNOWMAN}-secret", str(tmp_path), "provider")
    path = reference.removeprefix("file:")
    assert os.path.realpath(path) == path
    assert path != str(conflict)
    assert conflict.read_bytes() == b"existing"
    assert os.path.exists(path)
    with open(path, "rb") as stream:
        assert stream.read() == "literal-\N{SNOWMAN}-secret".encode()


def test_migration_requires_exact_readback_and_leaves_no_orphan(tmp_path, monkeypatch):
    storage = _storage()
    original_fdopen = storage.os.fdopen
    calls = 0

    class CorruptReader:
        def __init__(self, delegate):
            self.delegate = delegate

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.delegate.close()
            return False

        def read(self):
            return b"corrupt"

    def corrupt_readback(fd, mode="r", *args, **kwargs):
        nonlocal calls
        calls += 1
        delegate = original_fdopen(fd, mode, *args, **kwargs)
        return CorruptReader(delegate) if calls == 2 else delegate

    monkeypatch.setattr(storage.os, "fdopen", corrupt_readback)
    with pytest.raises((OSError, ValueError)):
        storage.migrate_literal_secret("literal", str(tmp_path), "provider")
    assert list(tmp_path.iterdir()) == []


def test_recursive_redaction_handles_keys_and_exact_values_without_overreach():
    storage = _storage()
    value = {
        "Authorization": "Bearer abc",
        "nested": [{"api_key": "key"}, {"normal": "exact-secret"}],
        "description": "token budget and password policy are ordinary text",
        "count": 7,
    }
    redacted = storage.redact_sensitive(value, exact_secrets={"exact-secret"})
    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["nested"][0]["api_key"] == "[REDACTED]"
    assert redacted["nested"][1]["normal"] == "[REDACTED]"
    assert redacted["description"] == value["description"]
    assert redacted["count"] == 7
    assert value["Authorization"] == "Bearer abc"
