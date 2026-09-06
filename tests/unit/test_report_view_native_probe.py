"""The native report probe must refuse the user's existing GUI/profile."""

import hashlib
import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def probe():
    path = Path(__file__).resolve().parents[2] / "scripts/check_report_view_native.py"
    return runpy.run_path(str(path))


@pytest.fixture
def specification(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    private = tmp_path / "probe"
    private.mkdir(mode=0o700)
    files = ("InitGui.py", "mcp_server_http.py", "freecad_ai/console_logging.py",
             "freecad_ai/ui/chat_widget.py", "freecad_ai/llm/client.py")
    hashes = {}
    for name in files:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fixture\n")
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = private / "spec.json"
    manifest.write_text(json.dumps({
        "schema_version": 1, "source_root": str(source),
        "probe_root": str(private), "expected_sha256": hashes,
    }))
    manifest.chmod(0o600)
    return manifest


def test_source_drift_prevents_native_probe(probe, specification):
    data = json.loads(specification.read_text())
    (Path(data["source_root"]) / "InitGui.py").write_text("# changed\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        probe["_load_spec"](specification)


def test_manifest_cannot_target_files_outside_source(probe, specification):
    data = json.loads(specification.read_text())
    data["expected_sha256"]["../outside.py"] = "0" * 64
    specification.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="relative source path"):
        probe["_load_spec"](specification)


def test_nonprivate_manifest_is_rejected(probe, specification):
    specification.chmod(0o644)
    with pytest.raises(ValueError, match="owner-only"):
        probe["_load_spec"](specification)


def test_wrong_profile_never_changes_console_or_closes_gui(
        probe, specification, monkeypatch):
    app = SimpleNamespace(ConfigGet=lambda key: "/existing/user.cfg", Console=Mock())
    gui = SimpleNamespace(getMainWindow=Mock())
    monkeypatch.setitem(sys.modules, "FreeCAD", app)
    monkeypatch.setitem(sys.modules, "FreeCADGui", gui)
    with pytest.raises(RuntimeError, match="isolated UserParameter"):
        probe["run_probe"](specification)
    assert not app.Console.mock_calls
    gui.getMainWindow.assert_not_called()


def test_existing_documents_refuse_probe_before_gui_mutation(probe, specification):
    private = specification.parent
    values = {"UserParameter": private / "user.cfg",
              "SystemParameter": private / "system.cfg",
              "UserCachePath": private / "cache"}
    app = SimpleNamespace(
        ConfigGet=lambda key: str(values[key]),
        getUserAppDataDir=lambda: str(private / "data"),
        listDocuments=lambda: {"Unsaved": object()},
    )
    with pytest.raises(RuntimeError, match="existing documents"):
        probe["_check_isolation"](app, private)


def test_explicit_spec_runs_with_freecad_script_module_name(specification, monkeypatch):
    """FreeCAD names startup scripts after the file, not __main__."""
    monkeypatch.setenv("FREECAD_AI_REPORT_PROBE_SPEC", str(specification))
    monkeypatch.setitem(sys.modules, "FreeCAD", SimpleNamespace(
        ConfigGet=lambda key: "/existing/user.cfg"))
    path = Path(__file__).resolve().parents[2] / "scripts/check_report_view_native.py"
    with pytest.raises(RuntimeError, match="isolated UserParameter"):
        runpy.run_path(str(path), run_name="check_report_view_native")
