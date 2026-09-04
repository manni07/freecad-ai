"""Release and support metadata contracts for SEC-07.

These tests intentionally use only the standard library.  Host-provided
FreeCAD, Qt and PySide are runtime inventory subjects, not packages that this
repository may silently pull from PyPI.
"""

import ast
import os
import re
import runpy
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

import freecad_ai

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_XML = ROOT / "package.xml"
PYPROJECT = ROOT / "pyproject.toml"
RUNTIME_POLICY = ROOT / "security" / "supported-runtime.json"
EXPECTED_ADDON_VERSION = "0.23.1-alpha"
EXPECTED_PYPROJECT_VERSION = "0.23.1a0"


def _project_metadata():
    with PYPROJECT.open("rb") as stream:
        return tomllib.load(stream)


def _package_metadata():
    return ET.parse(PACKAGE_XML).getroot()


def _prerelease_version(value):
    """Normalize only the two repository-supported alpha spellings."""
    match = re.fullmatch(
        r"(\d+)\.(\d+)\.(\d+)(?:(?:-alpha|a)(\d*))?", value)
    assert match is not None, f"unsupported release version spelling: {value!r}"
    major, minor, patch, alpha = match.groups()
    prerelease = None if alpha is None else ("alpha", int(alpha or 0))
    return int(major), int(minor), int(patch), prerelease


def test_package_module_and_pyproject_versions_are_semantically_identical():
    package_version = _package_metadata().findtext("version")
    pyproject_version = _project_metadata()["project"]["version"]

    assert package_version == EXPECTED_ADDON_VERSION
    assert freecad_ai.__version__ == EXPECTED_ADDON_VERSION
    assert pyproject_version == EXPECTED_PYPROJECT_VERSION
    assert _prerelease_version(package_version) == _prerelease_version(
        freecad_ai.__version__)
    assert _prerelease_version(pyproject_version) == _prerelease_version(
        package_version)


def test_python_minimum_is_311_in_package_pyproject_and_runtime_policy():
    import json

    package_python = _package_metadata().findtext("pythonmin")
    project_python = _project_metadata()["project"]["requires-python"]
    assert package_python == "3.11"
    assert project_python == ">=3.11"

    assert RUNTIME_POLICY.is_file(), "missing authoritative runtime policy"
    policy = json.loads(RUNTIME_POLICY.read_text(encoding="utf-8"))
    assert policy["minimum_versions"]["python"] == "3.11"


def test_pyproject_declares_no_pypi_runtime_dependencies():
    project = _project_metadata()["project"]
    assert "dependencies" in project
    assert project["dependencies"] == []


def test_setuptools_discovers_only_freecad_ai_packages():
    metadata = _project_metadata()
    discovery = (
        metadata.get("tool", {}).get("setuptools", {})
        .get("packages", {}).get("find"))
    assert isinstance(discovery, dict), (
        "pyproject must configure explicit setuptools package discovery")
    assert discovery["include"] == ["freecad_ai", "freecad_ai.*"]

    excluded = set(discovery["exclude"])
    required_exclusions = {
        "hooks*", "skills*", "Resources*", "resources*", "translations*",
        "tests*", "docs*", "security*",
    }
    assert required_exclusions <= excluded


