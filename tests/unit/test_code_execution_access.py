"""Process-only authorization tests for AI-proposed Python execution."""
import importlib
import json
from dataclasses import asdict

import pytest


def _module():
    try:
        return importlib.import_module("freecad_ai.core.code_execution_access")
    except ModuleNotFoundError as exc:
        pytest.fail(f"missing process-wide CodeExecutionAccess control: {exc}")


@pytest.fixture(autouse=True)
def _isolate_process_access():
    access = _module().get_code_execution_access()
    access.disarm()
    yield
    access.disarm()


def test_process_singleton_starts_disarmed_and_is_stable():
    module = _module()
    fresh = module.CodeExecutionAccess()
    first = module.get_code_execution_access()
    assert fresh.active is False
    assert first is module.get_code_execution_access()
    assert first.active is False

def test_arm_and_disarm_change_only_runtime_state():
    access = _module().get_code_execution_access(); access.arm(); assert access.active is True
    access.disarm(); assert access.active is False

def test_code_access_has_no_serialized_config_field():
    from freecad_ai.config import AppConfig

    access = _module().get_code_execution_access(); access.arm()
    assert "code_execution" not in json.dumps(asdict(AppConfig())).lower()
    assert access.active is True; access.disarm()

def test_code_access_and_dangerous_mode_are_independent_in_both_directions():
    from freecad_ai.core.dangerous_mode import get_dangerous_mode
    access = _module().get_code_execution_access(); danger = get_dangerous_mode()
    access.disarm(); danger.disarm(); danger.arm(); assert access.active is False
    access.arm(); danger.disarm(); assert access.active is True; access.disarm()
