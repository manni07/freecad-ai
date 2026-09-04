"""Approval and immutable-request tests for project instruction bundles."""

import importlib
import inspect
import os
from dataclasses import fields
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from freecad_ai.config import AppConfig
from freecad_ai.core.system_prompt import build_system_prompt
from freecad_ai.extensions.agents_md import InstructionBundle, InstructionLoadError
from freecad_ai.ui.chat_widget import ChatDockWidget
from freecad_ai.ui.project_instructions_dialog import ProjectInstructionsDialog


def _agents_module():
    return importlib.import_module("freecad_ai.extensions.agents_md")


def _discover_config_bundle(config_dir):
    module = _agents_module()
    discover = getattr(module, "discover_instruction_bundle", None)
    if discover is None:
        pytest.fail("missing InstructionBundle discovery for config AGENTS.md")
    with patch.object(module, "CONFIG_DIR", str(config_dir)), patch.object(
        module, "_get_document_directory", return_value=""
    ):
        return discover()


def _bundle(tmp_path, content="approved project bytes", fingerprint=None):
    root = os.path.realpath(tmp_path)
    return InstructionBundle(
        root=root,
        source_path=os.path.join(root, "AGENTS.md"),
        content=content,
        fingerprint=fingerprint or "sha256:" + "a" * 64,
        manifest=("AGENTS.md",),
    )


def _trust_record(bundle, decision="allow"):
    return {
        bundle.root: {
            "source": bundle.source_path,
            "fingerprint": bundle.fingerprint,
            "decision": decision,
            "timestamp": "2026-09-04T12:00:00+02:00",
        }
    }


def _patch_prepare_dependencies(monkeypatch, bundle, cfg, decision, dialog_calls):
    agents = _agents_module()
    chat = importlib.import_module("freecad_ai.ui.chat_widget")
    dialog_module = importlib.import_module(
        "freecad_ai.ui.project_instructions_dialog")

    class FakeDialog:
        def __init__(self, shown_bundle, parent):
            assert shown_bundle is bundle
            dialog_calls.append(shown_bundle.fingerprint)
            self.decision = decision

        def exec(self):
            return 0

    monkeypatch.setattr(agents, "discover_instruction_bundle", lambda: bundle)
    monkeypatch.setattr(chat, "get_config", lambda: cfg)
    monkeypatch.setattr(dialog_module, "ProjectInstructionsDialog", FakeDialog)


def test_config_schema_has_fingerprint_scoped_instruction_trust():
    field = next(
        (item for item in fields(AppConfig) if item.name == "project_instruction_trust"),
        None,
    )
    assert field is not None
    assert field.default_factory() == {}


@pytest.mark.parametrize(("decision", "expected"), [("allow", True), ("ignore", False)])
def test_config_agents_content_requires_exact_allow_decision(tmp_path, decision, expected):
    config_dir = tmp_path / "config"; config_dir.mkdir()
    (config_dir / "AGENTS.md").write_text("config-only instruction")
    bundle = _discover_config_bundle(config_dir)
    record = {
        os.path.realpath(bundle.root): {
            "source": os.path.realpath(bundle.source_path),
            "fingerprint": bundle.fingerprint,
            "decision": decision,
            "timestamp": "2026-09-04T12:00:00+02:00",
        }
    }
    module = _agents_module()
    cfg = SimpleNamespace(project_instruction_trust=record)
    with patch.object(module, "CONFIG_DIR", str(config_dir)), patch.object(
        module, "_get_document_directory", return_value=""
    ), patch.object(module, "get_config", return_value=cfg, create=True):
        content = module.load_agents_md()
    assert ("config-only instruction" in content) is expected


def test_config_allow_is_scoped_to_exact_fingerprint(tmp_path):
    config_dir = tmp_path / "config"; config_dir.mkdir()
    source = config_dir / "AGENTS.md"; source.write_text("approved version")
    approved = _discover_config_bundle(config_dir)
    source.write_text("unapproved changed version")
    record = {
        os.path.realpath(approved.root): {
            "source": os.path.realpath(approved.source_path),
            "fingerprint": approved.fingerprint,
            "decision": "allow",
            "timestamp": "2026-09-04T12:00:00+02:00",
        }
    }
    module = _agents_module()
    cfg = SimpleNamespace(project_instruction_trust=record)
    with patch.object(module, "CONFIG_DIR", str(config_dir)), patch.object(
        module, "_get_document_directory", return_value=""
    ), patch.object(module, "get_config", return_value=cfg, create=True):
        assert "unapproved changed version" not in module.load_agents_md()


