"""Generate a privacy-preserving CycloneDX inventory of the active runtime."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import secrets
import stat
import sys
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_COMPONENT_ORDER = ("FreeCAD AI", "FreeCAD", "Python", "PySide", "Qt")
_COMPONENT_DEFINITIONS = {
    "FreeCAD AI": ("application", "freecad-ai:add-on"),
    "FreeCAD": ("application", "freecad-ai:host:freecad"),
    "Python": ("platform", "freecad-ai:runtime:python"),
    "PySide": ("framework", "freecad-ai:runtime:pyside"),
    "Qt": ("framework", "freecad-ai:runtime:qt"),
}
_MAX_VERSION_LENGTH = 256
_SENSITIVE_VERSION_MARKERS = (
    "api_key", "apikey", "authorization", "password", "secret", "token",
)
_VERSION_PATTERN = re.compile(r"[0-9][0-9A-Za-z._+~-]{0,255}\Z")


def _required_version(component: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"{component} version is unavailable")
    folded = value.casefold()
    if (len(value) > _MAX_VERSION_LENGTH
            or _VERSION_PATTERN.fullmatch(value) is None
            or any(marker in folded for marker in _SENSITIVE_VERSION_MARKERS)):
        raise ValueError(f"{component} version has an unsafe format")
    return value


def _component(name: str, version: object) -> dict[str, str]:
    component_type, bom_ref = _COMPONENT_DEFINITIONS[name]
    return {
        "type": component_type,
        "name": name,
        "version": _required_version(name, version),
        "bom-ref": bom_ref,
    }


def collect_runtime_components() -> list[dict[str, str]]:
    """Collect versions from the modules actually selected by the application."""
    import freecad_ai

    from .ui import compat

    addon_version = getattr(freecad_ai, "__version__", None)

    try:
        freecad = importlib.import_module("FreeCAD")
        freecad_parts = freecad.Version()
        if len(freecad_parts) < 3:
            raise ValueError
        freecad_version_parts = [str(part) for part in freecad_parts[:3]]
        if any(not part for part in freecad_version_parts):
            raise ValueError
        freecad_version = ".".join(freecad_version_parts)
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        raise RuntimeError("FreeCAD version is unavailable") from exc

    try:
        python_info = sys.version_info
        if len(python_info) < 3:
            raise ValueError
        python_version = ".".join(str(python_info[index]) for index in range(3))
    except (AttributeError, TypeError, ValueError) as exc:
        raise RuntimeError("Python version is unavailable") from exc

    binding = getattr(compat, "PYSIDE_VERSION", None)
    try:
        pyside = importlib.import_module(f"PySide{binding}")
        pyside_version = getattr(pyside, "__version__", None)
    except (ImportError, TypeError) as exc:
        raise RuntimeError("PySide version is unavailable") from exc

    try:
        qt_version = compat.QtCore.qVersion()
    except (AttributeError, TypeError) as exc:
        raise RuntimeError("Qt version is unavailable") from exc

    versions = {
        "FreeCAD AI": addon_version,
        "FreeCAD": freecad_version,
        "Python": python_version,
        "PySide": pyside_version,
        "Qt": qt_version,
    }
    return [_component(name, versions[name]) for name in _COMPONENT_ORDER]


def _canonical_components(
    components: Sequence[Mapping[str, object]],
) -> list[dict[str, str]]:
    by_name: dict[str, Mapping[str, object]] = {}
    for component in components:
        if not isinstance(component, Mapping):
            raise ValueError(  # noqa: TRY004 - public validation contract
                "runtime inventory component must be a mapping")
        name = component.get("name")
        if not isinstance(name, str) or name not in _COMPONENT_DEFINITIONS:
            raise ValueError("runtime inventory contains an unexpected component")
        if name in by_name:
            raise ValueError(f"runtime inventory contains duplicate {name}")
        by_name[name] = component

    missing = [name for name in _COMPONENT_ORDER if name not in by_name]
    if missing:
        raise ValueError(f"runtime inventory is missing {missing[0]}")
    if len(by_name) != len(_COMPONENT_ORDER):
        raise ValueError("runtime inventory must contain exactly five components")

    return [
        _component(name, by_name[name].get("version")) for name in _COMPONENT_ORDER
    ]


def build_cyclonedx_bom(
    components: Sequence[Mapping[str, object]],
) -> dict[str, Any]:
    """Build a deterministic CycloneDX 1.5 graph with a fresh document serial."""
    canonical = _canonical_components(components)
    addon_ref = _COMPONENT_DEFINITIONS["FreeCAD AI"][1]
    host_refs = [
        _COMPONENT_DEFINITIONS[name][1] for name in _COMPONENT_ORDER[1:]
    ]
    dependencies = [
        {"ref": addon_ref, "dependsOn": host_refs},
        *({"ref": ref, "dependsOn": []} for ref in host_refs),
    ]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "components": canonical,
        "dependencies": dependencies,
    }


def _validate_existing_ancestors(path: str) -> None:
    current = os.path.dirname(os.path.abspath(path))
    ancestors = []
    while current and current != os.path.dirname(current):
        ancestors.append(current)
        current = os.path.dirname(current)
    for ancestor in reversed(ancestors):
        if not os.path.lexists(ancestor):
            continue
        info = os.lstat(ancestor)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("BOM output parent must be a non-symlink directory")


def _validate_output_target(path: str) -> None:
    if not os.path.lexists(path):
        return
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError("BOM output must be a non-symlink regular file")


def _prepare_output_parent(path: str) -> str:
    """Validate first, then privately create only missing parent directories."""
    absolute = os.path.abspath(path)
    _validate_existing_ancestors(absolute)
    _validate_output_target(absolute)
    parent = os.path.dirname(absolute)
    missing = []
    current = parent
    while not os.path.lexists(current):
        missing.append(current)
        current = os.path.dirname(current)
    for directory in reversed(missing):
        try:
            os.mkdir(directory, 0o700)
        except FileExistsError:
            info = os.lstat(directory)
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise ValueError(
                    "BOM output parent must be a non-symlink directory") from None
            continue
        if os.name != "nt":
            os.chmod(directory, 0o700)
            if stat.S_IMODE(os.lstat(directory).st_mode) != 0o700:
                raise OSError("BOM output parent permissions could not be secured")
    _validate_existing_ancestors(absolute)
    return parent


def _atomic_write_bom_windows(path: str, data: bytes) -> None:
    """Best-effort Windows fallback; POSIX mode and ACL guarantees do not apply."""
    parent = _prepare_output_parent(path)
    basename = os.path.basename(path)
    temp_path = os.path.join(
        parent, f".{basename}.tmp-{os.getpid()}-{secrets.token_hex(8)}")
    fd = None
    try:
        fd = os.open(
            temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            fd = None
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _validate_existing_ancestors(path)
        _validate_output_target(path)
        os.replace(temp_path, path)
        if not stat.S_ISREG(os.lstat(path).st_mode):
            raise OSError("BOM output is not a regular file after replacement")
    finally:
        if fd is not None:
            os.close(fd)
        if os.path.lexists(temp_path):
            os.unlink(temp_path)


def _directory_open_flags() -> int:
    return (os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0))


def _open_pinned_parent(path: str) -> int:
    """Open every parent component without following symlinks."""
    parent = os.path.dirname(os.path.abspath(path))
    flags = _directory_open_flags()
    current_fd = os.open(os.path.sep, flags)
    try:
        for component in Path(parent).parts[1:]:
            try:
                next_fd = os.open(component, flags, dir_fd=current_fd)
            except FileNotFoundError:
                os.mkdir(component, 0o700, dir_fd=current_fd)
                next_fd = os.open(component, flags, dir_fd=current_fd)
                os.fchmod(next_fd, 0o700)
                if stat.S_IMODE(os.fstat(next_fd).st_mode) != 0o700:
                    os.close(next_fd)
                    raise OSError(
                        "BOM output parent permissions could not be secured")
            os.close(current_fd)
            current_fd = next_fd

        path_fd = os.open(parent, flags)
        try:
            pinned = os.fstat(current_fd)
            resolved = os.fstat(path_fd)
            if (pinned.st_dev, pinned.st_ino) != (resolved.st_dev, resolved.st_ino):
                raise OSError("BOM output parent identity changed")
        finally:
            os.close(path_fd)
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def _target_stat(parent_fd: int, basename: str):
    try:
        return os.stat(
            basename, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _validate_target_at(parent_fd: int, basename: str) -> None:
    info = _target_stat(parent_fd, basename)
    if info is not None and not stat.S_ISREG(info.st_mode):
        raise ValueError("BOM output must be a non-symlink regular file")


def _same_identity(left, right) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _atomic_write_bom_posix(path: str, data: bytes) -> None:
    basename = os.path.basename(path)
    parent_fd = _open_pinned_parent(path)
    temp_name = f".{basename}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
    temp_fd = None
    temp_identity = None
    committed = False
    try:
        _validate_target_at(parent_fd, basename)
        flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, "O_NOFOLLOW", 0))
        temp_fd = os.open(temp_name, flags, 0o600, dir_fd=parent_fd)
        os.fchmod(temp_fd, 0o600)
        temp_identity = os.fstat(temp_fd)
        if (not stat.S_ISREG(temp_identity.st_mode)
                or stat.S_IMODE(temp_identity.st_mode) != 0o600):
            raise OSError("BOM temporary permissions could not be secured")

        with os.fdopen(temp_fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

        named_temp = os.stat(
            temp_name, dir_fd=parent_fd, follow_symlinks=False)
        if (not stat.S_ISREG(named_temp.st_mode)
                or not _same_identity(temp_identity, named_temp)):
            raise OSError("BOM temporary file identity changed")
        _validate_target_at(parent_fd, basename)
        os.replace(
            temp_name,
            basename,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        committed = True
        final = os.stat(
            basename, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISREG(final.st_mode) or not _same_identity(temp_identity, final):
            raise OSError("BOM output identity changed after replacement")
        if stat.S_IMODE(final.st_mode) != 0o600:
            raise OSError("BOM output permissions could not be secured")
        os.fsync(parent_fd)
    finally:
        try:
            if temp_fd is not None:
                os.close(temp_fd)
        finally:
            try:
                if not committed and temp_identity is not None:
                    named_temp = _target_stat(parent_fd, temp_name)
                    if (named_temp is not None
                            and _same_identity(temp_identity, named_temp)):
                        os.unlink(temp_name, dir_fd=parent_fd)
            finally:
                os.close(parent_fd)


def _atomic_write_bom(path: str, bom: Mapping[str, object]) -> None:
    data = (json.dumps(bom, indent=2) + "\n").encode("utf-8")
    if os.name == "nt":
        _atomic_write_bom_windows(path, data)
    else:
        _atomic_write_bom_posix(path, data)


def atomic_write_json(path: str | Path, value: Mapping[str, object]) -> None:
    """Compatibility seam backed by the BOM-specific atomic writer."""
    _atomic_write_bom(os.path.abspath(os.fspath(path)), value)


def write_runtime_bom(output: str | Path) -> None:
    """Collect and atomically write the active runtime inventory."""
    bom = build_cyclonedx_bom(collect_runtime_components())
    path = os.path.abspath(os.fspath(output))
    atomic_write_json(path, bom)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the active runtime inventory")
    parser.add_argument("--output", required=True, help="explicit CycloneDX output path")
    args = parser.parse_args(argv)
    try:
        write_runtime_bom(args.output)
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(
            f"Runtime inventory generation failed ({type(exc).__name__})",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
