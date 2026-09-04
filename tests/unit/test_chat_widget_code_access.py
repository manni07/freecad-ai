"""Execution-edge and GUI review invariants for session code access."""
import importlib
import inspect
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from freecad_ai.llm.client import LLMStreamEvent, ToolCall
from freecad_ai.tools.registry import ToolResult
from freecad_ai.ui.chat_widget import ChatDockWidget


def _access(active):
    try:
        access = importlib.import_module("freecad_ai.core.code_execution_access").get_code_execution_access()
    except ModuleNotFoundError as exc:
        pytest.fail(f"missing execution-edge gate: {exc}")
    access.arm() if active else access.disarm()
    return access


@pytest.fixture(autouse=True)
def _isolate_process_access():
    access = _access(False)
    yield
    access.disarm()


def _bare_widget(registry=None):
    widget = SimpleNamespace(_tool_registry=registry, _worker=Mock())
    return widget

def test_dock_declares_dedicated_toggle_before_dangerous_toggle():
    source = inspect.getsource(ChatDockWidget._build_ui)
    assert "code_access_toggle" in source
    assert source.index("code_access_toggle") < source.index("danger_toggle")


def test_toggle_warning_defaults_no_and_no_leaves_access_disarmed():
    access = _access(False)

    class Toggle:
        checked = True
        def blockSignals(self, _blocked):
            pass
        def setChecked(self, value):
            self.checked = value
        def isChecked(self):
            return self.checked

    class Box:
        Warning = 1
        Yes = 2
        No = 3
        default = None
        def __init__(self, _parent):
            pass
        def setIcon(self, _value):
            pass
        def setWindowTitle(self, _value):
            pass
        def setText(self, _value):
            pass
        def setInformativeText(self, _value):
            pass
        def setStandardButtons(self, _value):
            pass
        def setDefaultButton(self, value):
            type(self).default = value
        def exec(self):
            return self.No

    widget = SimpleNamespace(code_access_toggle=Toggle())
    with patch("freecad_ai.ui.chat_widget.QtWidgets.QMessageBox", Box):
        ChatDockWidget._on_code_access_toggled(widget, True)
    assert Box.default == Box.No
    assert access.active is False
    assert widget.code_access_toggle.checked is False


def test_toggle_yes_arms_and_explicit_off_disarms_process_access():
    access = _access(False)

    class Toggle:
        checked = True

        def blockSignals(self, _blocked):
            pass

        def setChecked(self, value):
            self.checked = value

        def isChecked(self):
            return self.checked

    class Box:
        Warning = 1
        Yes = 2
        No = 3

        def __init__(self, _parent):
            pass

        def setIcon(self, _value):
            pass

        def setWindowTitle(self, _value):
            pass

        def setText(self, _value):
            pass

        def setInformativeText(self, _value):
            pass

        def setStandardButtons(self, _value):
            pass

        def setDefaultButton(self, _value):
            pass

        def exec(self):
            return self.Yes

    widget = SimpleNamespace(code_access_toggle=Toggle())
    widget._update_code_access_toggle = lambda: None
    with patch("freecad_ai.ui.chat_widget.QtWidgets.QMessageBox", Box):
        ChatDockWidget._on_code_access_toggled(widget, True)
    assert access.active is True

    ChatDockWidget._on_code_access_toggled(widget, False)
    assert access.active is False

def test_new_chat_does_not_disarm_process_code_access():
    source = inspect.getsource(ChatDockWidget._new_chat)
    assert "disarm" not in source and "code_execution_access" not in source


def test_new_chat_preserves_armed_process_state():
    access = _access(True)
    old_conversation = Mock(messages=[])
    widget = SimpleNamespace(
        _optimization_active=False,
        conversation=old_conversation,
        _refresh_input_history=Mock(),
        chat_display=Mock(),
        _update_token_count=Mock(),
    )
    replacement = Mock(messages=[])
    with patch("freecad_ai.ui.chat_widget.Conversation", return_value=replacement):
        ChatDockWidget._new_chat(widget)
    assert widget.conversation is replacement
    assert access.active is True
    access.disarm()

def test_dock_construction_synchronizes_from_process_singleton():
    source = inspect.getsource(ChatDockWidget._build_ui)
    assert "_update_code_access_toggle" in source
    assert "get_code_execution_access" in inspect.getsource(ChatDockWidget._update_code_access_toggle)


