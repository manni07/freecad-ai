"""Upstream profiles must retain the fork's private-key migration contract."""

import json
from pathlib import Path

from freecad_ai import config, secure_storage


def _seed_profiles(monkeypatch):
    monkeypatch.setattr(config, "_get_param_group", lambda: None)
    cfg = config.AppConfig.from_dict({
        "profiles": {
            "chat": {"name": "ollama", "api_key": ""},
            "cloud": {"name": "openai", "api_key": "cloud-test-secret"},
            "rerank": {"name": "custom", "api_key": "rerank-test-secret"},
        },
        "active_profile": "chat",
        "utility_profiles": {"compaction": "cloud", "rerank": "rerank"},
        "project_instruction_trust": {"/fixture": {"fingerprint": "approved"}},
        "mcp_server_token_file": "/fixture/private.token",
    })
    original = json.dumps(cfg.to_dict()).encode()
    Path(config.CONFIG_FILE).write_bytes(original)
    return original


def test_inactive_utility_keys_migrate_without_changing_profiles(
        tmp_config_dir, monkeypatch):
    _seed_profiles(monkeypatch)
    cfg = config.load_config()
    persisted = Path(config.CONFIG_FILE).read_bytes()
    for label, literal in (("cloud", "cloud-test-secret"),
                           ("rerank", "rerank-test-secret")):
        reference = cfg.profiles[label].api_key
        assert reference.startswith("file:")
        assert Path(reference.removeprefix("file:")).read_text() == literal
        assert literal.encode() not in persisted
    assert cfg.active_profile == "chat"
    assert cfg.utility_profiles == {"compaction": "cloud", "rerank": "rerank"}
    assert cfg.project_instruction_trust == {"/fixture": {"fingerprint": "approved"}}
    assert cfg.mcp_server_token_file == "/fixture/private.token"
    assert config.load_config().to_dict() == cfg.to_dict()


def test_profile_migration_rolls_back_all_keys_if_later_profile_fails(
        tmp_config_dir, monkeypatch):
    original = _seed_profiles(monkeypatch)
    real_migrate = secure_storage.migrate_literal_secret
    seen = []

    def fail_later(value, directory, stem):
        seen.append(value)
        if value == "rerank-test-secret":
            raise OSError("injected later-profile failure")
        return real_migrate(value, directory, stem)

    monkeypatch.setattr(secure_storage, "migrate_literal_secret", fail_later)
    cfg = config.load_config()
    assert "cloud-test-secret" in seen
    assert "rerank-test-secret" in seen
    assert Path(config.CONFIG_FILE).read_bytes() == original
    assert cfg.profiles["cloud"].api_key == "cloud-test-secret"
    assert list(Path(config.SECRETS_DIR).iterdir()) == []


def test_profile_settings_keep_mandatory_file_token_policy(
        tmp_config_dir, monkeypatch):
    from freecad_ai.ui.compat import QtWidgets
    from freecad_ai.ui.settings_dialog import SettingsDialog

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    dialog = SettingsDialog()
    try:
        labels = "\n".join(label.text() for label in dialog.findChildren(QtWidgets.QLabel))
        assert "Every MCP request requires the installation's bearer token" in labels
        assert not hasattr(dialog, "mcp_server_auth_token_edit")
        assert hasattr(dialog, "profile_combo")
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