@pytest.mark.parametrize(
    ("decision", "expected_snapshot"),
    [("allow", "approved project bytes"), ("ignore", "")],
)
def test_first_use_previews_and_persists_exact_decision(
        tmp_path, monkeypatch, decision, expected_snapshot):
    bundle = _bundle(tmp_path)
    cfg = SimpleNamespace(project_instruction_trust={})
    dialog_calls = []
    saves = []
    _patch_prepare_dependencies(
        monkeypatch, bundle, cfg, decision, dialog_calls)
    monkeypatch.setattr(
        "freecad_ai.ui.chat_widget.save_current_config", lambda: saves.append(True))
    dock = SimpleNamespace(_current_instruction_snapshot="stale")

    result = ChatDockWidget._prepare_project_instructions(dock, "hello")

    assert result == ("hello", bundle)
    assert dialog_calls == [bundle.fingerprint]
    assert dock._current_instruction_snapshot == expected_snapshot
    assert cfg.project_instruction_trust[bundle.root]["decision"] == decision
    assert cfg.project_instruction_trust[bundle.root]["fingerprint"] == bundle.fingerprint
    assert saves == [True]


def test_unchanged_allow_uses_snapshot_without_dialog(tmp_path, monkeypatch):
    bundle = _bundle(tmp_path)
    cfg = SimpleNamespace(project_instruction_trust=_trust_record(bundle))
    dialog_calls = []
    _patch_prepare_dependencies(
        monkeypatch, bundle, cfg, decision=None, dialog_calls=dialog_calls)
    dock = SimpleNamespace(_current_instruction_snapshot="")

    result = ChatDockWidget._prepare_project_instructions(dock, "hello")

    assert result == ("hello", bundle)
    assert dialog_calls == []
    assert dock._current_instruction_snapshot == bundle.content


def test_no_instruction_bundle_clears_stale_snapshot(monkeypatch):
    agents = _agents_module()
    monkeypatch.setattr(agents, "discover_instruction_bundle", lambda: None)
    dock = SimpleNamespace(_current_instruction_snapshot="stale")

    result = ChatDockWidget._prepare_project_instructions(dock, "hello")

    assert result == ("hello", None)
    assert dock._current_instruction_snapshot == ""


def test_non_mapping_trust_is_replaced_only_after_explicit_decision(
        tmp_path, monkeypatch):
    bundle = _bundle(tmp_path)
    cfg = SimpleNamespace(project_instruction_trust=[])
    dialog_calls = []
    saves = []
    _patch_prepare_dependencies(
        monkeypatch, bundle, cfg, decision="allow", dialog_calls=dialog_calls)
    monkeypatch.setattr(
        "freecad_ai.ui.chat_widget.save_current_config", lambda: saves.append(True))
    dock = SimpleNamespace(_current_instruction_snapshot="")

    result = ChatDockWidget._prepare_project_instructions(dock, "hello")

    assert result == ("hello", bundle)
    assert isinstance(cfg.project_instruction_trust, dict)
    assert cfg.project_instruction_trust[bundle.root]["decision"] == "allow"
    assert saves == [True]


def test_changed_fingerprint_previews_and_replaces_old_decision(tmp_path, monkeypatch):
    old = _bundle(tmp_path, fingerprint="sha256:" + "a" * 64)
    changed = _bundle(
        tmp_path, content="changed bytes", fingerprint="sha256:" + "b" * 64)
    cfg = SimpleNamespace(project_instruction_trust=_trust_record(old))
    dialog_calls = []
    _patch_prepare_dependencies(
        monkeypatch, changed, cfg, decision="allow", dialog_calls=dialog_calls)
    monkeypatch.setattr(
        "freecad_ai.ui.chat_widget.save_current_config", lambda: None)
    dock = SimpleNamespace(_current_instruction_snapshot="")

    ChatDockWidget._prepare_project_instructions(dock, "hello")

    assert dialog_calls == [changed.fingerprint]
    assert cfg.project_instruction_trust[changed.root]["fingerprint"] == changed.fingerprint
    assert dock._current_instruction_snapshot == "changed bytes"


def test_cancel_does_not_persist_or_replace_request_snapshot(tmp_path, monkeypatch):
    bundle = _bundle(tmp_path)
    cfg = SimpleNamespace(project_instruction_trust={})
    dialog_calls = []
    saves = []
    _patch_prepare_dependencies(
        monkeypatch, bundle, cfg, decision=None, dialog_calls=dialog_calls)
    monkeypatch.setattr(
        "freecad_ai.ui.chat_widget.save_current_config", lambda: saves.append(True))
    dock = SimpleNamespace(_current_instruction_snapshot="previous request")

    result = ChatDockWidget._prepare_project_instructions(dock, "preserve me")

    assert result is None
    assert dialog_calls == [bundle.fingerprint]
    assert cfg.project_instruction_trust == {}
    assert saves == []
    assert dock._current_instruction_snapshot == "previous request"