def test_recreated_docks_reflect_the_same_process_state():
    access = _access(True)

    class Toggle:
        def __init__(self):
            self.checked = False
        def isChecked(self):
            return self.checked
        def blockSignals(self, _blocked):
            pass
        def setChecked(self, value):
            self.checked = value

    first = SimpleNamespace(code_access_toggle=Toggle())
    recreated = SimpleNamespace(code_access_toggle=Toggle())
    ChatDockWidget._update_code_access_toggle(first)
    ChatDockWidget._update_code_access_toggle(recreated)
    assert first.code_access_toggle.checked is True
    assert recreated.code_access_toggle.checked is True
    access.disarm()

def test_stale_execute_code_call_after_disarm_never_dispatches():
    registry = Mock(); registry.execute.return_value = ToolResult(True, "mutated")
    widget = _bare_widget(registry); _access(False)
    ChatDockWidget._execute_tool_call(widget, "execute_code", json.dumps({"code": "mutate()"}))
    registry.execute.assert_not_called()
    assert widget._worker.set_tool_result.call_args.args[0]["success"] is False
    widget._worker.set_tool_result.assert_called_once()

def test_cancelled_review_returns_rejection_without_registry_mutation():
    registry = Mock(); widget = _bare_widget(registry); dialog = Mock(); dialog.get_result.return_value = None; _access(True)
    with patch("freecad_ai.ui.chat_widget.CodeReviewDialog", return_value=dialog):
        ChatDockWidget._execute_tool_call(widget, "execute_code", '{"code":"exact bytes"}')
    registry.execute.assert_not_called()
    assert "reject" in widget._worker.set_tool_result.call_args.args[0]["error"].lower()
    widget._worker.set_tool_result.assert_called_once()


def test_malformed_execute_code_arguments_fail_before_review_or_registry():
    registry = Mock()
    widget = _bare_widget(registry)
    _access(True)

    with patch("freecad_ai.ui.chat_widget.CodeReviewDialog") as dialog:
        ChatDockWidget._execute_tool_call(widget, "execute_code", "not-json")

    dialog.assert_not_called()
    registry.execute.assert_not_called()
    result = widget._worker.set_tool_result.call_args.args[0]
    assert result["success"] is False
    assert "invalid" in result["error"].lower()


def test_non_code_tool_without_registry_returns_explicit_failure():
    widget = _bare_widget(None)

    ChatDockWidget._execute_tool_call(widget, "create_body", "{}")

    assert widget._worker.set_tool_result.call_args.args[0] == {
        "success": False,
        "output": "",
        "error": "No tool registry",
    }

def test_each_approved_call_reviews_and_executes_exact_bytes_once():
    registry = Mock(); widget = _bare_widget(registry); approved = SimpleNamespace(success=True, stdout="ok", stderr=""); dialogs = []; _access(True)
    def make_dialog(code, parent):
        dialog = Mock(); dialog.get_result.return_value = approved; dialogs.append((code, dialog)); return dialog
    with patch("freecad_ai.ui.chat_widget.CodeReviewDialog", side_effect=make_dialog):
        ChatDockWidget._execute_tool_call(widget, "execute_code", '{"code":"A\\nB"}')
        ChatDockWidget._execute_tool_call(widget, "execute_code", '{"code":"A\\nB"}')
    assert [code for code, _ in dialogs] == ["A\nB", "A\nB"]
    assert all(dialog.exec.call_count == 1 for _, dialog in dialogs)
    assert widget._worker.set_tool_result.call_count == 2
    registry.execute.assert_not_called()


def test_tool_call_execution_never_consults_auto_execute():
    source = inspect.getsource(ChatDockWidget._execute_tool_call)
    assert "auto_execute" not in source
    assert "CodeReviewDialog" in source

def test_auto_execute_never_bypasses_review_but_manual_plan_stays_available():
    act_source = inspect.getsource(ChatDockWidget._handle_act_mode)
    assert "if cfg.auto_execute" not in act_source and "CodeReviewDialog" in act_source
    assert "CodeReviewDialog" in inspect.getsource(ChatDockWidget.execute_code_from_plan)


class _LoopClient:
    def __init__(self, first_turn):
        self.first_turn = first_turn
        self.calls = 0
        self.response_truncated = False

    def stream_with_tools(self, messages, system="", tools=None):
        self.calls += 1
        if self.calls == 1:
            yield from self.first_turn
        else:
            yield LLMStreamEvent(type="text_delta", text="continued")
            yield LLMStreamEvent(type="done")


