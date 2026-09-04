"""Shared fixtures for FreeCAD AI tests."""

import os
import sys
import tempfile

import pytest

# Configuration is imported while test modules are collected, before fixtures
# can redirect its module-level paths.  Force that first resolution into a
# process-private temporary directory so collection and un-fixtured tests can
# never inspect or mutate the user's real FreeCAD configuration.
_SESSION_CONFIG_DIR = tempfile.TemporaryDirectory(
    prefix="freecad-ai-pytest-config-"
)
os.environ["FREECAD_AI_CONFIG_DIR"] = os.path.realpath(_SESSION_CONFIG_DIR.name)

# Add project root to path so `freecad_ai` package is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    """Redirect all config paths to a temp directory."""
    import freecad_ai.config as config_mod

    paths = {
        "CONFIG_DIR": tmp_path / "config",
        "CONVERSATIONS_DIR": tmp_path / "conversations",
        "SKILLS_DIR": tmp_path / "skills",
        "USER_TOOLS_DIR": tmp_path / "tools",
        "HOOKS_DIR": tmp_path / "hooks",
        "LOGS_DIR": tmp_path / "logs",
        "BACKUPS_DIR": tmp_path / "backups",
        "SECRETS_DIR": tmp_path / "secrets",
    }
    for path in paths.values():
        path.mkdir()
    for name, path in paths.items():
        monkeypatch.setattr(config_mod, name, str(path))
    monkeypatch.setattr(
        config_mod, "CONFIG_FILE", str(paths["CONFIG_DIR"] / "config.json")
    )
    monkeypatch.setattr(
        config_mod,
        "MCP_SERVER_TOKEN_FILE",
        str(paths["CONFIG_DIR"] / "mcp_server.token"),
        raising=False,
    )

    return tmp_path


@pytest.fixture(autouse=True)
def reset_config_singleton():
    """Reset the config singleton after each test."""
    yield
    import freecad_ai.config as config_mod
    config_mod._config = None


@pytest.fixture
def mock_skills_dir(tmp_path):
    """Create a temp skills directory with sample skills."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Create a sample skill
    sample = skills_dir / "test-skill"
    sample.mkdir()
    (sample / "SKILL.md").write_text(
        "# Test Skill\n\nA sample skill for testing.\n\nDo something useful.\n"
    )

    # Create a skill with a handler
    handled = skills_dir / "handled-skill"
    handled.mkdir()
    (handled / "SKILL.md").write_text(
        "# Handled Skill\n\nSkill with a Python handler.\n"
    )
    (handled / "handler.py").write_text(
        'def execute(args):\n    return {"output": f"Handled: {args}"}\n'
    )

    return skills_dir
