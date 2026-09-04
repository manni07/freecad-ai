#!/bin/bash

set -u

PROGRAM_NAME=$(basename "$0")
MODE="link"
DRY_RUN=0
CHECK_ONLY=0
REPLACE=0
EXPLICIT_MOD_DIR=""
SOURCE_DIR=""
MOD_DIR=""
DESTINATION=""
STAGE_DIR=""
BACKUP_PATH=""
LOCK_DIR=""
LOCK_HELD=0
PUBLISH_COMPLETE=0
OWNED_DESTINATION=0

usage() {
    printf '%s\n' "Usage: $PROGRAM_NAME [OPTIONS]"
    printf '%s\n' ""
    printf '%s\n' "Install this checkout as a FreeCAD user workbench on macOS."
    printf '%s\n' ""
    printf '%s\n' "Options:"
    printf '%s\n' "  --copy          Install a standalone copy instead of a symbolic link"
    printf '%s\n' "  --dry-run       Validate and report the action without changing files"
    printf '%s\n' "  --check         Check an existing installation without changing files"
    printf '%s\n' "  --replace       Back up and replace a conflicting destination"
    printf '%s\n' "  --mod-dir PATH  Use this absolute FreeCAD Mod directory"
    printf '%s\n' "  --help          Show this help"
}

fail() {
    printf 'Error: %s\n' "$1" >&2
    exit 1
}

cleanup_stage() {
    if [ -n "$STAGE_DIR" ] && [ -n "$MOD_DIR" ]; then
        case "$STAGE_DIR" in
            "$MOD_DIR"/.freecad-ai.stage.*)
                if [ -d "$STAGE_DIR" ]; then
                    rm -rf "$STAGE_DIR"
                fi
                ;;
        esac
    fi
}

cleanup_transaction() {
    if [ "$PUBLISH_COMPLETE" -eq 0 ] && \
       [ "$OWNED_DESTINATION" -eq 1 ] && \
       [ "$DESTINATION" = "$MOD_DIR/freecad-ai" ]; then
        if [ -L "$DESTINATION" ] || [ -f "$DESTINATION" ]; then
            rm -f "$DESTINATION"
        elif [ -d "$DESTINATION" ]; then
            rm -rf "$DESTINATION"
        fi
        OWNED_DESTINATION=0
    fi
    if [ -n "$BACKUP_PATH" ] && \
       { [ -e "$BACKUP_PATH" ] || [ -L "$BACKUP_PATH" ]; } && \
       [ "$PUBLISH_COMPLETE" -eq 0 ]; then
        if [ ! -e "$DESTINATION" ] && [ ! -L "$DESTINATION" ]; then
            if mv "$BACKUP_PATH" "$DESTINATION"; then
                printf '%s\n' "Previous installation restored after an incomplete replacement." >&2
                BACKUP_PATH=""
            else
                printf 'Error: automatic restoration failed; backup remains at %s.\n' \
                    "$BACKUP_PATH" >&2
            fi
        else
            printf 'Error: destination changed during replacement; backup remains at %s.\n' \
                "$BACKUP_PATH" >&2
        fi
    fi
    cleanup_stage
    if [ "$LOCK_HELD" -eq 1 ] && [ -n "$LOCK_DIR" ]; then
        rmdir "$LOCK_DIR" 2>/dev/null || \
            printf 'Error: installation lock remains at %s.\n' "$LOCK_DIR" >&2
        LOCK_HELD=0
    fi
}

trap cleanup_transaction EXIT
trap 'exit 130' HUP INT TERM

while [ "$#" -gt 0 ]; do
    case "$1" in
        --copy)
            MODE="copy"
            ;;
        --dry-run)
            DRY_RUN=1
            ;;
        --check)
            CHECK_ONLY=1
            ;;
        --replace)
            REPLACE=1
            ;;
        --mod-dir)
            shift
            [ "$#" -gt 0 ] || fail "--mod-dir requires an absolute path."
            EXPLICIT_MOD_DIR=$1
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            fail "Unknown option: $1"
            ;;
    esac
    shift
