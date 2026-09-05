"""Report-view severity must reflect records, not Python's stderr stream."""

import importlib
import io
import logging
from pathlib import Path
import sys
import subprocess
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def addon_logger():
    logger = logging.getLogger("freecad_ai")
    previous = logger.handlers[:], logger.level, logger.propagate
    logger.handlers = []
    logger.setLevel(logging.NOTSET)
    logger.propagate = True
    yield logger
    logger.handlers, level, logger.propagate = previous
    logger.setLevel(level)


@pytest.fixture
def console():
    return SimpleNamespace(PrintMessage=Mock(), PrintWarning=Mock(), PrintError=Mock())


def _configure(console):
    module = importlib.import_module("freecad_ai.console_logging")
    module.configure_console_logging(console)


@pytest.mark.parametrize("level,method", [
    (logging.DEBUG, "PrintMessage"),
    (logging.INFO, "PrintMessage"),
    (logging.WARNING, "PrintWarning"),
    (logging.ERROR, "PrintError"),
    (logging.CRITICAL, "PrintError"),
])
def test_records_keep_their_real_severity(addon_logger, console, level, method):
    addon_logger.setLevel(logging.DEBUG)
    _configure(console)
    logging.getLogger("freecad_ai.mcp.server").log(level, "status %s", "ready")
    for name in ("PrintMessage", "PrintWarning", "PrintError"):
        callback = getattr(console, name)
        if name == method:
            callback.assert_called_once_with("freecad_ai.mcp.server: status ready\n")
        else:
            callback.assert_not_called()


def test_exception_retains_traceback_for_diagnosis(addon_logger, console):
    _configure(console)
    try:
        raise RuntimeError("listener failed")
    except RuntimeError:
        addon_logger.exception("MCP server stopped unexpectedly")
    message = console.PrintError.call_args.args[0]
    assert "Traceback (most recent call last)" in message
    assert "RuntimeError: listener failed" in message
    assert "MCP server stopped unexpectedly" in message
    console.PrintMessage.assert_not_called()


def test_repeated_setup_does_not_duplicate_or_use_root_stderr(addon_logger, console):
    root = logging.getLogger()
    root_handlers, root_level = root.handlers[:], root.level
    output = io.StringIO()
    sentinel = logging.StreamHandler(output)
    root.addHandler(sentinel)
    try:
        _configure(console)
        _configure(console)
        addon_logger.info("started")
        assert len(addon_logger.handlers) == 1
        console.PrintMessage.assert_called_once_with("freecad_ai: started\n")
        assert output.getvalue() == ""
        assert root.handlers == root_handlers + [sentinel]
        assert root.level == root_level
        logging.getLogger("other_addon").warning("unrelated warning")
        assert output.getvalue() == "unrelated warning\n"
    finally:
        root.removeHandler(sentinel)


def test_existing_addon_handler_and_explicit_level_are_preserved(addon_logger, console):
    output = io.StringIO()
    sentinel = logging.StreamHandler(output)
    addon_logger.addHandler(sentinel)
    addon_logger.setLevel(logging.WARNING)
    _configure(console)
    addon_logger.info("filtered")
    addon_logger.warning("still visible")
    assert sentinel in addon_logger.handlers
    assert addon_logger.level == logging.WARNING
    assert output.getvalue() == "still visible\n"
    console.PrintMessage.assert_not_called()
    console.PrintWarning.assert_called_once()


def test_worker_thread_logs_through_console_api(addon_logger, console):
    _configure(console)
    thread = threading.Thread(target=lambda: addon_logger.info("worker ready"))
    thread.start()
    thread.join(timeout=5)
    assert not thread.is_alive()
    console.PrintMessage.assert_called_once_with("freecad_ai: worker ready\n")


def test_formatting_failure_uses_logging_diagnostic(addon_logger, console, capsys):
    _configure(console)
    addon_logger.error("bad placeholder %d", "text")
    assert "Logging error" in capsys.readouterr().err
    console.PrintMessage.assert_not_called()


def test_import_is_inert_for_headless_stdio():
    script = '''
import logging, sys
sys.modules["FreeCAD"] = None
logger = logging.getLogger("freecad_ai")
before = (logger.handlers[:], logger.level, logger.propagate, sys.stdout)
import freecad_ai.console_logging
assert (logger.handlers, logger.level, logger.propagate, sys.stdout) == before
print("stdio untouched")
'''
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True,
        cwd=Path(__file__).resolve().parents[2], timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "stdio untouched\n"
    assert result.stderr == ""


@pytest.mark.parametrize("with_file", [False, True])
def test_launcher_configures_before_start(addon_logger, console, monkeypatch, with_file):
    from freecad_ai import config
    from freecad_ai.mcp import gui_server
    controller = SimpleNamespace(token_file_path="test-token-path")
    def start(*args, **kwargs):
        logging.getLogger("freecad_ai.mcp.gui_server").info("server ready")
        return "http://127.0.0.1:3000/mcp"
    controller.start = start
    monkeypatch.setitem(sys.modules, "FreeCAD", SimpleNamespace(
        Console=console, ActiveDocument=object()))
    monkeypatch.setattr(config, "get_config", lambda: SimpleNamespace())
    monkeypatch.setattr(gui_server, "get_server_controller", lambda: controller)
    path = Path(__file__).resolve().parents[2] / "mcp_server_http.py"
    namespace = {"__file__": str(path)} if with_file else {}
    exec(compile(path.read_text(), str(path), "exec"), namespace)
    console.PrintMessage.assert_called_once_with("freecad_ai.mcp.gui_server: server ready\n")


@pytest.mark.parametrize("route", ["initialize", "direct_command"])
def test_workbench_routes_configure_before_start(addon_logger, console, monkeypatch, route):
    from freecad_ai.mcp import gui_server
    gui = SimpleNamespace(Workbench=object, addCommand=Mock(), addWorkbench=Mock(),
                          addPreferencePage=Mock())
    app = SimpleNamespace(Console=console, getUserAppDataDir=lambda: "",
                          getResourceDir=lambda: "")
    monkeypatch.setitem(sys.modules, "FreeCAD", app)
    monkeypatch.setitem(sys.modules, "FreeCADGui", gui)
    path = Path(__file__).resolve().parents[2] / "InitGui.py"
    namespace = {}
    exec(compile(path.read_text(), str(path), "exec"), namespace)
    if route == "initialize":
        workbench = SimpleNamespace(appendToolbar=Mock(), appendMenu=Mock())
        namespace["FreeCADAIWorkbench"].Initialize(workbench)
        addon_logger.info("toolbar ready")
    else:
        def controller():
            addon_logger.info("toolbar ready")
            raise RuntimeError("stop before touching a real server")
        monkeypatch.setattr(gui_server, "get_server_controller", controller)
        with pytest.raises(RuntimeError, match="stop before"):
            namespace["ToggleMCPServerCommand"]().Activated()
    console.PrintMessage.assert_called_once_with("freecad_ai: toolbar ready\n")