def test_editable_metadata_build_is_offline_and_ignores_top_level_decoys(
        tmp_path):
    """Exercise the real pyproject in an isolated synthetic checkout.

    The copied top-level packages reproduce setuptools' flat-layout ambiguity,
    while --no-build-isolation and PIP_NO_INDEX make a network lookup
    impossible.  Nothing is written into the developer checkout.
    """
    project = tmp_path / "project"
    target = tmp_path / "site"
    project.mkdir()
    (project / "pyproject.toml").write_bytes(PYPROJECT.read_bytes())
    package = project / "freecad_ai"
    package.mkdir()
    (package / "__init__.py").write_text(
        f'__version__ = "{EXPECTED_ADDON_VERSION}"\n', encoding="utf-8")
    subpackage = package / "runtime_support"
    subpackage.mkdir()
    (subpackage / "__init__.py").write_text("", encoding="utf-8")
    prefix_collision = project / "freecad_ai_evil"
    prefix_collision.mkdir()
    (prefix_collision / "__init__.py").write_text("", encoding="utf-8")
    seen = {"freecad_ai"}
    for name in (
            "hooks", "skills", "Resources", "resources", "translations",
            "tests", "docs", "security"):
        # Default macOS volumes are case-insensitive, so Resources/resources
        # cannot both be materialized there. Their two exclusion patterns are
        # still asserted independently above.
        if name.casefold() in seen:
            continue
        seen.add(name.casefold())
        decoy = project / name
        decoy.mkdir()
        (decoy / "__init__.py").write_text("", encoding="utf-8")

    environment = os.environ.copy()
    environment.update({
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    completed = subprocess.run(
        [
            sys.executable, "-m", "pip", "install", "--editable", str(project),
            "--target", str(target), "--no-deps", "--no-build-isolation",
            "--disable-pip-version-check",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
        env=environment,
    )
    assert completed.returncode == 0, completed.stderr
    finder_files = list(target.glob("__editable__*finder.py"))
    assert len(finder_files) == 1
    editable_finder = runpy.run_path(str(finder_files[0]))["_EditableFinder"]
    assert editable_finder.find_spec("freecad_ai.runtime_support") is not None
    assert editable_finder.find_spec("freecad_ai_evil") is None
    metadata_files = list(target.glob("freecad_ai-*.dist-info/METADATA"))
    assert len(metadata_files) == 1
    metadata_text = metadata_files[0].read_text(encoding="utf-8")
    assert f"Version: {EXPECTED_PYPROJECT_VERSION}" in metadata_text


def test_supported_runtime_policy_is_conservative_and_explicit():
    import json

    assert RUNTIME_POLICY.is_file(), "missing authoritative runtime policy"
    policy = json.loads(RUNTIME_POLICY.read_text(encoding="utf-8"))
    assert policy["schema_version"] == 1
    assert policy["freecad_ai"]["version"] == EXPECTED_ADDON_VERSION
    assert policy["minimum_versions"] == {
        "freecad": "1.0",
        "python": "3.11",
    }
    assert {name.casefold() for name in policy["host_provided"]} >= {
        "pyside", "qt"}
    assert policy["tested"] == []


def _version_expression(module_path, constant_name):
    module = ast.parse(module_path.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == constant_name
                for target in node.targets):
            assert isinstance(node.value, ast.Dict)
            for key, value in zip(node.value.keys, node.value.values):
                if isinstance(key, ast.Constant) and key.value == "version":
                    return value
    raise AssertionError(f"{constant_name}.version assignment not found")


def test_mcp_client_and_server_versions_derive_from_package_version():
    from freecad_ai.mcp.client import CLIENT_INFO
    from freecad_ai.mcp.server import SERVER_INFO

    assert CLIENT_INFO["version"] == freecad_ai.__version__
    assert SERVER_INFO["version"] == freecad_ai.__version__
    for module_name, constant_name in (
            ("client.py", "CLIENT_INFO"), ("server.py", "SERVER_INFO")):
        expression = _version_expression(
            ROOT / "freecad_ai" / "mcp" / module_name, constant_name)
        assert isinstance(expression, ast.Name)
        assert expression.id == "__version__"


def test_security_ci_scopes_zero_pypi_result_away_from_host_components():
    workflow = ROOT / ".github" / "workflows" / "security-regression.yml"
    assert workflow.is_file(), "missing deterministic security CI workflow"
    text = workflow.read_text(encoding="utf-8").casefold()
    assert "pip-audit" in text
    assert "host-provided" in text
    assert "out of scope" in text
    for unsupported_claim in (
            "vulnerability-free", "no vulnerabilities", "host is secure"):
        assert unsupported_claim not in text


def test_security_ci_runs_runtime_inventory_contracts():
    workflow = ROOT / ".github" / "workflows" / "security-regression.yml"
    text = workflow.read_text(encoding="utf-8").casefold()

    assert "tests/unit/test_runtime_inventory.py" in text


def test_security_ci_runs_pip_audit_in_strict_mode():
    workflow = ROOT / ".github" / "workflows" / "security-regression.yml"
    text = workflow.read_text(encoding="utf-8").casefold()
    audit_commands = [
        line for line in text.splitlines() if "python -m pip_audit" in line
    ]

    assert len(audit_commands) == 1
    assert "--strict" in audit_commands[0]
    assert "--disable-pip" in audit_commands[0]
    assert "--no-deps" in audit_commands[0]
    assert "--requirement" in audit_commands[0]
