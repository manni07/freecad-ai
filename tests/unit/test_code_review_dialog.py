"""Security behavior of the raw-code review dialog."""

from types import SimpleNamespace
from unittest.mock import patch

from freecad_ai.core import executor
from freecad_ai.ui.code_review_dialog import CodeReviewDialog
from freecad_ai.ui.compat import QtWidgets


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _preflight(status_name, message):
    enum = getattr(executor, "PreflightStatus", None)
    status = getattr(enum, status_name.upper()) if enum is not None else status_name
    return SimpleNamespace(
        status=status,
        message=message,
        code="print('reviewed')",
        success=False,
        stdout="",
        stderr=message,
    )


def test_rejected_preflight_cannot_be_executed_or_overridden():
    """A security rejection must disable the live-execution edge."""
    _app()
    dialog = CodeReviewDialog("print('reviewed')")
    with patch(
        "freecad_ai.ui.code_review_dialog.validate_code",
        return_value=_preflight("rejected", "unsafe code"),
    ):
        dialog._check()

    assert dialog.execute_btn.isEnabled() is False
    assert "without preflight" not in dialog.execute_btn.text().lower()


def test_unavailable_preflight_requires_an_explicit_unvalidated_action():
    """Infrastructure failure must be visible before any override is offered."""
    _app()
    dialog = CodeReviewDialog("print('reviewed')")
    with patch(
        "freecad_ai.ui.code_review_dialog.validate_code",
        return_value=_preflight("unavailable", "FreeCADCmd unavailable"),
    ):
        dialog._check()

    assert dialog.execute_btn.isEnabled() is True
    assert "without preflight" in dialog.execute_btn.text().lower()


def test_successful_preflight_keeps_normal_execute_action():
    _app()
    dialog = CodeReviewDialog("print('reviewed')")
    result = SimpleNamespace(
        status=executor.PreflightStatus.PASSED,
        message="ok",
        code="print('reviewed')",
        success=True,
        stdout="validated",
        stderr="",
    )
    with patch(
        "freecad_ai.ui.code_review_dialog.validate_code", return_value=result,
    ):
        dialog._check()

    assert dialog.execute_btn.isEnabled() is True
    assert dialog.execute_btn.text().lower() == "execute"


def test_editing_invalidates_only_the_prior_preflight_decision():
    _app()
    dialog = CodeReviewDialog("print('reviewed')")
    dialog._preflight_status = executor.PreflightStatus.PASSED
    dialog.execute_btn.setEnabled(False)
    dialog.execute_btn.setText("stale")

    dialog._invalidate_preflight()

    assert dialog._preflight_status is None
    assert dialog.execute_btn.isEnabled() is True
    assert dialog.execute_btn.text().lower() == "execute"


def test_unavailable_override_defaults_to_no_and_yes_is_the_only_live_path():
    """The second warning must deny by default and forward one explicit override."""
    _app()
    dialog = CodeReviewDialog("print('reviewed')")
    dialog._preflight_status = executor.PreflightStatus.UNAVAILABLE

    class _Box:
        Warning = QtWidgets.QMessageBox.Warning
        Yes = QtWidgets.QMessageBox.Yes
        No = QtWidgets.QMessageBox.No
        answer = QtWidgets.QMessageBox.No
        default = None
        def __init__(self, *args): pass
        def setIcon(self, *args): pass
        def setWindowTitle(self, *args): pass
        def setText(self, *args): pass
        def setInformativeText(self, *args): pass
        def setStandardButtons(self, *args): pass
        def setDefaultButton(self, value): type(self).default = value
        def exec(self): return type(self).answer

    with patch("freecad_ai.ui.code_review_dialog.QtWidgets.QMessageBox", _Box), patch(
        "freecad_ai.ui.code_review_dialog.execute_code",
        return_value=executor.ExecutionResult(True, "", "", "print('reviewed')"),
    ) as execute:
        dialog._execute()
        assert _Box.default == _Box.No
        execute.assert_not_called()
        _Box.answer = _Box.Yes
        dialog._execute()
        execute.assert_called_once_with("print('reviewed')", allow_unvalidated=True)
