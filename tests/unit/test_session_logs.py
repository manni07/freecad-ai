"""Session-log privacy policy tests."""

import json
import os
from types import SimpleNamespace

import pytest

from freecad_ai.ui.chat_widget import ChatDockWidget


def _worker():
    return SimpleNamespace(
        _tool_timeline=[
            {"name": "measure", "success": True, "elapsed": 0.25, "turn": 1},
            {"name": "broken", "success": False, "elapsed": 0.5, "turn": 2},
        ],
        _tool_results=[{
            "assistant_text": "assistant secret message",
            "tool_calls": [
                {"id": "call-1", "name": "measure",
                 "arguments": {"api_key": "configured-secret", "length": 10}},
                {"id": "call-2", "name": "broken", "arguments": {}},
            ],
            "results": [
                {"tool_call_id": "call-1",
                 "content": "sensitive tool result configured-secret"},
                {"tool_call_id": "call-2",
                 "content": "Error: ValueError: configured-secret is invalid"},
            ],
        }],
    )


def _config(mode):
    return SimpleNamespace(
        session_log_content=mode,
        max_session_logs=0,
        max_retention_age_days=0,
        provider=SimpleNamespace(api_key="configured-secret"),
        rerank_llm_api_key="reranker-secret",
    )


def _dock():
    return SimpleNamespace(
        _worker=_worker(),
        conversation=SimpleNamespace(messages=[
            {"role": "user", "content": "normal message configured-secret"},
            {"role": "assistant", "content": "ordinary answer"},
        ]),
        _append_html=lambda html: None,
    )


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode contract")
@pytest.mark.parametrize("method", ["auto", "manual"])
def test_metadata_log_omits_payloads_but_keeps_exact_operational_schema(
        tmp_path, monkeypatch, method):
    import stat

    import freecad_ai.ui.chat_widget as chat
    monkeypatch.setattr(chat, "LOGS_DIR", str(tmp_path))
    monkeypatch.setattr(chat, "get_config", lambda: _config("metadata"))

    dock = _dock()
    if method == "auto":
        ChatDockWidget._auto_save_log(dock)
        path = tmp_path / "latest_session.json"
    else:
        monkeypatch.setattr(chat, "prune_oldest_files", lambda *args: None)
        ChatDockWidget._save_session_log(dock)
        paths = list(tmp_path.glob("session_*.json"))
        assert len(paths) == 1
        path = paths[0]

    data = json.loads(path.read_text())
    encoded = json.dumps(data)
    assert "assistant secret message" not in encoded
    assert "sensitive tool result" not in encoded
    assert "configured-secret" not in encoded
    assert "arguments" not in encoded
    assert "messages" not in data
    assert set(data) == {"timestamp", "tool_trace"}
    trace = data["tool_trace"]
    assert set(trace[0]) == {"name", "success", "duration", "turn"}
    assert trace[0]["name"] == "measure"
    assert trace[0]["success"] is True
    assert trace[0]["duration"] == 0.25
    assert trace[0]["turn"] == 1
    assert set(trace[1]) == {
        "name", "success", "duration", "turn", "error_class"}
    assert trace[1]["error_class"] == "ValueError"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode contract")
@pytest.mark.parametrize("method", ["auto", "manual"])
def test_full_log_recursively_redacts_known_keys_and_configured_values(
        tmp_path, monkeypatch, method):
    import stat

    import freecad_ai.ui.chat_widget as chat
    monkeypatch.setattr(chat, "LOGS_DIR", str(tmp_path))
    monkeypatch.setattr(chat, "get_config", lambda: _config("full"))
    monkeypatch.setattr(chat, "prune_oldest_files", lambda *args: None)

    dock = _dock()
    if method == "auto":
        ChatDockWidget._auto_save_log(dock)
        path = tmp_path / "latest_session.json"
    else:
        ChatDockWidget._save_session_log(dock)
        paths = list(tmp_path.glob("session_*.json"))
        assert len(paths) == 1
        path = paths[0]
    encoded = path.read_text()
    if method == "manual":
        assert "ordinary answer" in encoded
    assert '"length": 10' in encoded
    assert "configured-secret" not in encoded
    assert "reranker-secret" not in encoded
    assert '"api_key": "[REDACTED]"' in encoded
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_auto_log_write_failure_is_visible_and_non_fatal(
        tmp_path, monkeypatch, capsys):
    import freecad_ai.ui.chat_widget as chat

    monkeypatch.setattr(chat, "LOGS_DIR", str(tmp_path))
    monkeypatch.setattr(chat, "get_config", lambda: _config("metadata"))
    monkeypatch.setattr(
        chat, "atomic_write_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    ChatDockWidget._auto_save_log(_dock())

    assert "automatic session log could not be saved" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []
