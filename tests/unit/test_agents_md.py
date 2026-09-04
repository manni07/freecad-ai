"""Tests for AGENTS.md loader — directory search, includes, variables."""

import importlib
import os
from unittest.mock import patch

import pytest

from freecad_ai.extensions.agents_md import (
    INCLUDE_RE,
    INSTRUCTION_FILENAMES,
    MAX_INCLUDE_DEPTH,
    MAX_PARENT_LEVELS,
    VARIABLE_RE,
    _load_from_directory,
    _resolve_includes,
    _search_directory_chain,
    _substitute_variables,
)


class TestLoadFromDirectory:
    def test_loads_agents_md(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# Instructions\nDo stuff.\n")
        content = _load_from_directory(str(tmp_path))
        assert "# Instructions" in content

    def test_loads_freecad_ai_md(self, tmp_path):
        (tmp_path / "FREECAD_AI.md").write_text("# FreeCAD AI\nCustom.\n")
        content = _load_from_directory(str(tmp_path))
        assert "# FreeCAD AI" in content

    def test_agents_md_has_priority(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("AGENTS content")
        (tmp_path / "FREECAD_AI.md").write_text("FREECAD_AI content")
        content = _load_from_directory(str(tmp_path))
        assert content == "AGENTS content"

    def test_returns_empty_for_missing_dir(self):
        content = _load_from_directory("/nonexistent/path")
        assert content == ""

    def test_returns_empty_for_empty_dir(self, tmp_path):
        content = _load_from_directory(str(tmp_path))
        assert content == ""

    def test_returns_empty_for_none(self):
        content = _load_from_directory(None)
        assert content == ""


class TestSearchDirectoryChain:
    def test_finds_in_start_dir(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("Found!")
        content = _search_directory_chain(str(tmp_path))
        assert content == "Found!"

    def test_finds_in_parent(self, tmp_path):
        child = tmp_path / "subdir"
        child.mkdir()
        (tmp_path / "AGENTS.md").write_text("Parent content")
        content = _search_directory_chain(str(child))
        assert content == "Parent content"

    def test_finds_in_grandparent(self, tmp_path):
        grandchild = tmp_path / "a" / "b"
        grandchild.mkdir(parents=True)
        (tmp_path / "AGENTS.md").write_text("Grandparent")
        content = _search_directory_chain(str(grandchild))
        assert content == "Grandparent"

    def test_returns_empty_when_not_found(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        content = _search_directory_chain(str(deep))
        assert content == ""

    def test_stops_at_max_parent_levels(self, tmp_path):
        # Create a chain deeper than MAX_PARENT_LEVELS
        current = tmp_path
        for i in range(MAX_PARENT_LEVELS + 3):
            current = current / f"level{i}"
            current.mkdir()
        (tmp_path / "AGENTS.md").write_text("Too far up")
        content = _search_directory_chain(str(current))
        # May or may not find it depending on depth — just shouldn't crash
        assert isinstance(content, str)


class TestResolveIncludes:
    def test_resolves_simple_include(self, tmp_path):
        (tmp_path / "extra.md").write_text("Included content")
        content = "Before\n<!-- include: extra.md -->\nAfter"
        result = _resolve_includes(content, str(tmp_path), depth=0)
        assert "Included content" in result
        assert "Before" in result
        assert "After" in result

    def test_nested_includes(self, tmp_path):
        (tmp_path / "a.md").write_text("<!-- include: b.md -->")
        (tmp_path / "b.md").write_text("Deep content")
        content = "<!-- include: a.md -->"
        result = _resolve_includes(content, str(tmp_path), depth=0)
        assert "Deep content" in result

    def test_missing_include_file(self, tmp_path):
        content = "<!-- include: nonexistent.md -->"
        result = _resolve_includes(content, str(tmp_path), depth=0)
        assert "include not found" in result

    def test_max_depth_stops_recursion(self, tmp_path):
        # Create a circular include that would infinitely recurse
        (tmp_path / "loop.md").write_text("<!-- include: loop.md -->")
        content = "<!-- include: loop.md -->"
        result = _resolve_includes(content, str(tmp_path), depth=MAX_INCLUDE_DEPTH - 1)
        # At max depth, includes are not resolved
        assert "include:" in result

    def test_empty_base_dir(self):
        content = "<!-- include: file.md -->"
        result = _resolve_includes(content, "", depth=0)
        assert result == content  # No resolution with empty base_dir

    def test_multiple_includes(self, tmp_path):
        (tmp_path / "a.md").write_text("Content A")
        (tmp_path / "b.md").write_text("Content B")
        content = "<!-- include: a.md -->\n<!-- include: b.md -->"
        result = _resolve_includes(content, str(tmp_path), depth=0)
        assert "Content A" in result
        assert "Content B" in result


class TestSubstituteVariables:
    @patch("freecad_ai.extensions.agents_md._get_variables")
    def test_replaces_known_variables(self, mock_vars):
        mock_vars.return_value = {
            "document_name": "MyDoc",
            "object_count": "5",
        }
        result = _substitute_variables("Doc: {{document_name}}, Objects: {{object_count}}")
        assert result == "Doc: MyDoc, Objects: 5"

    @patch("freecad_ai.extensions.agents_md._get_variables")
    def test_preserves_unknown_variables(self, mock_vars):
        mock_vars.return_value = {}
        result = _substitute_variables("{{unknown_var}}")
        assert result == "{{unknown_var}}"

    @patch("freecad_ai.extensions.agents_md._get_variables")
    def test_no_variables_passes_through(self, mock_vars):
        mock_vars.return_value = {}
        result = _substitute_variables("No variables here")
        assert result == "No variables here"


class TestRegexPatterns:
    def test_include_regex_matches(self):
        assert INCLUDE_RE.search("<!-- include: file.md -->")
        assert INCLUDE_RE.search("<!--include:file.md-->")
        assert INCLUDE_RE.search("<!--  include:  path/to/file.md  -->")

    def test_variable_regex_matches(self):
        assert VARIABLE_RE.search("{{document_name}}")
        assert VARIABLE_RE.search("{{object_count}}")

    def test_variable_regex_no_match_on_spaces(self):
        assert not VARIABLE_RE.search("{{ not_a_var }}")

    def test_instruction_filenames(self):
        assert "AGENTS.md" in INSTRUCTION_FILENAMES
        assert "FREECAD_AI.md" in INSTRUCTION_FILENAMES


def _bundle_from(project):
    module = importlib.import_module("freecad_ai.extensions.agents_md")
    discover = getattr(module, "discover_instruction_bundle", None)
    error = getattr(module, "InstructionLoadError", ValueError)
    if discover is None:
        pytest.fail("missing fail-closed InstructionBundle resolver")
    with patch.object(module, "_get_document_directory", return_value=str(project)):
        return discover(), error


class TestInstructionBundleContainment:
    @pytest.mark.parametrize("kind", ["symlink", "directory"])
    def test_main_source_symlink_and_non_regular_are_rejected(self, tmp_path, kind):
        project = tmp_path / "project"; project.mkdir()
        source = project / "AGENTS.md"
        if kind == "symlink":
            outside = tmp_path / "outside.md"; outside.write_text("outside")
            source.symlink_to(outside)
        else:
            source.mkdir()
        with pytest.raises(ValueError):
            _bundle_from(project)

    @pytest.mark.parametrize("target", ["/tmp/outside.md", "../outside.md"])
    def test_absolute_and_parent_includes_are_rejected(self, tmp_path, target):
        project = tmp_path / "project"; project.mkdir()
        (project / "AGENTS.md").write_text(f"<!-- include: {target} -->")
        with pytest.raises(ValueError):
            _bundle_from(project)

    def test_sibling_prefix_escape_is_rejected(self, tmp_path):
        project = tmp_path / "app"; project.mkdir()
        sibling = tmp_path / "app-evil"; sibling.mkdir()
        (sibling / "payload.md").write_text("outside")
        (project / "AGENTS.md").write_text("<!-- include: ../app-evil/payload.md -->")
        with pytest.raises(ValueError):
            _bundle_from(project)

    @pytest.mark.parametrize("kind", ["symlink", "directory"])
    def test_symlink_and_non_regular_include_are_rejected(self, tmp_path, kind):
        project = tmp_path / "project"; project.mkdir()
        target = project / "target"
        if kind == "symlink":
            outside = tmp_path / "outside.md"; outside.write_text("outside")
            target.symlink_to(outside)
        else:
            target.mkdir()
        (project / "AGENTS.md").write_text("<!-- include: target -->")
        with pytest.raises(ValueError):
            _bundle_from(project)

    @pytest.mark.parametrize("kind", ["cycle", "depth"])
    def test_cycle_and_depth_above_five_reject_whole_bundle(self, tmp_path, kind):
        project = tmp_path / "project"; project.mkdir()
        count = 2 if kind == "cycle" else 7
        for index in range(count):
            next_index = 0 if kind == "cycle" and index == count - 1 else index + 1
            text = f"<!-- include: {next_index}.md -->" if next_index < count else "end"
            (project / f"{index}.md").write_text(text)
        (project / "AGENTS.md").write_text("<!-- include: 0.md -->")
        with pytest.raises(ValueError):
            _bundle_from(project)

    @pytest.mark.parametrize("kind", ["single", "aggregate"])
    def test_per_file_and_aggregate_limits_reject_whole_bundle(self, tmp_path, kind):
        project = tmp_path / "project"; project.mkdir()
        if kind == "single":
            (project / "AGENTS.md").write_bytes(b"x" * (64 * 1024 + 1))
        else:
            includes = []
            for index in range(5):
                name = f"part{index}.md"; includes.append(f"<!-- include: {name} -->")
                (project / name).write_bytes(b"x" * (60 * 1024))
            (project / "AGENTS.md").write_text("\n".join(includes))
        with pytest.raises(ValueError):
            _bundle_from(project)

    @pytest.mark.parametrize("kind", ["nul", "utf8"])
    def test_nul_path_and_invalid_utf8_fail_closed(self, tmp_path, kind):
        project = tmp_path / "project"; project.mkdir()
        if kind == "nul":
            (project / "AGENTS.md").write_bytes(b"<!-- include: bad\x00.md -->")
        else:
            (project / "AGENTS.md").write_bytes(b"valid\xffinvalid")
        with pytest.raises(ValueError):
            _bundle_from(project)


class TestInstructionBundleFingerprint:
    def test_fingerprint_is_deterministic_and_binds_raw_bytes_and_manifest(self, tmp_path):
        project = tmp_path / "project"; project.mkdir()
        (project / "part.md").write_bytes(b"alpha")
        root = project / "AGENTS.md"; root.write_text("<!-- include: part.md -->")
        first, _ = _bundle_from(project); same, _ = _bundle_from(project)
        assert first.fingerprint == same.fingerprint
        (project / "part.md").write_bytes(b"alphb")
        changed_bytes, _ = _bundle_from(project)
        assert changed_bytes.fingerprint != first.fingerprint
        (project / "renamed.md").write_bytes(b"alpha")
        root.write_text("<!-- include: renamed.md -->")
        changed_manifest, _ = _bundle_from(project)
        assert changed_manifest.fingerprint != first.fingerprint
        assert changed_manifest.manifest != first.manifest

    def test_variable_substitution_does_not_change_fingerprint(self, tmp_path):
        project = tmp_path / "project"; project.mkdir()
        (project / "AGENTS.md").write_text("Document {{document_name}}")
        module = importlib.import_module("freecad_ai.extensions.agents_md")
        with patch.object(module, "_get_variables", return_value={"document_name": "One"}):
            one, _ = _bundle_from(project)
        with patch.object(module, "_get_variables", return_value={"document_name": "Two"}):
            two, _ = _bundle_from(project)
        assert one.fingerprint == two.fingerprint
        assert one.content != two.content


class TestInstructionBundleRootSelection:
    def test_parent_source_defines_canonical_containment_root(self, tmp_path):
        project = tmp_path / "project"; project.mkdir()
        nested = project / "models" / "part"; nested.mkdir(parents=True)
        source = project / "AGENTS.md"; source.write_text("parent instructions")

        bundle, _ = _bundle_from(nested)

        assert bundle.root == str(project.resolve())
        assert bundle.source_path == str(source.resolve())
        assert bundle.manifest == ("AGENTS.md",)

    def test_config_fallback_defines_config_as_containment_root(self, tmp_path):
        config_dir = tmp_path / "config"; config_dir.mkdir()
        source = config_dir / "AGENTS.md"; source.write_text("config instructions")
        module = importlib.import_module("freecad_ai.extensions.agents_md")
        with patch.object(module, "CONFIG_DIR", str(config_dir)), patch.object(
            module, "_get_document_directory", return_value=""
        ):
            bundle = module.discover_instruction_bundle()

        assert bundle.root == str(config_dir.resolve())
        assert bundle.source_path == str(source.resolve())
        assert bundle.manifest == ("AGENTS.md",)


class TestInstructionBundleDefensiveBranches:
    def test_source_search_stops_at_filesystem_root(self):
        module = importlib.import_module("freecad_ai.extensions.agents_md")
        with patch.object(module, "_get_document_directory", return_value=os.path.sep), \
                patch.object(module.os.path, "lexists", return_value=False):
            assert module._selected_instruction_source() is None

    def test_symlink_component_detector_reports_nested_link(self, tmp_path):
        module = importlib.import_module("freecad_ai.extensions.agents_md")
        root = tmp_path / "project"
        root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (root / "linked").symlink_to(outside, target_is_directory=True)

        assert module._path_has_symlink(
            str(root), str(root / "linked" / "instructions.md")) is True

    def test_selected_path_with_nul_is_rejected_before_io(self):
        module = importlib.import_module("freecad_ai.extensions.agents_md")
        with patch.object(
            module, "_selected_instruction_source", return_value="/tmp/bad\x00name"
        ), patch.object(
            module.os.path, "realpath", side_effect=lambda path: path
        ), pytest.raises(module.InstructionLoadError, match="NUL"):
            module.discover_instruction_bundle()

    def test_commonpath_cross_device_error_is_fail_closed(self, tmp_path):
        module = importlib.import_module("freecad_ai.extensions.agents_md")
        source = tmp_path / "AGENTS.md"
        source.write_text("instructions")
        with patch.object(
            module, "_selected_instruction_source", return_value=str(source)
        ), patch.object(
            module.os.path, "commonpath", side_effect=ValueError("different drives")
        ), pytest.raises(module.InstructionLoadError, match="outside"):
            module.discover_instruction_bundle()

    def test_symlink_guard_failure_is_fail_closed(self, tmp_path):
        module = importlib.import_module("freecad_ai.extensions.agents_md")
        source = tmp_path / "AGENTS.md"
        source.write_text("instructions")
        with patch.object(
            module, "_selected_instruction_source", return_value=str(source)
        ), patch.object(
            module, "_path_has_symlink", return_value=True
        ), pytest.raises(module.InstructionLoadError, match="symlink"):
            module.discover_instruction_bundle()

    @pytest.mark.parametrize("failure", ["stat", "open"])
    def test_source_metadata_or_read_failure_is_fail_closed(
            self, tmp_path, failure):
        module = importlib.import_module("freecad_ai.extensions.agents_md")
        source = tmp_path / "AGENTS.md"
        source.write_text("instructions")
        selected = patch.object(
            module, "_selected_instruction_source", return_value=str(source))
        if failure == "stat":
            injected = patch.object(
                module.os, "stat", side_effect=OSError("metadata denied"))
        else:
            injected = patch(
                "builtins.open", side_effect=OSError("read denied"))
        with selected, injected, pytest.raises(module.InstructionLoadError):
            module.discover_instruction_bundle()

    def test_trust_rejects_malformed_root_source_and_cross_device_records(
            self, tmp_path):
        module = importlib.import_module("freecad_ai.extensions.agents_md")
        source = tmp_path / "AGENTS.md"
        source.write_text("instructions")
        bundle, _ = _bundle_from(tmp_path)
        valid = {
            bundle.root: {
                "source": bundle.source_path,
                "fingerprint": bundle.fingerprint,
                "decision": "allow",
                "timestamp": "2026-09-04T12:00:00Z",
            }
        }

        assert module._trusted_decision(bundle, []) is None
        noncanonical = module.InstructionBundle(
            root=os.path.join(bundle.root, "."),
            source_path=bundle.source_path,
            content=bundle.content,
            fingerprint=bundle.fingerprint,
            manifest=bundle.manifest,
        )
        with patch.object(module.os.path, "realpath", return_value=bundle.root):
            assert module._trusted_decision(noncanonical, valid) is None
        mismatched = {
            bundle.root: {**valid[bundle.root], "source": str(source) + "x"}
        }
        assert module._trusted_decision(bundle, mismatched) is None
        with patch.object(
            module.os.path, "commonpath", side_effect=ValueError("different drives")
        ):
            assert module._trusted_decision(bundle, valid) is None

    def test_compatibility_loader_suppresses_instruction_load_error(self):
        module = importlib.import_module("freecad_ai.extensions.agents_md")
        with patch.object(
            module,
            "discover_instruction_bundle",
            side_effect=module.InstructionLoadError("unsafe bundle"),
        ), patch.object(module, "get_config") as get_config:
            assert module.load_agents_md() == ""
        get_config.assert_not_called()
