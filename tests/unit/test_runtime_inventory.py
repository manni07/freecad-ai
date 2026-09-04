"""Isolated contracts for the actual FreeCAD-host runtime CycloneDX BOM."""

import importlib
import json
import os
import stat
import sys
import types
import uuid

import pytest


def _inventory_module():
    try:
        return importlib.import_module("freecad_ai.runtime_inventory")
    except ModuleNotFoundError:
        pytest.fail("missing S12 freecad_ai.runtime_inventory module")


def _install_runtime(monkeypatch, inventory, *, binding=6, missing=None):
    """Install only synthetic host modules; never inspect a real FreeCAD."""
    freecad = types.ModuleType("FreeCAD")
    freecad.Version = lambda: [] if missing == "FreeCAD" else ["1", "1", "2", "test"]
    monkeypatch.setitem(sys.modules, "FreeCAD", freecad)

    active_name = f"PySide{binding}"
    inactive_name = "PySide2" if binding == 6 else "PySide6"
    active = types.ModuleType(active_name)
    if missing != "PySide":
        active.__version__ = f"{binding}.8.3"
    inactive = types.ModuleType(inactive_name)
    inactive.__version__ = "99.99.99"
    qtcore = types.ModuleType(f"{active_name}.QtCore")
    qtcore.qVersion = lambda: "" if missing == "Qt" else "6.8.3"
    active.QtCore = qtcore
    active.QtWidgets = types.ModuleType(f"{active_name}.QtWidgets")
    active.QtGui = types.ModuleType(f"{active_name}.QtGui")
    monkeypatch.setitem(sys.modules, active_name, active)
    monkeypatch.setitem(sys.modules, f"{active_name}.QtCore", qtcore)
    monkeypatch.setitem(sys.modules, inactive_name, inactive)

    import freecad_ai
    from freecad_ai.ui import compat

    monkeypatch.setattr(compat, "PYSIDE_VERSION", binding)
    monkeypatch.setattr(compat, "QtCore", qtcore)

    monkeypatch.setattr(
        freecad_ai, "__version__", "" if missing == "FreeCAD AI" else "0.23.1-alpha")
    version_info = () if missing == "Python" else (3, 11, 9, "final", 0)
    fake_sys = types.SimpleNamespace(
        version_info=version_info,
        executable="/private/Users/identity/secret-python",
        modules=sys.modules,
    )
    monkeypatch.setattr(inventory, "sys", fake_sys)
    return inventory.collect_runtime_components()


def _by_name(components):
    return {component["name"]: component for component in components}


def _parent_security_metadata(path):
    info = os.lstat(path)
    return (info.st_dev, info.st_ino, info.st_uid, info.st_gid,
            stat.S_IMODE(info.st_mode))


def test_collector_finds_exact_required_runtime_versions(monkeypatch):
    inventory = _inventory_module()
    found = _by_name(_install_runtime(monkeypatch, inventory, binding=6))

    assert set(found) == {"FreeCAD AI", "FreeCAD", "Python", "PySide", "Qt"}
    assert found["FreeCAD AI"]["version"] == "0.23.1-alpha"
    assert found["FreeCAD"]["version"] == "1.1.2"
    assert found["Python"]["version"] == "3.11.9"
    assert found["PySide"]["version"] == "6.8.3"
    assert found["Qt"]["version"] == "6.8.3"


def test_collector_uses_active_pyside_binding_not_installed_decoy(monkeypatch):
    inventory = _inventory_module()
    found = _by_name(_install_runtime(monkeypatch, inventory, binding=2))
    assert found["PySide"]["version"] == "2.8.3"
    assert found["PySide"]["version"] != "99.99.99"


def test_cyclonedx_15_has_exactly_five_unique_components(monkeypatch):
    inventory = _inventory_module()
    components = _install_runtime(monkeypatch, inventory)
    bom = inventory.build_cyclonedx_bom(components)

    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] == "1.5"
    assert bom["version"] == 1
    assert len(bom["components"]) == 5
    assert {item["name"] for item in bom["components"]} == {
        "FreeCAD AI", "FreeCAD", "Python", "PySide", "Qt"}
    refs = [item["bom-ref"] for item in bom["components"]]
    assert len(refs) == len(set(refs)) == 5
    assert all(ref and isinstance(ref, str) for ref in refs)


