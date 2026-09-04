"""Approval dialog for a captured project-instruction bundle."""

from ..i18n import translate
from .compat import QtWidgets


class ProjectInstructionsDialog(QtWidgets.QDialog):
    """Show the exact instruction snapshot before recording a decision."""

    def __init__(self, bundle, parent=None):
        super().__init__(parent)
        self.decision = None
        self.setWindowTitle(translate(
            "ProjectInstructionsDialog", "Project instructions"))
        self.setMinimumSize(680, 520)

        layout = QtWidgets.QVBoxLayout(self)
        notice = QtWidgets.QLabel(translate(
            "ProjectInstructionsDialog",
            "Review the project instructions before sending them to the AI."))
        notice.setWordWrap(True)
        layout.addWidget(notice)

        details = QtWidgets.QTextEdit()
        details.setReadOnly(True)
        details.setMaximumHeight(150)
        details.setPlainText("\n".join((
            translate("ProjectInstructionsDialog", "Root: {}")
            .format(bundle.root),
            translate("ProjectInstructionsDialog", "Source: {}")
            .format(bundle.source_path),
            translate("ProjectInstructionsDialog", "Fingerprint: {}")
            .format(bundle.fingerprint),
            translate("ProjectInstructionsDialog", "Manifest:\n{}")
            .format("\n".join(bundle.manifest)),
        )))
        layout.addWidget(details)

        content = QtWidgets.QTextEdit()
        content.setReadOnly(True)
        content.setPlainText(bundle.content)
        layout.addWidget(content)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch()
        allow_button = QtWidgets.QPushButton(translate(
            "ProjectInstructionsDialog", "Trust and send"))
        ignore_button = QtWidgets.QPushButton(translate(
            "ProjectInstructionsDialog", "Ignore this version"))
        cancel_button = QtWidgets.QPushButton(translate(
            "ProjectInstructionsDialog", "Cancel"))
        allow_button.clicked.connect(self._allow)
        ignore_button.clicked.connect(self._ignore)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(allow_button)
        buttons.addWidget(ignore_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def _allow(self):
        self.decision = "allow"
        self.accept()

    def _ignore(self):
        self.decision = "ignore"
        self.accept()