done

if [ "$CHECK_ONLY" -eq 1 ]; then
    [ "$MODE" = "link" ] || fail "--check cannot be combined with --copy."
    [ "$REPLACE" -eq 0 ] || fail "--check cannot be combined with --replace."
    [ "$DRY_RUN" -eq 0 ] || fail "--check cannot be combined with --dry-run."
fi

[ "$(uname -s 2>/dev/null)" = "Darwin" ] || \
    fail "This installer supports macOS only."
[ "${EUID:-0}" != "0" ] || \
    fail "Refusing to run a user-workbench installation as root."
EFFECTIVE_UID=$(id -u 2>/dev/null) || fail "Cannot determine the effective user."
case "$EFFECTIVE_UID" in
    ''|*[!0-9]*) fail "Cannot determine the effective user." ;;
esac
[ "$EFFECTIVE_UID" != "0" ] || \
    fail "Refusing to run a user-workbench installation as root."

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" 2>/dev/null && pwd -P) || \
    fail "Cannot resolve the installer directory."
SOURCE_DIR=$(CDPATH= cd "$SCRIPT_DIR/.." 2>/dev/null && pwd -P) || \
    fail "Cannot resolve the source checkout."

for required_path in Init.py InitGui.py package.xml; do
    [ -f "$SOURCE_DIR/$required_path" ] || \
        fail "Source checkout is missing $required_path."
done
[ -d "$SOURCE_DIR/freecad_ai" ] || \
    fail "Source checkout is missing freecad_ai."

if [ -n "$EXPLICIT_MOD_DIR" ]; then
    case "$EXPLICIT_MOD_DIR" in
        /*) ;;
        *) fail "--mod-dir must be an absolute path." ;;
    esac
    case "/$EXPLICIT_MOD_DIR/" in
        */../*|*/./*) fail "--mod-dir must not contain dot path components." ;;
    esac
    while [ "$EXPLICIT_MOD_DIR" != "/" ] && \
          [ "${EXPLICIT_MOD_DIR%/}" != "$EXPLICIT_MOD_DIR" ]; do
        EXPLICIT_MOD_DIR=${EXPLICIT_MOD_DIR%/}
    done
    [ "$EXPLICIT_MOD_DIR" != "/" ] || \
        fail "The filesystem root is not a valid FreeCAD Mod directory."
    MOD_DIR=$EXPLICIT_MOD_DIR
else
    [ -n "${HOME:-}" ] || fail "HOME is not set."
    FREECAD_ROOT="$HOME/Library/Application Support/FreeCAD"
    VERSION_COUNT=0
    VERSION_MOD_DIR=""
    for candidate in "$FREECAD_ROOT"/v*/Mod; do
        [ -d "$candidate" ] || continue
        VERSION_COUNT=$((VERSION_COUNT + 1))
        VERSION_MOD_DIR=$candidate
    done
    if [ "$VERSION_COUNT" -gt 1 ]; then
        fail "Multiple versioned FreeCAD Mod directories found; choose one with --mod-dir."
    elif [ "$VERSION_COUNT" -eq 1 ]; then
        MOD_DIR=$VERSION_MOD_DIR
    else
        MOD_DIR="$FREECAD_ROOT/Mod"
    fi
fi

canonicalize_directory_path() {
    requested_path=$1
    unresolved_suffix=""
    existing_ancestor=$requested_path

    while [ ! -e "$existing_ancestor" ] && [ ! -L "$existing_ancestor" ]; do
        path_component=$(basename "$existing_ancestor")
        unresolved_suffix="/$path_component$unresolved_suffix"
        parent_path=$(dirname "$existing_ancestor")
        [ "$parent_path" != "$existing_ancestor" ] || return 1
        existing_ancestor=$parent_path
    done
    [ -d "$existing_ancestor" ] || return 1
    physical_ancestor=$(CDPATH= cd "$existing_ancestor" 2>/dev/null && pwd -P) || \
        return 1
    printf '%s%s\n' "$physical_ancestor" "$unresolved_suffix"
}

