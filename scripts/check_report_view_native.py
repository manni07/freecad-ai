"""Run inside a newly launched, isolated FreeCAD GUI to check report severity.

Set FREECAD_AI_REPORT_PROBE_SPEC to an owner-only JSON file inside a new
owner-only probe directory. Its schema_version is 1; source_root names the
candidate checkout, probe_root names that directory, and expected_sha256 maps
relative source paths to reviewed hashes. Launch FreeCAD with --user-cfg and
--system-cfg pointing to probe_root/user.cfg and system.cfg, and private data
and cache paths probe_root/data and probe_root/cache. No server is started.

The script refuses existing documents or mismatched profiles before changing
native state. Only an isolated GUI is closed after the check. Read result.json
and require status PASS plus normal process exit; exit alone is insufficient.
"""

import hashlib
import importlib
import json
import logging
import os
from pathlib import Path
import stat
import sys
import threading
import traceback


_RUNTIME_FILES = {
    "InitGui.py", "mcp_server_http.py", "freecad_ai/console_logging.py",
    "freecad_ai/ui/chat_widget.py", "freecad_ai/llm/client.py",
}


def _load_spec(path):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("specification must be an absolute non-symlink file")
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
            or (hasattr(os, "getuid") and info.st_uid != os.getuid())):
        raise ValueError("specification must be owner-only")
    spec = json.loads(path.read_text(encoding="utf-8"))
    source = Path(spec["source_root"])
    private = Path(spec["probe_root"])
    if (spec.get("schema_version") != 1 or not source.is_absolute()
            or not source.is_dir() or not private.is_absolute()
            or private.resolve() != private or path.parent != private):
        raise ValueError("invalid source/probe directory or schema")
    info = private.stat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077
            or (hasattr(os, "getuid") and info.st_uid != os.getuid())):
        raise ValueError("probe directory must be owner-only")
    hashes = spec["expected_sha256"]
    if not isinstance(hashes, dict) or not _RUNTIME_FILES <= hashes.keys():
        raise ValueError("all five reviewed runtime hashes are required")
    for relative, expected in hashes.items():
        name = Path(relative)
        if name.is_absolute() or ".." in name.parts:
            raise ValueError("expected a relative source path")
        target = source / name
        if not target.resolve().is_relative_to(source.resolve()):
            raise ValueError("expected a relative source path inside source root")
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("source hash mismatch: " + relative)
    return spec


def _check_isolation(app, private):
    expected = {"UserParameter": private / "user.cfg",
                "SystemParameter": private / "system.cfg",
                "UserCachePath": private / "cache"}
    for key, path in expected.items():
        if Path(app.ConfigGet(key)).resolve() != path:
            raise RuntimeError("expected isolated " + key)
    if Path(app.getUserAppDataDir()).resolve() != private / "data":
        raise RuntimeError("expected isolated user data")
    if app.listDocuments():
        raise RuntimeError("refusing existing documents")