def test_bom_refs_and_dependency_edges_are_semantically_stable(monkeypatch):
    inventory = _inventory_module()
    components = _install_runtime(monkeypatch, inventory)
    first = inventory.build_cyclonedx_bom(components)
    second = inventory.build_cyclonedx_bom(list(reversed(components)))
    first_serial = first.pop("serialNumber")
    second_serial = second.pop("serialNumber")

    assert first == second
    assert first_serial != second_serial
    for serial in (first_serial, second_serial):
        assert serial.startswith("urn:uuid:")
        uuid.UUID(serial.removeprefix("urn:uuid:"))


def test_application_depends_on_all_four_host_components(monkeypatch):
    inventory = _inventory_module()
    components = _install_runtime(monkeypatch, inventory)
    bom = inventory.build_cyclonedx_bom(components)
    refs = {item["name"]: item["bom-ref"] for item in bom["components"]}
    edges = {item["ref"]: item["dependsOn"] for item in bom["dependencies"]}

    assert set(edges) == set(refs.values())
    assert set(edges[refs["FreeCAD AI"]]) == {
        refs["FreeCAD"], refs["Python"], refs["PySide"], refs["Qt"]}
    for name in ("FreeCAD", "Python", "PySide", "Qt"):
        assert edges[refs[name]] == []


@pytest.mark.parametrize("missing", [
    "FreeCAD AI", "FreeCAD", "Python", "PySide", "Qt",
])
def test_collector_fails_hard_when_any_required_version_is_missing(
        monkeypatch, missing):
    inventory = _inventory_module()
    with pytest.raises((RuntimeError, ValueError), match=missing):
        _install_runtime(monkeypatch, inventory, missing=missing)


@pytest.mark.parametrize("missing", [
    "FreeCAD AI", "FreeCAD", "Python", "PySide", "Qt",
])
def test_cli_missing_runtime_returns_nonzero_and_writes_no_bom(
        tmp_path, monkeypatch, missing):
    inventory = _inventory_module()
    output = tmp_path / "runtime.cdx.json"

    def fail_collection():
        raise RuntimeError(f"missing {missing}")

    monkeypatch.setattr(inventory, "collect_runtime_components", fail_collection)
    assert inventory.main(["--output", str(output)]) != 0
    assert not output.exists()


def test_bom_contains_no_local_identity_environment_or_secret(
        monkeypatch):
    inventory = _inventory_module()
    components = _install_runtime(monkeypatch, inventory)
    leaks = {
        "username": "audit-user-unique",
        "hostname": "audit-host-unique.local",
        "executable": "/private/Users/audit-user-unique/bin/python",
        "config": "/private/Users/audit-user-unique/.config/freecad-ai",
        "environment": "audit-environment-value-unique",
        "token": "audit-token-value-unique",
        "secret": "audit-secret-value-unique",
    }
    monkeypatch.setenv("USER", leaks["username"])
    monkeypatch.setenv("HOSTNAME", leaks["hostname"])
    monkeypatch.setenv("FREECAD_AI_CONFIG_DIR", leaks["config"])
    monkeypatch.setenv("MCP_TOKEN", leaks["token"])
    monkeypatch.setenv("AUDIT_SECRET", leaks["secret"])
    monkeypatch.setenv("AUDIT_ENV", leaks["environment"])
    monkeypatch.setattr(inventory.os, "getlogin", lambda: leaks["username"])
    if hasattr(inventory, "socket"):
        monkeypatch.setattr(inventory.socket, "gethostname", lambda: leaks["hostname"])

    encoded = json.dumps(inventory.build_cyclonedx_bom(components), sort_keys=True)
    assert all(value not in encoded for value in leaks.values())
    assert os.environ["AUDIT_SECRET"] not in encoded