def _loop_worker(execute):
    return SimpleNamespace(
        messages=[{"role": "user", "content": "do it"}],
        system_prompt="",
        tools=[{"type": "function"}],
        api_style="openai",
        registry=None,
        conversation=None,
        _max_tool_turns=5,
        _full_response="",
        _thinking_text="",
        _strip_thinking=False,
        _tool_timeline=[],
        _tool_results=[],
        _response_truncated=False,
        isInterruptionRequested=lambda: False,
        token_received=Mock(),
        thinking_received=Mock(),
        tool_call_started=Mock(),
        tool_call_finished=Mock(),
        response_finished=Mock(),
        _execute_tool_on_main_thread=execute,
    )


def _gui_cancel_result():
    _access(True)
    widget = _bare_widget(Mock())
    dialog = Mock()
    dialog.get_result.return_value = None
    with patch("freecad_ai.ui.chat_widget.CodeReviewDialog", return_value=dialog):
        ChatDockWidget._execute_tool_call(
            widget, "execute_code", '{"code":"review me"}')
    return widget._worker.set_tool_result.call_args.args[0]


def _tool_turn(*names):
    events = []
    for index, name in enumerate(names):
        events.append(LLMStreamEvent(
            type="tool_call_end",
            tool_call=ToolCall(
                id=f"call_{index}", name=name,
                arguments={"code": "review me"} if name == "execute_code" else {},
            ),
        ))
    events.append(LLMStreamEvent(type="done"))
    return events


def test_rejected_execute_code_is_terminal_and_stops_provider_loop():
    """User rejection is an authorization decision, not model feedback."""
    rejection = _gui_cancel_result()
    execute = Mock(return_value=rejection)
    worker = _loop_worker(execute)
    client = _LoopClient(_tool_turn("execute_code"))

    with patch("freecad_ai.hooks.fire_hook", return_value={}):
        from freecad_ai.ui.chat_widget import _LLMWorker
        _LLMWorker._tool_loop(worker, client)

    assert client.calls == 1
    assert rejection.get("terminal") is True
    execute.assert_called_once()


def test_rejected_execute_code_discards_later_tools_in_same_batch():
    """A later tool must not mutate the document after consent was denied."""
    rejection = _gui_cancel_result()
    execute = Mock(side_effect=[
        rejection,
        {"success": True, "output": "must not run", "error": ""},
    ])
    worker = _loop_worker(execute)
    client = _LoopClient(_tool_turn("execute_code", "create_body"))

    with patch("freecad_ai.hooks.fire_hook", return_value={}):
        from freecad_ai.ui.chat_widget import _LLMWorker
        _LLMWorker._tool_loop(worker, client)

    assert [call.args[0] for call in execute.call_args_list] == ["execute_code"]
    assert client.calls == 1
    assert [call["id"] for call in worker._tool_results[0]["tool_calls"]] == [
        "call_0", "call_1"]
    trace_results = worker._tool_results[0]["results"]
    assert [result["tool_call_id"] for result in trace_results] == [
        "call_0", "call_1"]
    assert "Rejected by user" in trace_results[0]["content"]
    assert "Skipped after authorization was denied" in trace_results[1]["content"]
    finished_names = [call.args[0] for call in worker.tool_call_finished.emit.call_args_list]
    assert finished_names == ["execute_code", "create_body"]


def test_anthropic_terminal_denial_emits_protocol_complete_skipped_result():
    rejection = _gui_cancel_result()
    execute = Mock(return_value=rejection)
    worker = _loop_worker(execute)
    worker.api_style = "anthropic"
    client = _LoopClient(_tool_turn("execute_code", "create_body"))
    original_stream = client.stream_with_tools

    def capture_messages(messages, **kwargs):
        client.seen_messages = messages
        yield from original_stream(messages, **kwargs)

    client.stream_with_tools = capture_messages

    with patch("freecad_ai.hooks.fire_hook", return_value={}):
        from freecad_ai.ui.chat_widget import _LLMWorker
        _LLMWorker._tool_loop(worker, client)

    messages = client.seen_messages[-2:]
    assert [item["role"] for item in messages] == ["user", "user"]
    skipped = messages[1]["content"][0]
    assert skipped["type"] == "tool_result"
    assert skipped["tool_use_id"] == "call_1"
    assert "Skipped" in skipped["content"]


def test_ordinary_tool_failure_remains_non_terminal():
    """Only explicit authorization denial halts; normal errors reach the model."""
    execute = Mock(return_value={
        "success": False, "output": "", "error": "ordinary failure"})
    worker = _loop_worker(execute)
    client = _LoopClient(_tool_turn("create_body"))

    with patch("freecad_ai.hooks.fire_hook", return_value={}):
        from freecad_ai.ui.chat_widget import _LLMWorker
        _LLMWorker._tool_loop(worker, client)

    assert client.calls == 2
    execute.assert_called_once()