def run_probe(spec_path=None):
    spec = _load_spec(spec_path or os.environ["FREECAD_AI_REPORT_PROBE_SPEC"])
    private = Path(spec["probe_root"])
    source = Path(spec["source_root"]).resolve()
    import FreeCAD as App
    # Fail before Console mutations, GUI access, timers or any close request.
    _check_isolation(App, private)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source))
    os.environ["FREECAD_AI_CONFIG_DIR"] = str(private / "ai-config")
    import FreeCADGui as Gui
    from freecad_ai.ui.compat import QtCore, QtGui, QtWidgets

    result = {"status": "STARTING", "schema_version": 1, "pid": os.getpid(),
              "source_root": str(source), "probe_root": str(private)}

    def finish():
        (private / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        # The profile/document isolation gate above is mandatory for this close.
        QtCore.QTimer.singleShot(100, Gui.getMainWindow().close)

    def inspect():
        try:
            rows = []
            for widget in Gui.getMainWindow().findChildren(QtWidgets.QTextEdit):
                if "ReportOutput" not in widget.metaObject().className():
                    continue
                block = widget.document().begin()
                while block.isValid():
                    if "REPORT_PROBE_" in block.text() or "Traceback" in block.text():
                        rows.append({"text": block.text(), "colors": [
                            item.format.foreground().color().name()
                            for item in block.layout().formats()]})
                    block = block.next()
            result["rows"] = rows
            keys = ("CONTROL_INFO", "CONTROL_WARNING", "CONTROL_ERROR", "BEFORE_INFO",
                    "AFTER_INFO", "AFTER_WARNING", "AFTER_ERROR", "THREAD_INFO",
                    "EXCEPTION")
            indexed = {key: [row for row in rows if "REPORT_PROBE_" + key in row["text"]]
                       for key in keys}
            for key, matches in indexed.items():
                assert len(matches) == 1, (key, matches)
            colors = {key: matches[0]["colors"] for key, matches in indexed.items()}
            for key, control in (("BEFORE_INFO", "CONTROL_ERROR"),
                                 ("AFTER_INFO", "CONTROL_INFO"),
                                 ("THREAD_INFO", "CONTROL_INFO"),
                                 ("AFTER_WARNING", "CONTROL_WARNING"),
                                 ("AFTER_ERROR", "CONTROL_ERROR"),
                                 ("EXCEPTION", "CONTROL_ERROR")):
                assert colors[key] == colors[control], colors
            assert colors["AFTER_INFO"] != colors["AFTER_ERROR"], colors
            assert any("Traceback (most recent call last)" in row["text"] for row in rows)
            assert any("RuntimeError: REPORT_PROBE_TRACEBACK_DETAIL" in row["text"]
                       for row in rows)
            assert not App.listDocuments(), "probe created a document"
            result["status"] = "PASS"
        except Exception:
            result.update(status="FAIL", error=traceback.format_exc())
        finish()

    def begin():
        try:
            _check_isolation(App, private)
            modules = {}
            for relative, expected in spec["expected_sha256"].items():
                if not relative.startswith("freecad_ai/") or not relative.endswith(".py"):
                    continue
                module = importlib.import_module(relative[:-3].replace("/", "."))
                actual = Path(module.__file__).resolve()
                assert actual == source / relative, (relative, str(actual))
                assert hashlib.sha256(actual.read_bytes()).hexdigest() == expected, relative
                modules[relative] = {"path": str(actual), "sha256": expected}
            result["modules"] = modules
            from freecad_ai.mcp import gui_server
            assert gui_server._controller is None, "existing MCP controller"
            from freecad_ai.config import get_config
            assert not get_config().mcp_servers, "configured external MCP servers"
            prefs = App.ParamGet("User parameter:BaseApp/Preferences/OutputWindow")
            for key in ("RedirectPythonOutput", "RedirectPythonErrors", "checkMessage",
                        "checkWarning", "checkError"):
                prefs.SetBool(key, True)
            for key, color in (("colorText", 0x102030ff), ("colorWarning", 0x987600ff),
                               ("colorError", 0xff0000ff)):
                prefs.SetUnsigned(key, color)
            App.Console.PrintMessage("REPORT_PROBE_CONTROL_INFO\n")
            App.Console.PrintWarning("REPORT_PROBE_CONTROL_WARNING\n")
            App.Console.PrintError("REPORT_PROBE_CONTROL_ERROR\n")
            parent = logging.getLogger("freecad_ai")
            parent.handlers = []
            parent.setLevel(logging.INFO)
            parent.propagate = False
            log = logging.getLogger("freecad_ai.native_probe")
            old = logging.StreamHandler(sys.stderr)
            parent.addHandler(old)
            log.info("REPORT_PROBE_BEFORE_INFO")
            parent.removeHandler(old)
            from freecad_ai.console_logging import configure_console_logging
            configure_console_logging(App.Console)
            configure_console_logging(App.Console)
            log.info("REPORT_PROBE_AFTER_INFO")
            log.warning("REPORT_PROBE_AFTER_WARNING")
            log.error("REPORT_PROBE_AFTER_ERROR")
            try:
                raise RuntimeError("REPORT_PROBE_TRACEBACK_DETAIL")
            except RuntimeError:
                log.exception("REPORT_PROBE_EXCEPTION")
            thread = threading.Thread(target=lambda: log.info("REPORT_PROBE_THREAD_INFO"))
            thread.start()
            thread.join(3)
            assert not thread.is_alive()
            app_font = QtWidgets.QApplication.font()
            result["native_app_font"] = app_font.family()
            result["resolved_app_font"] = QtGui.QFontInfo(app_font).family()
            messages = []
            old_handler = QtCore.qInstallMessageHandler(
                lambda kind, context, message: messages.append(message))
            dock = None
            try:
                from freecad_ai.ui.chat_widget import ChatDockWidget
                dock = ChatDockWidget(Gui.getMainWindow())
                result["chat_fonts"] = {}
                for name, widget in (("message", dock.chat_display), ("input", dock.input_edit)):
                    font = widget.font()
                    result["chat_fonts"][name] = {"family": font.family(), "size": font.pointSize()}
                    assert font.family() == app_font.family() and font.pointSize() == 10
                from freecad_ai.llm.client import _generate_probe_image
                number, data = _generate_probe_image()
                image = QtGui.QImage.fromData(data)
                assert 100 <= number <= 999 and (image.width(), image.height()) == (128, 64)
                assert any(image.pixelColor(x, y).value() < 128
                           for x in range(128) for y in range(64))
                result["probe_image_bytes"] = len(data)
                result["addon_qt_messages"] = messages
                assert not [msg for msg in messages if "missing font family" in msg], messages
            finally:
                QtCore.qInstallMessageHandler(old_handler)
                if dock is not None:
                    dock._mark_shutdown()
                    dock.close()
            QtCore.QTimer.singleShot(1500, inspect)
        except Exception:
            result.update(status="FAIL", error=traceback.format_exc())
            finish()

    QtCore.QTimer.singleShot(1000, begin)


if __name__ == "__main__" or os.environ.get("FREECAD_AI_REPORT_PROBE_SPEC"):
    run_probe()
