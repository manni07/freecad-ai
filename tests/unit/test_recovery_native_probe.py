"""The native recovery probe must refuse the user's live profile before edits."""

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def probe(monkeypatch):
    monkeypatch.delenv("FREECAD_AI_RECOVERY_PROBE_SPEC", raising=False)
    path = Path(__file__).resolve().parents[2] / "scripts/check_recovery_native.py"
    spec = importlib.util.spec_from_file_location("recovery_native_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def private_spec(tmp_path):
    tmp_path.chmod(0o700)
    data = {"schema_version": 1, "root": str(tmp_path), "case": "created",
            "expect": "fixed"}
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(data))
    path.chmod(0o600)
    return path, data


def test_private_spec_is_accepted(probe, private_spec):
    path, data = private_spec
    assert probe._load_spec(path) == data


@pytest.mark.parametrize("field,value", [
    ("schema_version", 2), ("case", "erase"), ("expect", "anything"),
    ("root", "/tmp"),
])
def test_invalid_spec_is_rejected_before_native_import(probe, private_spec, field, value):
    path, data = private_spec
    data[field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        probe._load_spec(path)


def test_public_spec_and_symlink_are_rejected(probe, private_spec):
    path, _ = private_spec
    path.chmod(0o644)
    with pytest.raises(ValueError, match="owner-only"):
        probe._load_spec(path)
    path.chmod(0o600)
    link = path.with_name("link.json")
    link.symlink_to(path)
    with pytest.raises(ValueError, match="non-symlink"):
        probe._load_spec(link)


@pytest.mark.parametrize("mismatch", [
    "UserParameter", "SystemParameter", "UserCachePath", "data", "documents",
])
def test_native_profile_mismatch_fails_before_mutation(probe, private_spec, monkeypatch, mismatch):
    path, data = private_spec
    root = Path(data["root"])
    config = {"UserParameter": str(root / "user.cfg"),
              "SystemParameter": str(root / "system.cfg"),
              "UserCachePath": str(root / "cache")}
    if mismatch in config:
        config[mismatch] = "/not-the-private-profile"
    app = SimpleNamespace(
        ConfigGet=config.__getitem__,
        getUserAppDataDir=lambda: "/user-data" if mismatch == "data" else str(root / "data"),
        listDocuments=lambda: {"Unsaved": object()} if mismatch == "documents" else {},
    )
    monkeypatch.setitem(sys.modules, "FreeCAD", app)
    monkeypatch.setitem(sys.modules, "FreeCADGui", None)
    before = set(root.iterdir())
    with pytest.raises(RuntimeError, match="refusing"):
        probe.run_native(path)
    assert set(root.iterdir()) == before


def test_empty_isolated_profile_passes_guard(probe, private_spec):
    _, data = private_spec
    root = Path(data["root"])
    config = {"UserParameter": str(root / "user.cfg"),
              "SystemParameter": str(root / "system.cfg"),
              "UserCachePath": str(root / "cache")}
    app = SimpleNamespace(ConfigGet=config.__getitem__,
                          getUserAppDataDir=lambda: str(root / "data"),
                          listDocuments=lambda: {})
    probe._check_isolation(app, root)
