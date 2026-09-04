"""AGENTS.md loader with multi-location search, includes, and variable substitution.

Looks for project-level instruction files (AGENTS.md or FREECAD_AI.md) in:
  1. Active document's directory
  2. Parent directories (up to 3 levels)
  3. User config: ~/.config/FreeCAD/FreeCADAI/AGENTS.md

Supports:
  - Include directives: <!-- include: other_file.md -->
  - Variable substitution: {{document_name}}, {{object_count}}, etc.
"""

import hashlib
import os
import re
import stat
from dataclasses import dataclass

from ..config import CONFIG_DIR, get_config

# Filenames to search for, in priority order
INSTRUCTION_FILENAMES = ["AGENTS.md", "FREECAD_AI.md"]

# Regex for include directives: <!-- include: filename.md -->
INCLUDE_RE = re.compile(r"<!--\s*include:\s*(.+?)\s*-->")

# Regex for variable placeholders: {{variable_name}}
VARIABLE_RE = re.compile(r"\{\{(\w+)\}\}")

# Max parent directories to search upward
MAX_PARENT_LEVELS = 3

# Max include depth to prevent infinite recursion
MAX_INCLUDE_DEPTH = 5

MAX_INSTRUCTION_FILE_BYTES = 64 * 1024
MAX_INSTRUCTION_BUNDLE_BYTES = 256 * 1024
_FINGERPRINT_VERSION = b"freecad-ai-instruction-bundle-v1"


class InstructionLoadError(ValueError):
    """The selected instruction bundle could not be loaded safely."""


@dataclass(frozen=True)
class InstructionBundle:
    root: str
    source_path: str
    content: str
    fingerprint: str
    manifest: tuple[str, ...]


def _selected_instruction_source() -> str | None:
    """Return the selected instruction file without reading its contents."""
    doc_dir = _get_document_directory()
    if doc_dir:
        current = os.path.realpath(doc_dir)
        for _ in range(MAX_PARENT_LEVELS + 1):
            for filename in INSTRUCTION_FILENAMES:
                path = os.path.join(current, filename)
                if os.path.lexists(path):
                    return path
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

    config_root = os.path.realpath(CONFIG_DIR)
    for filename in INSTRUCTION_FILENAMES:
        path = os.path.join(config_root, filename)
        if os.path.lexists(path):
            return path
    return None


