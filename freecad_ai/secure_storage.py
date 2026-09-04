"""Private, atomic persistence primitives for managed FreeCAD AI data."""

import json
import os
import re
import secrets
import stat
from collections.abc import Iterable

_SENSITIVE_KEY_PARTS = (
    "authorization", "api_key", "token", "password", "secret",
)


def _verify_mode(path: str, expected: int) -> None:
    if os.name != "nt" and stat.S_IMODE(os.lstat(path).st_mode) != expected:
        raise OSError("managed path permissions could not be secured")


def _validate_existing_ancestors(path: str) -> None:
    """Reject symlinked or non-directory components above *path*."""
    absolute = os.path.abspath(path)
    current = os.path.dirname(absolute)
    components = []
    while current and current != os.path.dirname(current):
        components.append(current)
        current = os.path.dirname(current)
    for component in reversed(components):
        if not os.path.lexists(component):
            continue
        info = os.lstat(component)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError(
                "managed path parent must be a non-symlink directory")


def ensure_private_dir(path: str) -> None:
    """Create or tighten a managed directory without following a symlink."""
    path = os.path.abspath(path)
    _validate_existing_ancestors(path)
    if os.path.lexists(path):
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("managed directory must be a non-symlink directory")
    else:
        missing = []
        current = path
        while not os.path.lexists(current):
            missing.append(current)
            current = os.path.dirname(current)
        for component in reversed(missing):
            os.mkdir(component, 0o700)
            if os.name != "nt":
                os.chmod(component, 0o700)
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("managed directory must be a non-symlink directory")
    if os.name != "nt":
        os.chmod(path, 0o700)
        _verify_mode(path, 0o700)


def _reject_unsafe_file(path: str) -> None:
    _validate_existing_ancestors(path)
    if not os.path.lexists(path):
        return
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError("managed file must be a non-symlink regular file")


def _fsync_directory(path: str) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    parent_fd = os.open(path, flags)
    try:
        try:
            os.fsync(parent_fd)
        except OSError as exc:
            raise OSError("parent fsync failed after durable file write") from exc
    finally:
        os.close(parent_fd)


def atomic_write_bytes(path: str, data: bytes, mode: int = 0o600) -> None:
    """Atomically replace a managed file using a private sibling temporary."""
    parent = os.path.dirname(os.path.abspath(path))
    ensure_private_dir(parent)
    _reject_unsafe_file(path)

    basename = os.path.basename(path)
    temp_path = os.path.join(
        parent, f".{basename}.tmp-{os.getpid()}-{secrets.token_hex(8)}")
    fd = None
    try:
        fd = os.open(
            temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        if os.name != "nt":
            os.fchmod(fd, mode)
            if stat.S_IMODE(os.fstat(fd).st_mode) != mode:
                raise OSError("temporary file permissions could not be secured")
        with os.fdopen(fd, "wb") as stream:
            fd = None
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

        _reject_unsafe_file(path)
        os.replace(temp_path, path)
        if os.name != "nt":
            _verify_mode(path, mode)
            _fsync_directory(parent)
    finally:
        if fd is not None:
            os.close(fd)
        if os.path.lexists(temp_path):
            os.unlink(temp_path)


def atomic_write_json(path: str, value: object) -> None:
    """Serialize JSON to a private atomic file."""
    data = (json.dumps(value, indent=2, default=str) + "\n").encode("utf-8")
    atomic_write_bytes(path, data, mode=0o600)


def harden_managed_paths(directories: Iterable[str],
                         files: Iterable[str]) -> list[str]:
    """Tighten known managed paths and return platform limitation warnings."""
    warnings = []
    if os.name == "nt":
        warnings.append(
            "Windows ACL enforcement is not provided by POSIX mode hardening.")
    for directory in directories:
        ensure_private_dir(directory)
    for path in files:
        if not os.path.lexists(path):
            continue
        _reject_unsafe_file(path)
        if os.name != "nt":
            os.chmod(path, 0o600)
            _verify_mode(path, 0o600)
    return warnings


def redact_sensitive(value: object,
                     exact_secrets: Iterable[str] = ()) -> object:
    """Recursively redact sensitive-key values and exact secret strings."""
    secrets_set = {item for item in exact_secrets if isinstance(item, str) and item}

    def redact(item, sensitive_key=False):
        if sensitive_key:
            return "[REDACTED]"
        if isinstance(item, str):
            for secret in secrets_set:
                item = item.replace(secret, "[REDACTED]")
            return item
        if isinstance(item, dict):
            return {
                key: redact(
                    child,
                    isinstance(key, str) and any(
                        part in key.casefold() for part in _SENSITIVE_KEY_PARTS),
                )
                for key, child in item.items()
            }
        if isinstance(item, list):
            return [redact(child) for child in item]
        if isinstance(item, tuple):
            return tuple(redact(child) for child in item)
        return item

    return redact(value)


def migrate_literal_secret(value: str, directory: str, stem: str) -> str:
    """Losslessly move a literal secret to a collision-free private file."""
    if not value or value.startswith(("file:", "cmd:")):
        return value

    ensure_private_dir(directory)
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]", "_", stem) or "secret"
    secret_bytes = value.encode("utf-8")
    index = 0
    while True:
        suffix = "" if index == 0 else f"-{index}"
        candidate = os.path.join(directory, safe_stem + suffix + ".secret")
        if os.path.lexists(candidate):
            try:
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                read_fd = os.open(candidate, flags)
                with os.fdopen(read_fd, "rb") as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                        raise ValueError("secret candidate is not a regular file")
                    if stream.read() == secret_bytes:
                        harden_managed_paths((), (candidate,))
                        return "file:" + os.path.realpath(candidate)
            except (OSError, ValueError):
                pass
            index += 1
            continue
        try:
            fd = os.open(
                candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            index += 1
            continue
        try:
            if os.name != "nt":
                os.fchmod(fd, 0o600)
                if stat.S_IMODE(os.fstat(fd).st_mode) != 0o600:
                    raise OSError("secret file permissions could not be secured")
            with os.fdopen(fd, "wb") as stream:
                fd = -1
                stream.write(secret_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            read_fd = os.open(candidate, flags)
            with os.fdopen(read_fd, "rb") as stream:
                if stream.read() != secret_bytes:
                    raise ValueError("secret migration read-back mismatch")
            _fsync_directory(directory)
        except Exception:
            if fd not in (-1, None):
                os.close(fd)
            if os.path.lexists(candidate):
                os.unlink(candidate)
            raise
        return "file:" + os.path.realpath(candidate)
