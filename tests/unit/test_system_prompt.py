"""Prompt parity with the process code-execution capability."""
import pytest

from freecad_ai.core.system_prompt import build_system_prompt


def _prompt(enabled):
    try:
        return build_system_prompt(mode="act", tools_enabled=True, code_tool_enabled=enabled)
    except TypeError as exc:
        pytest.fail(f"build_system_prompt lacks code_tool_enabled policy: {exc}")

def test_default_locked_prompt_omits_execute_code_recommendations():
    assert "execute_code" not in _prompt(False)


def test_omitted_code_tool_argument_is_locked_by_default():
    prompt = build_system_prompt(mode="act", tools_enabled=True)
    assert "execute_code" not in prompt


def test_armed_prompt_exposes_execute_code_recommendations():
    prompt = _prompt(True); assert "execute_code" in prompt; assert "last resort" in prompt.lower()


def test_armed_override_keeps_explicit_execute_code_guidance_verbatim():
    override = "Use execute_code only after the user approves this exact call."
    prompt = build_system_prompt(override=override, code_tool_enabled=True)
    assert override in prompt


def test_explicit_approved_agents_snapshot_is_used_without_disk_reload():
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "freecad_ai.core.system_prompt.load_agents_md",
            lambda: pytest.fail("approved request snapshot must not be re-read"),
        )
        prompt = build_system_prompt(agents_md="approved bytes")
    assert "approved bytes" in prompt


def test_explicit_empty_instruction_snapshot_never_falls_back_to_unapproved_disk():
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "freecad_ai.core.system_prompt.load_agents_md",
            lambda: "unapproved bytes from disk",
        )
        prompt = build_system_prompt(agents_md="")
    assert "unapproved bytes from disk" not in prompt
