"""Exercise the real recovery dialog in a disposable native FreeCAD process.

Run with system Python, --app, --workspace, --case and --expect fixed|legacy.
The workspace must already exist. Outputs are retained in a new private directory.
No existing profile, recovery cache or input model is changed. The optional model
is copied before launch. This is a GUI regression probe, not a recovery utility.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
import xml.etree.ElementTree as ET
import zipfile


CASES = ("created", "corrupted", "revalidated", "missing", "invalid_zip",
         "invalid_xml", "accept")
SPEC_ENV = "FREECAD_AI_RECOVERY_PROBE_SPEC"


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_spec(path):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("specification must be an absolute non-symlink file")
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
            or info.st_uid != os.getuid()):
        raise ValueError("specification must be owner-only")
    spec = json.loads(path.read_text())
    root = Path(spec["root"])
    if (spec.get("schema_version") != 1 or spec.get("case") not in CASES
            or spec.get("expect") not in ("fixed", "legacy")
            or root.resolve() != root or path.parent != root
            or root.stat().st_mode & 0o077 or root.stat().st_uid != os.getuid()):
        raise ValueError("invalid private root or probe specification")
    return spec


def _check_isolation(app, root):
    expected = {"UserParameter": root / "user.cfg",
                "SystemParameter": root / "system.cfg",
                "UserCachePath": root / "cache"}
    for key, value in expected.items():
        if Path(app.ConfigGet(key)).resolve() != value:
            raise RuntimeError("refusing non-isolated " + key)
    if Path(app.getUserAppDataDir()).resolve() != root / "data":
        raise RuntimeError("refusing non-isolated user data")
    if app.listDocuments():
        raise RuntimeError("refusing existing documents")


def run_native(spec_path):
    """CLI macros execute before MainWindow's native recovery scan."""
    spec = _load_spec(spec_path)
    root = Path(spec["root"])
    import FreeCAD as App
    # Fail before GUI access, preferences, fixture creation or close requests.
    _check_isolation(App, root)
    sys.dont_write_bytecode = True
    import FreeCADGui as Gui
    import Part
    try:
        from PySide6 import QtCore, QtWidgets
    except ImportError:
        from PySide2 import QtCore, QtWidgets

    result = {"status": "STARTING", "case": spec["case"], "version": App.Version(),
              "pid": os.getpid(), "root": str(root), "cwd": os.getcwd(),
              "user_cache": App.ConfigGet("UserCachePath"), "rows": []}
    owned_names = []

    def write():
        (root / "result.json").write_text(json.dumps(result, indent=2))

    def finish():
        for name in owned_names:
            if name in App.listDocuments():
                App.closeDocument(name)
        write()
        QtCore.QTimer.singleShot(100, Gui.getMainWindow().close)

    try:
        preferences = App.ParamGet("User parameter:BaseApp/Preferences/OutputWindow")
        for key in ("RedirectPythonOutput", "RedirectPythonErrors", "checkMessage",
                    "checkWarning", "checkError"):
            preferences.SetBool(key, True)
        original = root / "model" / "original.FCStd"
        if spec.get("input_sha256"):
            assert _digest(original) == spec["input_sha256"], "input copy hash drift"
        else:
            doc = App.newDocument("RecoveryFixture")
            owned_names.append(doc.Name)
            obj = doc.addObject("Part::Feature", "Box")
            obj.Shape = Part.makeBox(10, 20, 30)
            doc.recompute()
            Gui.activeDocument().activeView().viewAxonometric()
            Gui.activeDocument().activeView().fitAll()
            doc.saveAs(str(original))
            App.closeDocument(doc.Name)
        result["fixture_sha256"] = _digest(original)
        fake_id = "98765001"
        cache = root / "cache"
        transient = cache / ("FreeCAD_Doc_" + uuid.uuid4().hex + "_" + fake_id)
        transient.mkdir(mode=0o700)
        (cache / ("FreeCAD_" + fake_id + ".lock")).write_bytes(b"")
        recovery = transient / "fc_recovery_file.fcstd"
        shutil.copy2(original, recovery)
        os.utime(original, (time.time() - 60, time.time() - 60))
        os.utime(recovery, None)
        case = spec["case"]
        if case == "missing":
            original = root / "model" / "missing.FCStd"
        elif case == "invalid_zip":
            original.write_bytes(b"intentionally invalid ZIP fixture")
        elif case == "invalid_xml":
            with zipfile.ZipFile(original, "w") as archive:
                archive.writestr("Document.xml", b"<Document><broken>")
        metadata = transient / "fc_recovery_file.xml"
        xml = ET.Element("AutoRecovery", SchemaVersion="1")
        ET.SubElement(xml, "Status").text = (
            "Corrupted" if case in ("corrupted", "revalidated") else "Created")
        ET.SubElement(xml, "Label").text = "RECOVERY_PROBE_" + case
        ET.SubElement(xml, "FileName").text = str(original)
        ET.ElementTree(xml).write(metadata, encoding="utf-8", xml_declaration=True)
        if case == "revalidated":
            # The fixture alone models an explicit audited metadata reset.
            shutil.copy2(metadata, root / "metadata-before-revalidation.xml")
            xml.find("Status").text = "Created"
            ET.ElementTree(xml).write(metadata, encoding="utf-8", xml_declaration=True)
        result.update(original=str(original), metadata=str(metadata),
                      basename_in_cwd=Path(original.name).exists(),
                      original_before=_digest(original) if original.exists() else None,
                      metadata_before=metadata.read_text())
        assert not result["basename_in_cwd"], "fixture must exercise a different CWD"
        assert not App.listDocuments(), "fixture builder left a document open"
        write()
    except Exception:
        result.update(status="FAIL", error=traceback.format_exc())
        finish()
        return

    deadline = time.monotonic() + 25

    def inspect():
        dialog = next((widget for widget in QtWidgets.QApplication.topLevelWidgets()
                       if "DocumentRecovery" in widget.metaObject().className()
                       and widget.isVisible()), None)
        if dialog is None and time.monotonic() < deadline:
            QtCore.QTimer.singleShot(100, inspect)
            return
        try:
            assert dialog is not None, "native recovery dialog did not appear"
            tree = dialog.findChild(QtWidgets.QTreeWidget)
            assert tree is not None and tree.topLevelItemCount() == 1
            item = tree.topLevelItem(0)
            result["dialog_before"] = [item.text(i) for i in range(tree.columnCount())]
            result["dialog_status_color"] = item.foreground(1).color().name()
            state = ET.parse(metadata).getroot().findtext("Status")
            expected = ("Corrupted" if spec["expect"] == "legacy"
                        or case in ("corrupted", "missing", "invalid_zip", "invalid_xml")
                        else "Created")
            assert state == expected, (state, expected)
            result["native_metadata_status"] = state
            if case == "accept":
                # Native dialog acceptance restores only our copied recovery payload.
                dialog.accept()
                docs = list(App.listDocuments().values())
                owned_names.extend(doc.Name for doc in docs)
                assert len(docs) == 1, "recovery did not produce exactly one document"
                doc = docs[0]
                result["recovered"] = {
                    "objects": len(doc.Objects),
                    "links": sum(obj.TypeId == "App::Link" for obj in doc.Objects),
                    "states": {obj.Name: obj.State for obj in doc.Objects},
                    "gui_document": Gui.getDocument(doc.Name) is not None,
                    "camera": Gui.getDocument(doc.Name).activeView().getCamera(),
                }
                expected_count = spec.get("expected_objects", 1)
                assert len(doc.Objects) == expected_count
                assert result["recovered"]["gui_document"]
                assert all("Invalid" not in obj.State for obj in doc.Objects)
                result["dialog_after"] = [item.text(i) for i in range(tree.columnCount())]
            result["report_widget_count"] = 0
            for widget in Gui.getMainWindow().findChildren(QtWidgets.QTextEdit):
                if "ReportOutput" in widget.metaObject().className():
                    result["report_widget_count"] += 1
                    result["rows"].extend(widget.toPlainText().splitlines())
                    block = widget.document().begin()
                    result.setdefault("report_colors", [])
                    while block.isValid():
                        result["report_colors"].append({"text": block.text(), "colors": [
                            item.format.foreground().color().name()
                            for item in block.layout().formats()]})
                        block = block.next()
            assert result["report_widget_count"] > 0, "native ReportOutput widget not found"
            result["read_error_reported"] = any(
                "Error reading from file" in row for row in result["rows"])
            result["corruption_warning_reported"] = any(
                "Original project file is corrupted" in row for row in result["rows"])
            if expected == "Created":
                assert not result["corruption_warning_reported"], result["rows"]
                assert not result["read_error_reported"], result["rows"]
            if result["original_before"] is not None:
                assert _digest(original) == result["original_before"], "original fixture changed"
            result["status"] = "PASS"
        except Exception:
            result.update(status="FAIL", error=traceback.format_exc())
        finally:
            if dialog is not None:
                dialog.reject()
            finish()

    QtCore.QTimer.singleShot(1000, inspect)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--expect", choices=("fixed", "legacy"), required=True)
    parser.add_argument("--source-model", type=Path)
    parser.add_argument("--expected-objects", type=int, default=1)
    args = parser.parse_args()
    app = args.app.resolve(strict=True)
    workspace = args.workspace.resolve(strict=True)
    # The embedded interpreter may write bytecode before this macro executes.
    for directory, _names, files in os.walk(app):
        for target in [Path(directory)] + [Path(directory) / name for name in files]:
            if not target.is_symlink() and target.stat().st_mode & 0o222:
                raise RuntimeError("app bundle must be read-only before launch")
    root = Path(tempfile.mkdtemp(prefix="recovery-" + args.case + "-", dir=workspace))
    for name in ("data", "cache", "home", "tmp", "model", "cwd"):
        (root / name).mkdir(mode=0o700)
    for name in ("user.cfg", "system.cfg"):
        (root / name).write_text('<?xml version="1.0"?><FCParameters><FCParamGroup Name="Root"/></FCParameters>')
    spec = {"schema_version": 1, "root": str(root), "case": args.case,
            "expect": args.expect, "expected_objects": args.expected_objects}
    if args.source_model:
        source = args.source_model.resolve(strict=True)
        spec["input_sha256"] = _digest(source)
        shutil.copy2(source, root / "model" / "original.FCStd")
    spec_path = root / "spec.json"
    spec_path.write_text(json.dumps(spec, indent=2))
    spec_path.chmod(0o600)
    env = {"PATH": "/usr/bin:/bin", "HOME": str(root / "home"), "LANG": "en_US.UTF-8",
           "TMPDIR": str(root / "tmp"), "FREECAD_USER_HOME": str(root / "home"),
           "FREECAD_USER_DATA": str(root / "data"), "FREECAD_USER_TEMP": str(root / "cache"),
           "PYTHONDONTWRITEBYTECODE": "1", SPEC_ENV: str(spec_path)}
    command = [str(app / "Contents/MacOS/FreeCAD"), "--user-cfg", str(root / "user.cfg"),
               "--system-cfg", str(root / "system.cfg"), str(Path(__file__).resolve())]
    print(str(root), flush=True)
    with (root / "process.log").open("w") as output:
        process = subprocess.Popen(command, cwd=root / "cwd", env=env,
                                   stdout=output, stderr=subprocess.STDOUT)
        (root / "launch.json").write_text(json.dumps({"pid": process.pid, "command": command}, indent=2))
        try:
            exit_code = process.wait(timeout=90)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise RuntimeError("owned diagnostic timed out; evidence retained at " + str(root))
    (root / "exit.json").write_text(json.dumps({"exit_code": exit_code}))
    if args.source_model:
        assert _digest(source) == spec["input_sha256"], "input model changed"
    result = json.loads((root / "result.json").read_text())
    print(json.dumps(result, indent=2))
    if exit_code != 0 or result.get("status") != "PASS":
        raise SystemExit(1)


if os.environ.get(SPEC_ENV):
    run_native(os.environ[SPEC_ENV])
elif __name__ == "__main__":
    main()