def test_resolver_failure_aborts_send_before_user_state_or_provider(monkeypatch):
    agents = _agents_module()
    monkeypatch.setattr(
        agents,
        "discover_instruction_bundle",
        lambda: (_ for _ in ()).throw(InstructionLoadError("unsafe include")),
    )
    monkeypatch.setattr(
        "freecad_ai.ui.chat_widget.QtWidgets.QMessageBox.warning",
        lambda *args: None,
    )

    class Input:
        clear_calls = 0

        def toPlainText(self):
            return "/unsafe"

        def clear(self):
            self.clear_calls += 1

    calls = []
    dock = SimpleNamespace(
        _worker=None,
        input_edit=Input(),
        _current_instruction_snapshot="previous request",
        _handle_skill_command=lambda text: calls.append(("skill", text)) or True,
        _continue_send=lambda: calls.append(("provider", None)),
        conversation=SimpleNamespace(messages=["unchanged"]),
        _attachment_strip=SimpleNamespace(items=["unchanged"]),
    )
    dock._prepare_project_instructions = (
        lambda text: ChatDockWidget._prepare_project_instructions(dock, text))

    ChatDockWidget._send_message(dock)

    assert dock.input_edit.clear_calls == 0
    assert dock.conversation.messages == ["unchanged"]
    assert dock._attachment_strip.items == ["unchanged"]
    assert dock._current_instruction_snapshot == "previous request"
    assert calls == []


@pytest.mark.parametrize(
    "bad_record",
    [
        None,
        {"source": "relative", "fingerprint": "sha256:" + "a" * 64,
         "decision": "allow", "timestamp": "now"},
        {"source": "SOURCE", "fingerprint": "sha256:" + "A" * 64,
         "decision": "allow", "timestamp": "now"},
        {"source": "SOURCE", "fingerprint": "sha256:" + "a" * 64,
         "decision": "yes", "timestamp": "now"},
        {"source": "SOURCE", "fingerprint": "sha256:" + "a" * 64,
         "decision": "allow", "timestamp": 1},
    ],
)
def test_invalid_trust_records_fail_closed(tmp_path, bad_record):
    bundle = _bundle(tmp_path)
    if isinstance(bad_record, dict) and bad_record.get("source") == "SOURCE":
        bad_record = {**bad_record, "source": bundle.source_path}
    trust = {bundle.root: bad_record}
    assert _agents_module()._trusted_decision(bundle, trust) is None


def test_approved_in_memory_snapshot_survives_disk_change(tmp_path, monkeypatch):
    source = tmp_path / "AGENTS.md"
    source.write_text("approved project bytes")
    bundle = InstructionBundle(
        root=os.path.realpath(tmp_path),
        source_path=os.path.realpath(source),
        content="approved project bytes",
        fingerprint="sha256:" + "a" * 64,
        manifest=("AGENTS.md",),
    )
    cfg = SimpleNamespace(project_instruction_trust={})
    dialog_calls = []
    _patch_prepare_dependencies(
        monkeypatch, bundle, cfg, decision="allow", dialog_calls=dialog_calls)
    monkeypatch.setattr(
        "freecad_ai.ui.chat_widget.save_current_config", lambda: None)
    dock = SimpleNamespace(_current_instruction_snapshot="")
    ChatDockWidget._prepare_project_instructions(dock, "hello")
    source.write_text("unapproved bytes after approval")

    prompt = build_system_prompt(agents_md=dock._current_instruction_snapshot)

    assert "approved project bytes" in prompt
    assert "unapproved bytes after approval" not in prompt


def test_prepare_contract_covers_first_changed_unchanged_and_all_actions():
    prepare = getattr(ChatDockWidget, "_prepare_project_instructions", None)
    assert prepare is not None
    source = inspect.getsource(prepare)
    assert "fingerprint" in source
    assert "allow" in source and "ignore" in source
    assert "ProjectInstructionsDialog" in source
    assert "_current_instruction_snapshot" in source
    dialog_source = inspect.getsource(ProjectInstructionsDialog)
    assert dialog_source.count("setReadOnly(True)") == 2
    assert "Trust and send" in dialog_source
    assert "Ignore this version" in dialog_source
    assert "Cancel" in dialog_source
    assert "self.decision = \"allow\"" in dialog_source
    assert "self.decision = \"ignore\"" in dialog_source
    assert "cancel_button.clicked.connect(self.reject)" in dialog_source


def test_cancel_precedes_input_clear_and_conversation_mutation():
    source = inspect.getsource(ChatDockWidget._send_message)
    assert "_prepare_project_instructions" in source
    prepare_at = source.index("_prepare_project_instructions")
    assert prepare_at < source.index("input_edit.clear")
    assert prepare_at < source.index("add_user_message")
    assert "if prepared is None" in source


def test_approved_snapshot_not_disk_is_passed_to_provider_prompt():
    source = inspect.getsource(ChatDockWidget._continue_send)
    assert "_current_instruction_snapshot" in source
    assert "agents_md=" in source
    assert source.index("_current_instruction_snapshot") < source.index("build_system_prompt")
    assert "load_agents_md" not in source
