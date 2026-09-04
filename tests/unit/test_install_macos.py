"""Behavior and safety contracts for the macOS user-workbench installer.

Every subprocess receives a temporary HOME, TMPDIR, and fixture-owned ``uname``.
The tests must never inspect or mutate the operator's real FreeCAD profile.
"""

import hashlib
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "scripts" / "install_macos.sh"
REQUIRED = ("Init.py", "InitGui.py", "package.xml", "freecad_ai")


def _require_installer(path=INSTALLER):
    assert path.is_file(), (
        "missing production contract: scripts/install_macos.sh has not been "
        "implemented yet"
    )


def _write_executable(path, text):
    path.write_text(text, encoding="utf-8")
    path.chmod(0o700)


@pytest.fixture
def isolated_process(tmp_path):
    """Return a runner whose environment cannot resolve the real user profile."""
    home = tmp_path / "isolated home"
    temp = tmp_path / "temporary files"
    fake_bin = tmp_path / "fixture commands"
    home.mkdir()
    temp.mkdir()
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "uname",
        '#!/bin/sh\nprintf "%s\\n" "${FAKE_UNAME:-Darwin}"\n',
    )
    _write_executable(
        fake_bin / "id",
        '#!/bin/sh\n[ "${1:-}" = "-u" ] || exit 64\n'
        'printf "%s\\n" "${FAKE_EUID:-501}"\n',
    )
    environment = {
        "HOME": str(home),
        "PATH": f"{fake_bin}:/usr/bin:/bin:/usr/sbin:/sbin",
        "TMPDIR": str(temp),
        "FAKE_UNAME": "Darwin",
        "FAKE_EUID": "501",
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    def run(*arguments, script=INSTALLER, extra_env=None):
        _require_installer(script)
        env = dict(environment)
        if extra_env:
            env.update({key: str(value) for key, value in extra_env.items()})
        return subprocess.run(
            ["/bin/bash", str(script), *map(str, arguments)],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
            cwd=ROOT,
        )

    return {
        "run": run,
        "home": home,
        "tmp": temp,
        "fake_bin": fake_bin,
        "env": environment,
    }


def _default_freecad_root(home):
    return home / "Library" / "Application Support" / "FreeCAD"


def _destination(mod_dir):
    return mod_dir / "freecad-ai"


def _minimal_source(tmp_path, missing=None):
    """Copy the future installer into a tiny physical checkout fixture."""
    _require_installer()
    source = tmp_path / "source checkout with spaces"
    scripts = source / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(INSTALLER, scripts / INSTALLER.name)
    for name in REQUIRED:
        if name == missing:
            continue
        path = source / name
        if name == "freecad_ai":
            path.mkdir()
            (path / "__init__.py").write_text("", encoding="utf-8")
        else:
            path.write_text(f"fixture {name}\n", encoding="utf-8")
    return source, scripts / INSTALLER.name


def _tree_snapshot(root):
    """Capture type, link target/content hash, and mode without following links."""
    if not root.exists():
        return ()
    records = []
    for directory, names, files in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in sorted(names + files):
            path = base / name
            relative = str(path.relative_to(root))
            info = path.lstat()
            mode = stat.S_IMODE(info.st_mode)
            if path.is_symlink():
                payload = f"link:{os.readlink(path)}"
            elif path.is_file():
                payload = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                payload = "directory"
            records.append((relative, mode, payload))
    return tuple(sorted(records))


def _assert_success(result):
    assert result.returncode == 0, result.stderr or result.stdout


def _assert_failure(result):
    assert result.returncode != 0, result.stdout
    assert (result.stderr + result.stdout).strip(), "failure must be diagnostic"


def test_help_uses_apple_bash_and_documents_the_complete_interface(
        isolated_process):
    result = isolated_process["run"]("--help")

    _assert_success(result)
    for option in ("--copy", "--dry-run", "--check", "--replace", "--mod-dir"):
        assert option in result.stdout


def test_script_parses_with_bash_3_2_compatible_entrypoint():
    _require_installer()
    result = subprocess.run(
        ["/bin/bash", "-n", str(INSTALLER)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
    )

    assert result.returncode == 0, result.stderr


def test_non_darwin_gate_precedes_every_filesystem_mutation(isolated_process):
    home = isolated_process["home"]
    before = _tree_snapshot(home)
    target = home / "must not be created" / "Mod"

    result = isolated_process["run"](
        "--mod-dir", target, extra_env={"FAKE_UNAME": "Linux"})

    _assert_failure(result)
    assert "macos" in (result.stderr + result.stdout).lower()
    assert _tree_snapshot(home) == before
    assert not target.exists()


def test_effective_root_is_refused_early_without_target_mutation(
        isolated_process):
    """A user-workbench installer must not turn root into installation scope."""
    home = isolated_process["home"]
    target = home / "root must not create this" / "Mod"
    before = _tree_snapshot(home)

    result = isolated_process["run"](
        "--mod-dir", target, extra_env={"FAKE_EUID": "0"})

    _assert_failure(result)
    assert "root" in (result.stderr + result.stdout).lower()
    assert _tree_snapshot(home) == before
    assert not target.exists()


def test_root_gate_is_statically_before_mutating_commands():
    """Keep the behavioral fake-id test tied to an early production check."""
    _require_installer()
    text = INSTALLER.read_text(encoding="utf-8")
    root_check = re.search(r"\bid\s+-u\b", text)

    assert root_check is not None, "installer must obtain effective uid"
    mutation_offsets = [
        text.find(token) for token in (
            'mkdir -p "$MOD_DIR"', "mktemp -d", 'mv "$DESTINATION"',
            'ln -s "$SOURCE_DIR" "$DESTINATION"',
        ) if text.find(token) >= 0
    ]
    assert mutation_offsets
    assert root_check.start() < min(mutation_offsets), (
        "effective-root refusal must precede every target mutation")


@pytest.mark.parametrize("missing", REQUIRED)
def test_source_requires_every_workbench_entry_before_target_mutation(
        isolated_process, tmp_path, missing):
    source, script = _minimal_source(tmp_path, missing=missing)
    target = isolated_process["home"] / "new target" / "Mod"

    result = isolated_process["run"](
        "--mod-dir", target, script=script)

    _assert_failure(result)
    assert missing in (result.stderr + result.stdout)
    assert not target.exists()
    assert source.exists()


def test_explicit_absolute_mod_dir_overrides_ambiguous_discovery(
        isolated_process):
    freecad = _default_freecad_root(isolated_process["home"])
    (freecad / "v1.1" / "Mod").mkdir(parents=True)
    (freecad / "v1.2" / "Mod").mkdir(parents=True)
    explicit = isolated_process["home"] / "chosen Mod with spaces"

    result = isolated_process["run"]("--mod-dir", explicit)

    _assert_success(result)
    installed = _destination(explicit)
    assert installed.is_symlink()
    assert installed.resolve() == ROOT.resolve()
    assert not (freecad / "v1.1" / "Mod" / "freecad-ai").exists()
    assert not (freecad / "v1.2" / "Mod" / "freecad-ai").exists()


def test_single_existing_versioned_mod_directory_is_selected(isolated_process):
    freecad = _default_freecad_root(isolated_process["home"])
    selected = freecad / "v1.1" / "Mod"
    selected.mkdir(parents=True)

    result = isolated_process["run"]()

    _assert_success(result)
    assert _destination(selected).is_symlink()
    assert _destination(selected).resolve() == ROOT.resolve()
    assert not _destination(freecad / "Mod").exists()


def test_multiple_versioned_mod_directories_fail_closed_without_mutation(
        isolated_process):
    freecad = _default_freecad_root(isolated_process["home"])
    (freecad / "v1.1" / "Mod").mkdir(parents=True)
    (freecad / "v1.2" / "Mod").mkdir(parents=True)
    before = _tree_snapshot(isolated_process["home"])

    result = isolated_process["run"]()

    _assert_failure(result)
    assert "--mod-dir" in (result.stderr + result.stdout)
    assert _tree_snapshot(isolated_process["home"]) == before


def test_no_versioned_directory_uses_generic_mod_path(isolated_process):
    generic = _default_freecad_root(isolated_process["home"]) / "Mod"

    result = isolated_process["run"]()

    _assert_success(result)
    assert _destination(generic).is_symlink()
    assert _destination(generic).resolve() == ROOT.resolve()


@pytest.mark.parametrize("value", ["relative/Mod", ".", "/"])
def test_unsafe_explicit_mod_directory_is_rejected_before_mutation(
        isolated_process, value):
    before = _tree_snapshot(isolated_process["home"])

    result = isolated_process["run"]("--mod-dir", value)

    _assert_failure(result)
    assert _tree_snapshot(isolated_process["home"]) == before


@pytest.mark.parametrize(
    "prefix",
    [
        "/Applications", "/Library", "/System", "/bin", "/etc",
        "/private/etc", "/sbin", "/usr",
    ],
)
def test_system_prefixes_are_rejected_even_for_dry_run(
        isolated_process, prefix):
    """A preview must not normalize a system location into accepted scope."""
    target = Path(prefix) / "FreeCAD-AI-installer-contract-never-write" / "Mod"
    destination = target / "freecad-ai"
    assert not destination.exists(), "test sentinel unexpectedly exists"

    result = isolated_process["run"](
        "--dry-run", "--mod-dir", target)

    _assert_failure(result)
    assert "system" in (result.stderr + result.stdout).lower()
    assert not destination.exists(), "dry-run mutated a system destination"


@pytest.mark.parametrize(
    "prefix",
    [
        "/Applications", "/Library", "/System", "/bin", "/etc",
        "/private/etc", "/sbin", "/usr",
    ],
)
def test_double_slash_system_prefixes_are_rejected_even_for_dry_run(
        isolated_process, prefix):
    """POSIX // handling must not bypass protected-prefix rejection."""
    target = f"/{prefix}/FreeCAD-AI-installer-contract-never-write/Mod"
    destination = Path(target) / "freecad-ai"
    assert not destination.exists(), "test sentinel unexpectedly exists"

    result = isolated_process["run"](
        "--dry-run", "--mod-dir", target)

    _assert_failure(result)
    assert "system" in (result.stderr + result.stdout).lower()
    assert not destination.exists(), "dry-run mutated a system destination"


@pytest.mark.parametrize("leading_root", ["/", "//"])
def test_canonicalization_preserves_a_single_leading_root_separator(
        isolated_process, leading_root):
    """Missing root-level paths must not become a distinct // namespace."""
    suffix = "FreeCAD-AI-installer-contract-never-write-root/Mod"
    target = f"{leading_root}{suffix}"
    assert not Path(target).exists(), "test sentinel unexpectedly exists"

    result = isolated_process["run"](
        "--dry-run", "--mod-dir", target)

    _assert_success(result)
    assert f"Destination: /{suffix}/freecad-ai" in result.stdout
    assert "Destination: //" not in result.stdout
    assert not Path(target).exists(), "dry-run mutated the destination"


def test_symlink_parent_cannot_bypass_canonical_system_prefix_rejection(
        isolated_process):
    """Lexically private paths remain unsafe when their parent resolves system-wide."""
    alias = isolated_process["home"] / "apparently user owned"
    alias.symlink_to("/private", target_is_directory=True)
    target = alias / "etc" / "FreeCAD-AI-installer-contract" / "Mod"
    real_target = Path(
        "/private/etc/FreeCAD-AI-installer-contract/Mod/freecad-ai")
    assert not real_target.exists(), "test sentinel unexpectedly exists"
    before = _tree_snapshot(isolated_process["home"])

    result = isolated_process["run"](
        "--dry-run", "--mod-dir", target)

    _assert_failure(result)
    assert _tree_snapshot(isolated_process["home"]) == before
    assert not real_target.exists()


def test_default_install_publishes_a_link_via_clean_sibling_staging(
        isolated_process):
    mod_dir = isolated_process["home"] / "Library with spaces" / "Mod"

    result = isolated_process["run"]("--mod-dir", mod_dir)

    _assert_success(result)
    installed = _destination(mod_dir)
    assert installed.is_symlink()
    assert installed.resolve() == ROOT.resolve()
    assert not list(mod_dir.glob(".*stage*"))


@pytest.mark.parametrize("mode", ["link", "copy"])
def test_installer_owned_lock_is_removed_after_success(
        isolated_process, mode):
    mod_dir = isolated_process["home"] / f"successful {mode}" / "Mod"
    arguments = ["--mod-dir", mod_dir]
    if mode == "copy":
        arguments.insert(0, "--copy")

    result = isolated_process["run"](*arguments)

    _assert_success(result)
    assert not (mod_dir / ".freecad-ai.install.lock").exists()


def test_copy_install_is_structurally_complete_and_excludes_development_data(
        isolated_process):
    mod_dir = isolated_process["home"] / "copy target" / "Mod"

    result = isolated_process["run"]("--copy", "--mod-dir", mod_dir)

    _assert_success(result)
    installed = _destination(mod_dir)
    assert installed.is_dir() and not installed.is_symlink()
    for name in REQUIRED:
        assert (installed / name).exists(), name
    for excluded in (
            ".git", ".venv", "tests", "docs", "build", "__pycache__",
            ".pytest_cache", ".coverage", ".DS_Store"):
        assert not (installed / excluded).exists(), excluded
    assert not list(mod_dir.glob(".*stage*"))


def test_correct_link_is_an_idempotent_noop_without_backup(isolated_process):
    mod_dir = isolated_process["home"] / "link idempotence" / "Mod"
    mod_dir.mkdir(parents=True)
    installed = _destination(mod_dir)
    installed.symlink_to(ROOT, target_is_directory=True)
    before = _tree_snapshot(mod_dir)

    result = isolated_process["run"]("--mod-dir", mod_dir)

    _assert_success(result)
    assert _tree_snapshot(mod_dir) == before
    assert not list(mod_dir.glob("freecad-ai.backup.*"))


def test_preexisting_per_target_install_lock_fails_unchanged(
        isolated_process):
    """A concurrent-looking run must not share one target transaction."""
    mod_dir = isolated_process["home"] / "locked target" / "Mod"
    mod_dir.mkdir(parents=True)
    lock = mod_dir / ".freecad-ai.install.lock"
    lock.mkdir()
    (lock / "owner").write_text("other installer", encoding="utf-8")
    before = _tree_snapshot(mod_dir)

    result = isolated_process["run"]("--mod-dir", mod_dir)

    _assert_failure(result)
    assert "lock" in (result.stderr + result.stdout).lower()
    assert _tree_snapshot(mod_dir) == before
    assert not _destination(mod_dir).exists()


def test_structurally_valid_copy_is_idempotent_only_in_copy_mode(
        isolated_process):
    mod_dir = isolated_process["home"] / "copy idempotence" / "Mod"
    installed = _destination(mod_dir)
    installed.mkdir(parents=True)
    for name in REQUIRED:
        path = installed / name
        path.mkdir() if name == "freecad_ai" else path.write_text(
            name, encoding="utf-8")
    before = _tree_snapshot(mod_dir)

    copy_result = isolated_process["run"]("--copy", "--mod-dir", mod_dir)
    link_result = isolated_process["run"]("--mod-dir", mod_dir)

    _assert_success(copy_result)
    _assert_failure(link_result)
    assert _tree_snapshot(mod_dir) == before
    assert not list(mod_dir.glob("freecad-ai.backup.*"))


@pytest.mark.parametrize("kind", ["file", "directory", "wrong-link", "broken-link"])
def test_every_foreign_or_broken_destination_conflicts_without_replace(
        isolated_process, tmp_path, kind):
    mod_dir = isolated_process["home"] / f"conflict {kind}" / "Mod"
    mod_dir.mkdir(parents=True)
    installed = _destination(mod_dir)
    if kind == "file":
        installed.write_text("keep me", encoding="utf-8")
    elif kind == "directory":
        installed.mkdir()
        (installed / "foreign.txt").write_text("keep me", encoding="utf-8")
    elif kind == "wrong-link":
        foreign = tmp_path / "foreign source"
        foreign.mkdir()
        installed.symlink_to(foreign, target_is_directory=True)
    else:
        installed.symlink_to(tmp_path / "missing source", target_is_directory=True)
    before = _tree_snapshot(mod_dir)

    result = isolated_process["run"]("--mod-dir", mod_dir)

    _assert_failure(result)
    assert _tree_snapshot(mod_dir) == before
    assert not list(mod_dir.glob("freecad-ai.backup.*"))


def test_replace_moves_conflict_to_unique_backups_before_publication(
        isolated_process):
    mod_dir = isolated_process["home"] / "replace target" / "Mod"
    mod_dir.mkdir(parents=True)
    installed = _destination(mod_dir)
    installed.write_text("first old payload", encoding="utf-8")

    first = isolated_process["run"]("--replace", "--mod-dir", mod_dir)
    _assert_success(first)
    assert installed.is_symlink() and installed.resolve() == ROOT.resolve()
    first_backups = list(mod_dir.glob("freecad-ai.backup.*"))
    assert len(first_backups) == 1
    assert first_backups[0].read_text(encoding="utf-8") == "first old payload"

    installed.unlink()
    installed.write_text("second old payload", encoding="utf-8")
    second = isolated_process["run"]("--replace", "--mod-dir", mod_dir)

    _assert_success(second)
    backups = sorted(mod_dir.glob("freecad-ai.backup.*"))
    assert len(backups) == 2
    assert {item.read_text(encoding="utf-8") for item in backups} == {
        "first old payload", "second old payload"}


def test_publication_failure_restores_exact_old_destination_and_cleans_stage(
        isolated_process):
    mod_dir = isolated_process["home"] / "rollback target" / "Mod"
    mod_dir.mkdir(parents=True)
    installed = _destination(mod_dir)
    installed.mkdir()
    (installed / "identity.txt").write_text("original", encoding="utf-8")
    before = _tree_snapshot(installed)

    fake_ln = isolated_process["fake_bin"] / "ln"
    _write_executable(
        fake_ln,
        """#!/bin/sh
last=''
for item in "$@"; do last=$item; done
if [ "$last" = "$FAIL_PUBLISH_DEST" ] && [ ! -e "$FAIL_ONCE_MARKER" ]; then
    : > "$FAIL_ONCE_MARKER"
    exit 73
fi
exec /bin/ln "$@"
""",
    )
    marker = isolated_process["tmp"] / "publish failed once"
    result = isolated_process["run"](
        "--replace", "--mod-dir", mod_dir,
        extra_env={
            "FAIL_PUBLISH_DEST": installed,
            "FAIL_ONCE_MARKER": marker,
        },
    )

    _assert_failure(result)
    assert marker.exists(), "failure injection did not reach publication"
    assert installed.is_dir() and not installed.is_symlink()
    assert _tree_snapshot(installed) == before
    assert not list(mod_dir.glob("freecad-ai.backup.*"))
    assert not list(mod_dir.glob(".*stage*"))
    assert not (mod_dir / ".freecad-ai.install.lock").exists()


def test_fresh_link_publication_failure_cleans_transaction_without_backup(
        isolated_process):
    """Cleanup of a failed fresh install must not depend on backup state."""
    mod_dir = isolated_process["home"] / "fresh link failure" / "Mod"
    installed = _destination(mod_dir)
    marker = isolated_process["tmp"] / "fresh link publish failed"
    fake_ln = isolated_process["fake_bin"] / "ln"
    _write_executable(
        fake_ln,
        """#!/bin/sh
last=''
for item in "$@"; do last=$item; done
if [ "$last" = "$FAIL_FRESH_DEST" ]; then
    : > "$FAIL_FRESH_MARKER"
    exit 73
fi
exec /bin/ln "$@"
""",
    )

    result = isolated_process["run"](
        "--mod-dir", mod_dir,
        extra_env={
            "FAIL_FRESH_DEST": installed,
            "FAIL_FRESH_MARKER": marker,
        },
    )

    _assert_failure(result)
    assert marker.exists(), "failure injection did not reach direct publication"
    assert not installed.exists() and not installed.is_symlink()
    assert not list(mod_dir.glob("freecad-ai.backup.*"))
    assert not list(mod_dir.glob(".*stage*"))
    assert not (mod_dir / ".freecad-ai.install.lock").exists()


def test_reappearing_destination_directory_never_becomes_publish_parent(
        isolated_process):
    """An attacker/racing process must not make mv nest the staged payload."""
    mod_dir = isolated_process["home"] / "reappearing destination" / "Mod"
    mod_dir.mkdir(parents=True)
    installed = _destination(mod_dir)
    installed.write_text("original payload", encoding="utf-8")

    fake_ln = isolated_process["fake_bin"] / "ln"
    _write_executable(
        fake_ln,
        """#!/bin/sh
last=''
for item in "$@"; do last=$item; done
if [ "$last" = "$RACE_DEST" ]; then
    /bin/mkdir "$RACE_DEST" || exit $?
    printf '%s\n' 'racing object' > "$RACE_DEST/intruder.txt"
fi
exec /bin/ln "$@"
""",
    )

    result = isolated_process["run"](
        "--replace", "--mod-dir", mod_dir,
        extra_env={"RACE_DEST": installed},
    )

    _assert_failure(result)
    assert not (installed / "freecad-ai").exists(), (
        "publication nested the staged workbench into a raced directory")
    assert (installed / "intruder.txt").read_text(
        encoding="utf-8") == "racing object\n"
    backups = list(mod_dir.glob("freecad-ai.backup.*"))
    restored = installed.is_file() and installed.read_text(
        encoding="utf-8") == "original payload"
    preserved = len(backups) == 1 and backups[0].read_text(
        encoding="utf-8") == "original payload"
    assert restored or preserved, "the pre-race installation was lost"
    assert not list(mod_dir.glob(".*stage*"))
    assert not (mod_dir / ".freecad-ai.install.lock").exists()


def test_correct_source_link_race_never_leaves_nested_link_and_preserves_backup(
        isolated_process, tmp_path):
    """A raced correct link is foreign state, not a publication success."""
    source, script = _minimal_source(tmp_path)
    mod_dir = isolated_process["home"] / "correct link race" / "Mod"
    mod_dir.mkdir(parents=True)
    installed = _destination(mod_dir)
    installed.write_text("original payload", encoding="utf-8")
    nested = source / source.name
    marker = isolated_process["tmp"] / "correct link race injected"
    fake_ln = isolated_process["fake_bin"] / "ln"
    _write_executable(
        fake_ln,
        """#!/bin/sh
last=''
for item in "$@"; do last=$item; done
if [ "$last" = "$RACE_LINK_DEST" ]; then
    : > "$RACE_LINK_MARKER"
    /bin/ln -s "$RACE_LINK_SOURCE" "$RACE_LINK_DEST" || exit $?
fi
exec /bin/ln "$@"
""",
    )

    result = isolated_process["run"](
        "--replace", "--mod-dir", mod_dir, script=script,
        extra_env={
            "RACE_LINK_DEST": installed,
            "RACE_LINK_SOURCE": source,
            "RACE_LINK_MARKER": marker,
        },
    )

    _assert_failure(result)
    assert marker.exists(), "race injection did not reach direct publication"
    assert installed.is_symlink() and installed.resolve() == source.resolve()
    assert not nested.exists() and not nested.is_symlink(), (
        "ln nested a source-basename link through the raced destination")
    backups = list(mod_dir.glob("freecad-ai.backup.*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "original payload"
    assert not list(mod_dir.glob(".*stage*"))
    assert not (mod_dir / ".freecad-ai.install.lock").exists()


def test_copy_claim_race_with_valid_foreign_workbench_never_false_succeeds(
        isolated_process):
    """Copy publication must exclusively claim DEST before copying contents."""
    mod_dir = isolated_process["home"] / "copy claim race" / "Mod"
    mod_dir.mkdir(parents=True)
    installed = _destination(mod_dir)
    marker = isolated_process["tmp"] / "copy race injected"
    fake_mkdir = isolated_process["fake_bin"] / "mkdir"
    _write_executable(
        fake_mkdir,
        """#!/bin/sh
last=''
for item in "$@"; do last=$item; done
if [ "$last" = "$COPY_RACE_DEST" ] && [ ! -e "$COPY_RACE_MARKER" ]; then
    : > "$COPY_RACE_MARKER"
    /bin/mkdir "$COPY_RACE_DEST" || exit $?
    /usr/bin/touch "$COPY_RACE_DEST/Init.py" \
        "$COPY_RACE_DEST/InitGui.py" "$COPY_RACE_DEST/package.xml"
    /bin/mkdir "$COPY_RACE_DEST/freecad_ai" || exit $?
    printf '%s\n' 'foreign' > "$COPY_RACE_DEST/foreign-owner.txt"
fi
exec /bin/mkdir "$@"
""",
    )

    result = isolated_process["run"](
        "--copy", "--mod-dir", mod_dir,
        extra_env={
            "COPY_RACE_DEST": installed,
            "COPY_RACE_MARKER": marker,
        },
    )

    _assert_failure(result)
    assert marker.exists(), "copy race did not reach destination claim"
    assert (installed / "foreign-owner.txt").read_text(
        encoding="utf-8") == "foreign\n"
    assert not (installed / "freecad-ai").exists()
    assert not list(mod_dir.glob(".*stage*"))
    assert not (mod_dir / ".freecad-ai.install.lock").exists()


def test_fresh_copy_second_rsync_failure_leaves_no_partial_transaction(
        isolated_process, tmp_path):
    """A failed publish copy must remove its exclusively claimed destination."""
    _source, script = _minimal_source(tmp_path)
    mod_dir = isolated_process["home"] / "fresh copy failure" / "Mod"
    installed = _destination(mod_dir)
    marker = isolated_process["tmp"] / "publication directory made read only"
    blocker = isolated_process["tmp"] / "not a publication directory"
    blocker.write_text("filesystem race blocker\n", encoding="utf-8")
    fake_mkdir = isolated_process["fake_bin"] / "mkdir"
    _write_executable(
        fake_mkdir,
        """#!/bin/sh
last=''
for item in "$@"; do last=$item; done
if [ "$last" = "$FAIL_COPY_DEST" ]; then
    /bin/mkdir "$@" || exit $?
    /bin/rmdir "$FAIL_COPY_DEST" || exit $?
    /bin/ln -s "$FAIL_COPY_BLOCKER" "$FAIL_COPY_DEST" || exit $?
    : > "$FAIL_COPY_MARKER"
    exit 0
fi
exec /bin/mkdir "$@"
""",
    )

    result = isolated_process["run"](
        "--copy", "--mod-dir", mod_dir, script=script,
        extra_env={
            "FAIL_COPY_DEST": installed,
            "FAIL_COPY_MARKER": marker,
            "FAIL_COPY_BLOCKER": blocker,
        },
    )

    _assert_failure(result)
    assert marker.exists(), "staged copy did not reach final destination claim"
    assert not installed.exists() and not installed.is_symlink(), (
        "failed publication left its invalidated destination behind")
    assert not list(mod_dir.glob("freecad-ai.backup.*"))
    assert not list(mod_dir.glob(".*stage*"))
    assert not (mod_dir / ".freecad-ai.install.lock").exists()


def test_term_during_copy_publication_restores_backup_without_partial_state(
        isolated_process, tmp_path):
    """TERM observed during the second rsync must roll replacement back."""
    source, script = _minimal_source(tmp_path)
    with (source / "zz-copy-window.bin").open("wb") as payload:
        chunk = b"copy publication signal window\n" * 4096
        for _ in range(256):
            payload.write(chunk)
    (source / "zzz-copy-complete.marker").write_text(
        "publication complete\n", encoding="utf-8")
    mod_dir = isolated_process["home"] / "copy signal rollback" / "Mod"
    mod_dir.mkdir(parents=True)
    installed = _destination(mod_dir)
    installed.mkdir()
    (installed / "identity.txt").write_text("original", encoding="utf-8")
    before = _tree_snapshot(installed)
    marker = isolated_process["tmp"] / "copy term injected"
    fake_mkdir = isolated_process["fake_bin"] / "mkdir"
    _write_executable(
        fake_mkdir,
        """#!/bin/sh
last=''
for item in "$@"; do last=$item; done
if [ "$last" = "$TERM_COPY_DEST" ]; then
    /bin/mkdir "$@" || exit $?
    installer_pid=$PPID
    (
        attempts=0
        while [ "$attempts" -lt 500 ] && kill -0 "$installer_pid" 2>/dev/null; do
            if [ -e "$TERM_COPY_DEST/Init.py" ] && \
               [ ! -e "$TERM_COPY_DEST/zzz-copy-complete.marker" ]; then
                : > "$TERM_COPY_MARKER"
                kill -TERM "$installer_pid"
                exit 0
            fi
            attempts=$((attempts + 1))
            /bin/sleep 0.01
        done
        exit 1
    ) </dev/null >/dev/null 2>&1 &
    exit 0
fi
exec /bin/mkdir "$@"
""",
    )

    result = isolated_process["run"](
        "--copy", "--replace", "--mod-dir", mod_dir, script=script,
        extra_env={
            "TERM_COPY_DEST": installed,
            "TERM_COPY_MARKER": marker,
        },
    )

    assert result.returncode != 0
    assert marker.exists(), "TERM was not injected during copy publication"
    assert installed.is_dir() and not installed.is_symlink()
    assert _tree_snapshot(installed) == before
    assert not list(mod_dir.glob("freecad-ai.backup.*"))
    assert not list(mod_dir.glob(".*stage*"))
    assert not (mod_dir / ".freecad-ai.install.lock").exists()


def test_term_after_backup_restores_old_destination_and_cleans_transaction(
        isolated_process):
    """Signal cleanup must include rollback once replacement has begun."""
    mod_dir = isolated_process["home"] / "signal rollback" / "Mod"
    mod_dir.mkdir(parents=True)
    installed = _destination(mod_dir)
    installed.mkdir()
    (installed / "identity.txt").write_text("original", encoding="utf-8")
    before = _tree_snapshot(installed)

    fake_ln = isolated_process["fake_bin"] / "ln"
    _write_executable(
        fake_ln,
        """#!/bin/sh
last=''
for item in "$@"; do last=$item; done
if [ "$last" = "$TERM_PUBLISH_DEST" ] && [ ! -e "$TERM_ONCE_MARKER" ]; then
    : > "$TERM_ONCE_MARKER"
    kill -TERM "$PPID"
    sleep 1
    exit 143
fi
exec /bin/ln "$@"
""",
    )
    marker = isolated_process["tmp"] / "term injected"

    result = isolated_process["run"](
        "--replace", "--mod-dir", mod_dir,
        extra_env={
            "TERM_PUBLISH_DEST": installed,
            "TERM_ONCE_MARKER": marker,
        },
    )

    assert result.returncode != 0
    assert marker.exists(), "TERM injection did not reach publication"
    assert installed.is_dir() and not installed.is_symlink()
    assert _tree_snapshot(installed) == before
    assert not list(mod_dir.glob("freecad-ai.backup.*"))
    assert not list(mod_dir.glob(".*stage*"))
    assert not (mod_dir / ".freecad-ai.install.lock").exists()


def test_dry_run_replace_reports_plan_without_creating_or_moving_anything(
        isolated_process):
    mod_dir = isolated_process["home"] / "dry run target" / "Mod"
    mod_dir.mkdir(parents=True)
    installed = _destination(mod_dir)
    installed.write_text("untouched", encoding="utf-8")
    before = _tree_snapshot(isolated_process["home"])

    result = isolated_process["run"](
        "--dry-run", "--replace", "--mod-dir", mod_dir)

    _assert_success(result)
    assert "replace" in result.stdout.lower()
    assert str(installed) in result.stdout
    assert _tree_snapshot(isolated_process["home"]) == before


def test_dry_run_absent_generic_target_does_not_create_parent_directories(
        isolated_process):
    home = isolated_process["home"]
    before = _tree_snapshot(home)

    result = isolated_process["run"]("--dry-run")

    _assert_success(result)
    assert "freecad-ai" in result.stdout
    assert _tree_snapshot(home) == before
    assert not _default_freecad_root(home).exists()


def test_check_accepts_current_link_and_valid_copy_without_mutation(
        isolated_process):
    link_mod = isolated_process["home"] / "check link" / "Mod"
    copy_mod = isolated_process["home"] / "check copy" / "Mod"
    link_mod.mkdir(parents=True)
    copy_mod.mkdir(parents=True)
    _destination(link_mod).symlink_to(ROOT, target_is_directory=True)
    copied = _destination(copy_mod)
    copied.mkdir()
    for name in REQUIRED:
        path = copied / name
        path.mkdir() if name == "freecad_ai" else path.write_text(
            name, encoding="utf-8")
    before = _tree_snapshot(isolated_process["home"])

    link_result = isolated_process["run"]("--check", "--mod-dir", link_mod)
    copy_result = isolated_process["run"]("--check", "--mod-dir", copy_mod)

    _assert_success(link_result)
    _assert_success(copy_result)
    assert _tree_snapshot(isolated_process["home"]) == before


@pytest.mark.parametrize("kind", ["absent", "broken-link", "foreign-file"])
def test_check_rejects_invalid_state_without_mutation(
        isolated_process, tmp_path, kind):
    mod_dir = isolated_process["home"] / f"check invalid {kind}" / "Mod"
    mod_dir.mkdir(parents=True)
    installed = _destination(mod_dir)
    if kind == "broken-link":
        installed.symlink_to(tmp_path / "not there")
    elif kind == "foreign-file":
        installed.write_text("foreign", encoding="utf-8")
    before = _tree_snapshot(isolated_process["home"])

    result = isolated_process["run"]("--check", "--mod-dir", mod_dir)

    _assert_failure(result)
    assert _tree_snapshot(isolated_process["home"]) == before


@pytest.mark.parametrize(
    "arguments",
    [
        ("--check", "--copy"),
        ("--check", "--replace"),
        ("--check", "--dry-run"),
        ("--mod-dir",),
        ("--unknown-option",),
    ],
)
def test_invalid_option_combinations_fail_before_mutation(
        isolated_process, arguments):
    before = _tree_snapshot(isolated_process["home"])

    result = isolated_process["run"](*arguments)

    _assert_failure(result)
    assert _tree_snapshot(isolated_process["home"]) == before


def test_paths_with_spaces_survive_copy_replace_and_backup(isolated_process):
    mod_dir = isolated_process["home"] / "FreeCAD Profile With Spaces" / "Mod"
    mod_dir.mkdir(parents=True)
    installed = _destination(mod_dir)
    installed.write_text("old content with spaces", encoding="utf-8")

    result = isolated_process["run"](
        "--copy", "--replace", "--mod-dir", mod_dir)

    _assert_success(result)
    assert installed.is_dir() and not installed.is_symlink()
    backups = list(mod_dir.glob("freecad-ai.backup.*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "old content with spaces"


def test_script_contains_no_forbidden_privilege_network_process_or_secret_ops():
    _require_installer()
    text = INSTALLER.read_text(encoding="utf-8")
    forbidden = {
        "dynamic evaluation": r"\beval\b",
        "privilege escalation": r"\bsudo\b",
        "network client": r"\b(?:curl|wget|ftp)\b",
        "package manager": r"\b(?:brew|port|pip|npm)\b",
        "service/process control": r"\b(?:launchctl|reboot|shutdown|pkill|killall)\b",
        "application launch": r"(?:\bopen\s+-a\b|Contents/MacOS/FreeCAD)",
        "provider or credential mutation": (
            r"(?:api[_ -]?key|credential|config\.json|mcp_server\.token)"),
    }

    findings = [label for label, pattern in forbidden.items()
                if re.search(pattern, text, flags=re.IGNORECASE)]
    assert not findings, f"installer contains prohibited operations: {findings}"


def test_script_avoids_bash_4_and_gnu_only_constructs():
    _require_installer()
    text = INSTALLER.read_text(encoding="utf-8")
    forbidden = {
        "associative arrays": r"\bdeclare\s+-A\b",
        "mapfile/readarray": r"\b(?:mapfile|readarray)\b",
        "globstar": r"\bglobstar\b",
        "case conversion expansion": r"\$\{[^}\n]+(?:,,|\^\^)[^}\n]*\}",
        "GNU realpath": r"\brealpath\b",
        "GNU readlink flags": r"\breadlink\s+(?:-[efm]|--canonicalize)",
    }

    findings = [label for label, pattern in forbidden.items()
                if re.search(pattern, text)]
    assert not findings, f"not Apple Bash 3.2/macOS compatible: {findings}"
