"""Fresh Qt processes catch missing-font warnings before alias caching hides them."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("target", ["chat", "probe"])
def test_native_fonts_use_application_family_without_warnings(tmp_path, target):
    script = r'''
import sys
# Qt rendering needs no FreeCAD document or real parameter store.
sys.modules["FreeCAD"] = None
from freecad_ai.ui.compat import QtCore, QtGui, QtWidgets
app = QtWidgets.QApplication([])
# Offscreen Qt may itself default to an unavailable "Sans Serif" alias.
# Model the installed font selected by a native application/user preference.
font = QtGui.QFont(QtGui.QFontDatabase.families()[0])
app.setFont(font)
messages = []
QtCore.qInstallMessageHandler(lambda kind, context, message: messages.append(message))
if sys.argv[1] == "chat":
    from freecad_ai.ui.chat_widget import ChatDockWidget
    dock = ChatDockWidget()
    for widget in (dock.chat_display, dock.input_edit):
        assert widget.font().family() == app.font().family(), widget.font().family()
        assert widget.font().pointSize() == 10
        QtGui.QFontMetrics(widget.font()).horizontalAdvance("FreeCAD AI")
    dock._mark_shutdown()
else:
    from freecad_ai.llm.client import _generate_probe_image
    number, data = _generate_probe_image()
    image = QtGui.QImage.fromData(data)
    assert 100 <= number <= 999
    assert (image.width(), image.height()) == (128, 64)
    assert any(image.pixelColor(x, y).value() < 128
               for x in range(image.width()) for y in range(image.height()))
assert not [m for m in messages if "missing font family" in m], messages
print("native font PASS", sys.argv[1], app.font().family())
'''
    result = subprocess.run(
        [sys.executable, "-c", script, target],
        cwd=Path(__file__).resolve().parents[2],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen",
             "FREECAD_AI_CONFIG_DIR": str(tmp_path / "config")},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "native font PASS" in result.stdout