@pytest.mark.skipif(os.name == "nt", reason="POSIX private-file contract")
def test_explicit_output_is_complete_private_json(tmp_path, monkeypatch):
    inventory = _inventory_module()
    expected = _install_runtime(monkeypatch, inventory)
    output = tmp_path / "runtime.cdx.json"

    inventory.write_runtime_bom(str(output))

    saved = json.loads(output.read_text())
    assert saved["bomFormat"] == "CycloneDX"
    assert len(saved["components"]) == len(expected) == 5
    assert stat.S_IMODE(output.stat().st_mode) == 0o600


@pytest.mark.skipif(os.name == "nt", reason="POSIX parent-mode contract")
def test_success_never_changes_existing_output_parent_security_metadata(
        tmp_path, monkeypatch):
    inventory = _inventory_module()
    _install_runtime(monkeypatch, inventory)
    parent = tmp_path / "shared-output"
    parent.mkdir(mode=0o750)
    os.chmod(parent, 0o750)
    output = parent / "runtime.cdx.json"
    output.write_text("previous complete output", encoding="utf-8")
    before = _parent_security_metadata(parent)

    inventory.write_runtime_bom(output)

    assert _parent_security_metadata(parent) == before
    assert json.loads(output.read_text(encoding="utf-8"))["bomFormat"] == "CycloneDX"
    assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_explicit_output_rejects_symlink_without_touching_target(
        tmp_path, monkeypatch):
    inventory = _inventory_module()
    _install_runtime(monkeypatch, inventory)
    parent = tmp_path / "shared-output"
    parent.mkdir(mode=0o750)
    os.chmod(parent, 0o750)
    before_parent = _parent_security_metadata(parent)
    outside = tmp_path / "outside.json"
    outside.write_text("do-not-touch")
    output = parent / "runtime.cdx.json"
    output.symlink_to(outside)

    with pytest.raises((OSError, ValueError)):
        inventory.write_runtime_bom(str(output))

    assert outside.read_text() == "do-not-touch"
    assert output.is_symlink()
    assert _parent_security_metadata(parent) == before_parent


def test_atomic_output_failure_preserves_previous_complete_file(
        tmp_path, monkeypatch):
    inventory = _inventory_module()
    _install_runtime(monkeypatch, inventory)
    output = tmp_path / "runtime.cdx.json"
    output.write_bytes(b"previous-complete-bom")

    def fail_atomic(*args, **kwargs):
        raise OSError("injected BOM atomic failure")

    monkeypatch.setattr(inventory, "atomic_write_json", fail_atomic)
    with pytest.raises(OSError, match="BOM atomic"):
        inventory.write_runtime_bom(str(output))
    assert output.read_bytes() == b"previous-complete-bom"


def test_cli_success_writes_requested_path_only(tmp_path, monkeypatch):
    inventory = _inventory_module()
    components = _install_runtime(monkeypatch, inventory)
    output = tmp_path / "chosen" / "runtime.cdx.json"
    monkeypatch.setattr(
        inventory, "collect_runtime_components", lambda: components)

    assert inventory.main(["--output", str(output)]) == 0
    assert json.loads(output.read_text())["specVersion"] == "1.5"
    assert sorted(path for path in tmp_path.rglob("*") if path.is_file()) == [output]


@pytest.mark.parametrize("payload", [
    "/Users/alice/.config/freecad-ai/token",
    r"C:\Users\alice\AppData\secret",
    "6.8.3\nTOKEN=do-not-emit",
    "A" * 257,
    "password=do-not-emit",
])
def test_unsafe_version_payload_is_rejected_before_bom_or_write(
        tmp_path, monkeypatch, payload):
    inventory = _inventory_module()
    components = _install_runtime(monkeypatch, inventory)
    poisoned = [dict(component) for component in components]
    poisoned[3]["version"] = payload

    with pytest.raises(ValueError):
        inventory.build_cyclonedx_bom(poisoned)

    writes = []
    monkeypatch.setattr(inventory, "collect_runtime_components", lambda: poisoned)
    monkeypatch.setattr(
        inventory, "atomic_write_json",
        lambda *args, **kwargs: writes.append((args, kwargs)))
    output = tmp_path / "runtime.cdx.json"
    with pytest.raises(ValueError):
        inventory.write_runtime_bom(output)
    assert writes == []
    assert not output.exists()