MOD_DIR=$(canonicalize_directory_path "$MOD_DIR") || \
    fail "Cannot resolve the selected Mod directory safely."
case "$MOD_DIR" in
    /Applications|/Applications/*|/Library|/Library/*|/System|/System/*|\
    /bin|/bin/*|/etc|/etc/*|/private/etc|/private/etc/*|\
    /sbin|/sbin/*|/usr|/usr/*)
        fail "--mod-dir must not select a macOS system directory."
        ;;
esac

DESTINATION="$MOD_DIR/freecad-ai"

is_structural_workbench() {
    candidate_path=$1
    [ -d "$candidate_path" ] &&
        [ ! -L "$candidate_path" ] &&
        [ -f "$candidate_path/Init.py" ] &&
        [ -f "$candidate_path/InitGui.py" ] &&
        [ -f "$candidate_path/package.xml" ] &&
        [ -d "$candidate_path/freecad_ai" ]
}

is_current_link() {
    candidate_path=$1
    [ -L "$candidate_path" ] || return 1
    resolved_path=$(CDPATH= cd "$candidate_path" 2>/dev/null && pwd -P) || return 1
    [ "$resolved_path" = "$SOURCE_DIR" ]
}

classify_destination() {
    if is_current_link "$DESTINATION"; then
        printf '%s\n' "current-link"
    elif is_structural_workbench "$DESTINATION"; then
        printf '%s\n' "valid-copy"
    elif [ -e "$DESTINATION" ] || [ -L "$DESTINATION" ]; then
        printf '%s\n' "conflict"
    else
        printf '%s\n' "absent"
    fi
}

STATE=$(classify_destination)

printf 'Source: %s\n' "$SOURCE_DIR"
printf 'Destination: %s\n' "$DESTINATION"

if [ "$CHECK_ONLY" -eq 1 ]; then
    case "$STATE" in
        current-link)
            printf '%s\n' "Check passed: symbolic link points to this checkout."
            exit 0
            ;;
        valid-copy)
            printf '%s\n' "Check passed: copied workbench is structurally complete."
            exit 0
            ;;
        *)
            fail "No valid freecad-ai installation exists at the destination."
            ;;
    esac
fi

CORRECT_STATE="current-link"
[ "$MODE" = "copy" ] && CORRECT_STATE="valid-copy"

if [ "$STATE" = "$CORRECT_STATE" ]; then
    printf '%s\n' "Already installed correctly; no changes made."
    exit 0
fi

if [ "$STATE" != "absent" ] && [ "$REPLACE" -eq 0 ]; then
    fail "Destination conflicts with the requested mode; use --replace to preserve and replace it."
fi

if [ "$DRY_RUN" -eq 1 ]; then
    if [ "$STATE" = "absent" ]; then
        printf 'Dry run: would install using %s mode.\n' "$MODE"
    else
        printf 'Dry run: would replace the destination using %s mode after creating a backup.\n' "$MODE"
    fi
    exit 0
fi

mkdir -p "$MOD_DIR" || fail "Cannot create the selected Mod directory."
LOCK_DIR="$MOD_DIR/.freecad-ai.install.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    fail "Installation lock exists at $LOCK_DIR; another run may be active."
fi
LOCK_HELD=1

# State can change between the read-only preview above and lock acquisition.
STATE=$(classify_destination)
if [ "$STATE" = "$CORRECT_STATE" ]; then
    printf '%s\n' "Already installed correctly; no changes made."
    exit 0
fi
if [ "$STATE" != "absent" ] && [ "$REPLACE" -eq 0 ]; then
    fail "Destination conflicts with the requested mode; use --replace to preserve and replace it."
fi

STAGE_DIR=$(mktemp -d "$MOD_DIR/.freecad-ai.stage.XXXXXX") || \
    fail "Cannot create a staging directory."

if [ "$MODE" = "link" ]; then
    ln -s "$SOURCE_DIR" "$STAGE_DIR/freecad-ai" || \
        fail "Cannot create the staged symbolic link."
    staged_resolved=$(CDPATH= cd "$STAGE_DIR/freecad-ai" 2>/dev/null && pwd -P) || \
        fail "Cannot validate the staged symbolic link."
    [ "$staged_resolved" = "$SOURCE_DIR" ] || \
        fail "The staged symbolic link does not resolve to this checkout."
else
    mkdir "$STAGE_DIR/freecad-ai" || fail "Cannot create the staged copy."
    /usr/bin/rsync -a \
        --exclude '.git' \
        --exclude '.github' \
        --exclude '.vscode' \
        --exclude '.venv' \
        --exclude 'tests' \
        --exclude 'docs' \
        --exclude 'build' \
        --exclude '__pycache__' \
        --exclude '.pytest_cache' \
        --exclude '.ruff_cache' \
        --exclude '.coverage' \
        --exclude '.DS_Store' \
        --exclude '*.egg-info' \
        "$SOURCE_DIR/" "$STAGE_DIR/freecad-ai/" || \
        fail "Cannot create the staged copy."
    is_structural_workbench "$STAGE_DIR/freecad-ai" || \
        fail "The staged copy is incomplete."
fi

if [ "$STATE" != "absent" ]; then
    timestamp=$(date '+%Y%m%d-%H%M%S') || fail "Cannot create a backup timestamp."
    BACKUP_PATH="$DESTINATION.backup.$timestamp.$$"
    suffix=1
    while [ -e "$BACKUP_PATH" ] || [ -L "$BACKUP_PATH" ]; do
        BACKUP_PATH="$DESTINATION.backup.$timestamp.$suffix"
        suffix=$((suffix + 1))
    done
    mv "$DESTINATION" "$BACKUP_PATH" || fail "Cannot move the existing destination to its backup."
    printf 'Backup: %s\n' "$BACKUP_PATH"
fi

if [ -e "$DESTINATION" ] || [ -L "$DESTINATION" ]; then
    fail "Destination changed while the installation lock was held; publication stopped."
fi

if [ "$MODE" = "link" ]; then
    claim_result=0
    trap '' HUP INT TERM
    ln -s "$SOURCE_DIR" "$DESTINATION" || claim_result=$?
    trap 'exit 130' HUP INT TERM
    if [ "$claim_result" -ne 0 ]; then
        fail "Publication failed; transaction cleanup will restore the previous destination when safe."
    fi
    nested_link="$DESTINATION/$(basename "$SOURCE_DIR")"
    if is_current_link "$nested_link"; then
        rm -f "$nested_link"
        fail "Publication did not exclusively claim the destination; backup was preserved."
    fi
    if ! is_current_link "$DESTINATION"; then
        fail "Publication did not exclusively claim the destination; backup was preserved."
    fi
    OWNED_DESTINATION=1
else
    claim_result=0
    trap '' HUP INT TERM
    mkdir "$DESTINATION" || claim_result=$?
    if [ "$claim_result" -eq 0 ]; then
        OWNED_DESTINATION=1
    fi
    trap 'exit 130' HUP INT TERM
    if [ "$claim_result" -ne 0 ]; then
        fail "Publication could not exclusively claim the destination; backup was preserved."
    fi
    if ! /usr/bin/rsync -a "$STAGE_DIR/freecad-ai/" "$DESTINATION/"; then
        fail "Publication failed; transaction cleanup will restore the previous destination when safe."
    fi
    is_structural_workbench "$DESTINATION" || \
        fail "Published copy is incomplete; transaction cleanup will restore the previous destination."
fi
PUBLISH_COMPLETE=1

printf 'Installed freecad-ai using %s mode.\n' "$MODE"
if [ -n "$BACKUP_PATH" ]; then
    printf '%s\n' "The previous destination remains in the backup shown above."
fi