def _frame_digest(digest, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _path_has_symlink(root: str, path: str) -> bool:
    """Return whether a path component below canonical root is a symlink."""
    relative = os.path.relpath(os.path.abspath(path), root)
    current = root
    for part in relative.split(os.sep):
        current = os.path.join(current, part)
        if os.path.islink(current):
            return True
    return False


def discover_instruction_bundle() -> InstructionBundle | None:
    """Capture a bounded, canonical instruction bundle or raise fail-closed."""
    selected = _selected_instruction_source()
    if selected is None:
        return None

    root = os.path.realpath(os.path.dirname(selected))
    source_path = os.path.realpath(selected)
    manifest = []
    fingerprint_parts = []
    active_paths = set()
    expanded_bytes = 0

    def expand(path: str, depth: int) -> str:
        nonlocal expanded_bytes
        if depth > MAX_INCLUDE_DEPTH:
            raise InstructionLoadError("Instruction include depth exceeds limit")
        if "\x00" in path:
            raise InstructionLoadError("Instruction include path contains NUL")

        lexical_path = os.path.abspath(path)
        canonical_path = os.path.realpath(lexical_path)
        try:
            contained = os.path.commonpath((root, canonical_path)) == root
        except ValueError as exc:
            raise InstructionLoadError("Instruction path is outside project root") from exc
        if not contained:
            raise InstructionLoadError("Instruction path is outside project root")
        if _path_has_symlink(root, lexical_path):
            raise InstructionLoadError("Instruction symlinks are not allowed")
        try:
            mode = os.stat(lexical_path, follow_symlinks=False).st_mode
        except OSError as exc:
            raise InstructionLoadError("Instruction file is unavailable") from exc
        if not stat.S_ISREG(mode):
            raise InstructionLoadError("Instruction target is not a regular file")
        if canonical_path in active_paths:
            raise InstructionLoadError("Instruction include cycle detected")

        try:
            with open(lexical_path, "rb") as stream:
                raw = stream.read(MAX_INSTRUCTION_FILE_BYTES + 1)
        except OSError as exc:
            raise InstructionLoadError("Instruction file could not be read") from exc
        if len(raw) > MAX_INSTRUCTION_FILE_BYTES:
            raise InstructionLoadError("Instruction file exceeds size limit")
        expanded_bytes += len(raw)
        if expanded_bytes > MAX_INSTRUCTION_BUNDLE_BYTES:
            raise InstructionLoadError("Instruction bundle exceeds size limit")
        try:
            decoded = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise InstructionLoadError("Instruction file is not valid UTF-8") from exc

        relative = os.path.relpath(canonical_path, root).replace(os.sep, "/")
        manifest.append(relative)
        fingerprint_parts.append((relative.encode("utf-8"), raw))
        active_paths.add(canonical_path)
        try:
            def replace_include(match):
                include_path = match.group(1).strip()
                if "\x00" in include_path or os.path.isabs(include_path):
                    raise InstructionLoadError("Invalid instruction include path")
                return expand(
                    os.path.join(os.path.dirname(canonical_path), include_path),
                    depth + 1,
                )

            return INCLUDE_RE.sub(replace_include, decoded)
        finally:
            active_paths.remove(canonical_path)

    content_before_substitution = expand(selected, 0)
    digest = hashlib.sha256()
    _frame_digest(digest, _FINGERPRINT_VERSION)
    for relative, raw in fingerprint_parts:
        _frame_digest(digest, relative)
        _frame_digest(digest, raw)
    fingerprint = "sha256:" + digest.hexdigest()
    return InstructionBundle(
        root=root,
        source_path=source_path,
        content=_substitute_variables(content_before_substitution),
        fingerprint=fingerprint,
        manifest=tuple(manifest),
    )


def _trusted_decision(bundle: InstructionBundle, trust: object) -> str | None:
    """Validate and return the exact fingerprint-scoped trust decision."""
    if not isinstance(trust, dict):
        return None
    root = bundle.root
    if os.path.realpath(root) != root:
        return None
    record = trust.get(root)
    if not isinstance(record, dict):
        return None
    source = record.get("source")
    fingerprint = record.get("fingerprint")
    decision = record.get("decision")
    timestamp = record.get("timestamp")
    if not isinstance(source, str) or os.path.realpath(source) != source:
        return None
    try:
        source_is_contained = os.path.commonpath((root, source)) == root
    except ValueError:
        return None
    if not source_is_contained or source != bundle.source_path:
        return None
    if not isinstance(fingerprint, str) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", fingerprint):
        return None
    if fingerprint != bundle.fingerprint:
        return None
    if decision not in ("allow", "ignore") or not isinstance(timestamp, str):
        return None
    return decision


def load_agents_md() -> str:
    """Return content only for the currently and exactly allowed bundle."""
    try:
        bundle = discover_instruction_bundle()
    except InstructionLoadError:
        return ""
    if bundle is None:
        return ""
    cfg = get_config()
    decision = _trusted_decision(
        bundle, getattr(cfg, "project_instruction_trust", {}))
    return bundle.content if decision == "allow" else ""


def _search_directory_chain(start_dir: str) -> str:
    """Search start_dir and its parents for instruction files."""
    current = start_dir
    for _ in range(MAX_PARENT_LEVELS + 1):
        content = _load_from_directory(current)
        if content:
            return content
        parent = os.path.dirname(current)
        if parent == current:
            break  # Reached filesystem root
        current = parent
    return ""


def _load_from_directory(directory: str) -> str:
    """Try to load an instruction file from a directory."""
    if not directory or not os.path.isdir(directory):
        return ""

    for filename in INSTRUCTION_FILENAMES:
        path = os.path.join(directory, filename)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except (OSError, UnicodeDecodeError):
                continue
    return ""


def _find_base_dir(doc_dir: str) -> str:
    """Find the directory containing the loaded AGENTS.md for resolving includes."""
    if doc_dir:
        current = doc_dir
        for _ in range(MAX_PARENT_LEVELS + 1):
            for filename in INSTRUCTION_FILENAMES:
                if os.path.isfile(os.path.join(current, filename)):
                    return current
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

    # Check config dir
    for filename in INSTRUCTION_FILENAMES:
        if os.path.isfile(os.path.join(CONFIG_DIR, filename)):
            return CONFIG_DIR

    return ""


def _resolve_includes(content: str, base_dir: str, depth: int) -> str:
    """Resolve <!-- include: filename.md --> directives."""
    if depth >= MAX_INCLUDE_DEPTH or not base_dir:
        return content

    def replace_include(match):
        include_path = match.group(1).strip()
        # Resolve relative to base_dir
        full_path = os.path.join(base_dir, include_path)
        if os.path.isfile(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    included = f.read()
                # Recursively resolve includes in the included file
                return _resolve_includes(included, os.path.dirname(full_path), depth + 1)
            except (OSError, UnicodeDecodeError):
                return f"<!-- include failed: {include_path} -->"
        return f"<!-- include not found: {include_path} -->"

    return INCLUDE_RE.sub(replace_include, content)


def _substitute_variables(content: str) -> str:
    """Replace {{variable}} placeholders with live values."""
    variables = _get_variables()

    def replace_var(match):
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))  # Keep original if unknown

    return VARIABLE_RE.sub(replace_var, content)


def _get_variables() -> dict:
    """Get current variable values for substitution."""
    variables = {
        "document_name": "",
        "document_path": "",
        "object_count": "0",
        "active_body": "",
    }

    try:
        import FreeCAD as App
        doc = App.ActiveDocument
        if doc:
            variables["document_name"] = doc.Name
            variables["document_path"] = doc.FileName or "(unsaved)"
            variables["object_count"] = str(len(doc.Objects))

            # Find active body
            for obj in doc.Objects:
                if hasattr(obj, "TypeId") and obj.TypeId == "PartDesign::Body":
                    if hasattr(obj, "IsActive") and obj.IsActive:
                        variables["active_body"] = obj.Label
                        break
    except ImportError:
        pass

    return variables


def _get_document_directory() -> str:
    """Get the directory containing the active FreeCAD document.

    Returns empty string if no document is open or it hasn't been saved.
    """
    try:
        import FreeCAD as App
        doc = App.ActiveDocument
        if doc and doc.FileName:
            return os.path.dirname(doc.FileName)
    except ImportError:
        pass
    return ""