def test_known_runtime_version_spellings_remain_valid(monkeypatch):
    inventory = _inventory_module()
    components = _install_runtime(monkeypatch, inventory)
    bom = inventory.build_cyclonedx_bom(components)
    assert {item["version"] for item in bom["components"]} == {
        "0.23.1-alpha", "1.1.2", "3.11.9", "6.8.3"}


def test_non_mapping_component_is_a_value_error_without_partial_bom(
        monkeypatch):
    inventory = _inventory_module()
    components = _install_runtime(monkeypatch, inventory)
    components[2] = "Python=3.11.9"

    with pytest.raises(ValueError, match="component"):
        inventory.build_cyclonedx_bom(components)


def _stat_with_mode(info, mode):
    values = list(info)
    values[0] = mode
    return os.stat_result(values)


def _assert_no_temporary_bom(parent):
    assert not list(parent.glob(".runtime.cdx.json.tmp-*"))


def test_atomic_writer_pins_parent_and_uses_relative_dir_fd_operations(
        tmp_path, monkeypatch):
    """A checked pathname must not be re-resolved for the commit."""
    inventory = _inventory_module()
    _install_runtime(monkeypatch, inventory)
    output = tmp_path / "runtime.cdx.json"
    real_open = os.open
    real_replace = os.replace
    opens = []
    replacements = []

    def recording_open(path, flags, mode=0o777, *, dir_fd=None):
        opens.append((os.fspath(path), flags, dir_fd))
        return real_open(path, flags, mode, dir_fd=dir_fd)

    def recording_replace(src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        replacements.append(
            (os.fspath(src), os.fspath(dst), src_dir_fd, dst_dir_fd))
        return real_replace(
            src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(inventory.os, "open", recording_open)
    monkeypatch.setattr(inventory.os, "replace", recording_replace)

    inventory.write_runtime_bom(output)

    assert replacements
    _, _, src_dir_fd, dst_dir_fd = replacements[-1]
    if os.name == "nt":
        assert src_dir_fd is None and dst_dir_fd is None
        assert json.loads(output.read_text(encoding="utf-8"))["bomFormat"] == "CycloneDX"
        return
    assert src_dir_fd is not None
    assert src_dir_fd == dst_dir_fd
    assert any(
        ".runtime.cdx.json.tmp-" in path
        and not os.path.isabs(path)
        and dir_fd == src_dir_fd
        and flags & os.O_EXCL
        for path, flags, dir_fd in opens
    )
    assert any(
        os.path.abspath(path) == os.path.abspath(tmp_path)
        and flags & getattr(os, "O_DIRECTORY", 0)
        and flags & getattr(os, "O_NOFOLLOW", 0)
        for path, flags, _ in opens
    )


@pytest.mark.skipif(os.name == "nt", reason="POSIX inode identity contract")
def test_temp_inode_mismatch_preserves_old_target_and_cleans_only_own_temp(
        tmp_path, monkeypatch):
    inventory = _inventory_module()
    _install_runtime(monkeypatch, inventory)
    output = tmp_path / "runtime.cdx.json"
    output.write_bytes(b"previous-complete-bom")
    innocent = tmp_path / ".runtime.cdx.json.tmp-innocent"
    innocent.write_bytes(b"not-owned-by-writer")
    real_stat = os.stat
    injected = False

    def mismatching_stat(path, *args, **kwargs):
        nonlocal injected
        info = real_stat(path, *args, **kwargs)
        if (not injected and ".runtime.cdx.json.tmp-" in os.fspath(path)
                and os.fspath(path) != innocent.name
                and kwargs.get("dir_fd") is not None
                and kwargs.get("follow_symlinks") is False):
            injected = True
            values = list(info)
            values[1] += 1
            return os.stat_result(values)
        return info

    monkeypatch.setattr(inventory.os, "stat", mismatching_stat)

    with pytest.raises(OSError, match="temporary|inode|identity"):
        inventory.write_runtime_bom(output)

    assert injected
    assert output.read_bytes() == b"previous-complete-bom"
    assert innocent.read_bytes() == b"not-owned-by-writer"
    assert sorted(tmp_path.glob(".runtime.cdx.json.tmp-*")) == [innocent]


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory-fd confinement")
def test_parent_path_swap_is_confined_to_pinned_directory(
        tmp_path, monkeypatch):
    inventory = _inventory_module()
    _install_runtime(monkeypatch, inventory)
    parent = tmp_path / "selected"
    parent.mkdir()
    output = parent / "runtime.cdx.json"
    output.write_bytes(b"previous-complete-bom")
    moved_parent = tmp_path / "selected-pinned"
    outside = tmp_path / "outside"
    outside.mkdir()
    real_replace = os.replace
    swapped = False

    def swap_parent_then_replace(
            src, dst, *, src_dir_fd=None, dst_dir_fd=None):
        nonlocal swapped
        if not swapped:
            swapped = True
            parent.rename(moved_parent)
            parent.symlink_to(outside, target_is_directory=True)
            if src_dir_fd is None:
                (outside / os.path.basename(os.fspath(src))).write_bytes(
                    b"attacker-controlled-redirection")
        return real_replace(
            src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(inventory.os, "replace", swap_parent_then_replace)

    inventory.write_runtime_bom(output)

    assert swapped
    assert not (outside / "runtime.cdx.json").exists()
    saved = json.loads(
        (moved_parent / "runtime.cdx.json").read_text(encoding="utf-8"))
    assert saved["bomFormat"] == "CycloneDX"


@pytest.mark.parametrize("payload", [
    "\n6.8.3",
    "6.8.3\t",
    "audit-host.example",
    "Users.alice.private.freecad-ai",
])
def test_raw_identity_or_whitespace_version_is_rejected_without_echo(
        monkeypatch, payload):
    inventory = _inventory_module()
    components = _install_runtime(monkeypatch, inventory)
    poisoned = [dict(component) for component in components]
    poisoned[3]["version"] = payload

    with pytest.raises(ValueError) as caught:
        inventory.build_cyclonedx_bom(poisoned)

    assert payload not in str(caught.value)


@pytest.mark.parametrize("version", [
    "0", "1.0", "3.11.9", "6.8.3", "0.23.1-alpha",
])
def test_strict_version_validator_keeps_known_numeric_spellings(
        monkeypatch, version):
    inventory = _inventory_module()
    components = _install_runtime(monkeypatch, inventory)
    candidate = [dict(component) for component in components]
    candidate[0]["version"] = version

    bom = inventory.build_cyclonedx_bom(candidate)

    assert bom["components"][0]["version"] == version


def test_real_writer_write_failure_preserves_old_target(
        tmp_path, monkeypatch):
    inventory = _inventory_module()
    _install_runtime(monkeypatch, inventory)
    output = tmp_path / "runtime.cdx.json"
    output.write_bytes(b"previous-complete-bom")
    real_fdopen = os.fdopen

    class FailingWriter:
        def __init__(self, stream):
            self._stream = stream

        def __enter__(self):
            self._stream.__enter__()
            return self

        def __exit__(self, *args):
            return self._stream.__exit__(*args)

        def write(self, _data):
            raise OSError("injected write failure")

    def failing_fdopen(fd, *args, **kwargs):
        return FailingWriter(real_fdopen(fd, *args, **kwargs))

    monkeypatch.setattr(inventory.os, "fdopen", failing_fdopen)

    with pytest.raises(OSError, match="injected write failure"):
        inventory.write_runtime_bom(output)

    assert output.read_bytes() == b"previous-complete-bom"
    _assert_no_temporary_bom(tmp_path)


def test_real_writer_file_fsync_failure_preserves_old_target(
        tmp_path, monkeypatch):
    inventory = _inventory_module()
    _install_runtime(monkeypatch, inventory)
    output = tmp_path / "runtime.cdx.json"
    output.write_bytes(b"previous-complete-bom")
    real_fsync = os.fsync

    def failing_file_fsync(fd):
        if stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("injected file fsync failure")
        return real_fsync(fd)

    monkeypatch.setattr(inventory.os, "fsync", failing_file_fsync)

    with pytest.raises(OSError, match="injected file fsync failure"):
        inventory.write_runtime_bom(output)

    assert output.read_bytes() == b"previous-complete-bom"
    _assert_no_temporary_bom(tmp_path)


def test_real_writer_replace_failure_preserves_old_target(
        tmp_path, monkeypatch):
    inventory = _inventory_module()
    _install_runtime(monkeypatch, inventory)
    output = tmp_path / "runtime.cdx.json"
    output.write_bytes(b"previous-complete-bom")

    def failing_replace(*args, **kwargs):
        raise OSError("injected replace failure")

    monkeypatch.setattr(inventory.os, "replace", failing_replace)

    with pytest.raises(OSError, match="injected replace failure"):
        inventory.write_runtime_bom(output)

    assert output.read_bytes() == b"previous-complete-bom"
    _assert_no_temporary_bom(tmp_path)


@pytest.mark.skipif(os.name == "nt", reason="POSIX final-mode verification")
def test_real_writer_final_mode_failure_is_loud_after_complete_commit(
        tmp_path, monkeypatch):
    inventory = _inventory_module()
    _install_runtime(monkeypatch, inventory)
    output = tmp_path / "runtime.cdx.json"
    output.write_bytes(b"previous-complete-bom")
    real_lstat = os.lstat
    real_stat = os.stat
    real_replace = os.replace
    committed = False

    def recording_replace(*args, **kwargs):
        nonlocal committed
        result = real_replace(*args, **kwargs)
        committed = True
        return result

    def insecure_final_mode(path, *args, **kwargs):
        info = real_lstat(path, *args, **kwargs)
        if committed and os.path.abspath(os.fspath(path)) == os.path.abspath(output):
            return _stat_with_mode(info, stat.S_IFREG | 0o644)
        return info

    def insecure_final_mode_at(path, *args, **kwargs):
        info = real_stat(path, *args, **kwargs)
        if committed and os.path.basename(os.fspath(path)) == output.name:
            return _stat_with_mode(info, stat.S_IFREG | 0o644)
        return info

    monkeypatch.setattr(inventory.os, "replace", recording_replace)
    monkeypatch.setattr(inventory.os, "lstat", insecure_final_mode)
    monkeypatch.setattr(inventory.os, "stat", insecure_final_mode_at)

    with pytest.raises(OSError, match="permissions|mode"):
        inventory.write_runtime_bom(output)

    assert committed
    assert json.loads(output.read_text(encoding="utf-8"))["bomFormat"] == "CycloneDX"
    _assert_no_temporary_bom(tmp_path)


@pytest.mark.skipif(os.name == "nt", reason="POSIX parent-directory fsync")
def test_real_writer_parent_fsync_failure_is_loud_after_complete_commit(
        tmp_path, monkeypatch):
    inventory = _inventory_module()
    _install_runtime(monkeypatch, inventory)
    output = tmp_path / "runtime.cdx.json"
    output.write_bytes(b"previous-complete-bom")
    real_fsync = os.fsync

    def failing_parent_fsync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("injected parent fsync failure")
        return real_fsync(fd)

    monkeypatch.setattr(inventory.os, "fsync", failing_parent_fsync)

    with pytest.raises(OSError, match="injected parent fsync failure"):
        inventory.write_runtime_bom(output)

    assert json.loads(output.read_text(encoding="utf-8"))["bomFormat"] == "CycloneDX"
    _assert_no_temporary_bom(tmp_path)
