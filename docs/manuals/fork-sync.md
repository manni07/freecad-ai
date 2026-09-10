# Synchronizing this fork

The maintained repository is **manni07/freecad-ai**, branch **master**.
The source of incoming updates is **ghbalf/freecad-ai**, branch **master**.
Only the maintained fork is a publication target.

## Direction and preservation

Merge `upstream/master` into a temporary branch based on `origin/master`,
test the combined result, and open the PR with **base repository
manni07/freecad-ai**, **base branch master**. Use a merge commit so both
histories remain reachable. Do not reset the fork to upstream, force-push,
or squash an upstream synchronization: these actions either discard fork
work or obscure the ancestry needed by the next synchronization.

GitHub does not send commits back to the parent repository when a fork is
synchronized. A PR opened against `ghbalf/freecad-ai` is a separate action;
do not use that destination for fork maintenance. In the GitHub PR form,
inspect the **base repository**, not just the branch name. Both repositories
use `master`.

## Local push guard

The existing local checkout and its linked worktrees use these repository-local
settings (Git does not copy them into newly cloned repositories):

```sh
git config --local remote.pushDefault origin
git config --local push.default simple
git config --local branch.master.pushRemote origin
git config --local remote.upstream.pushurl disabled://upstream-read-only
```

`origin` fetches/pushes `https://github.com/manni07/freecad-ai.git`.
`upstream` still fetches `https://github.com/ghbalf/freecad-ai.git`, but a
push via that remote fails locally. This prevents accidental Git pushes
through the configured remote; it does not restrict GitHub UI/API PR targets
or somebody explicitly supplying a different push URL.

The fork is public. These controls prevent accidental upstream publication
from this workflow; they do not prevent another person from copying public
code. No upstream access or branch-protection settings were changed.

## Integration of 2026-09-10

- Fork starting point: `479b03b6810d6eb2268e3a643a48032f8a9fadbf`.
- Upstream starting point: `1966688556bbe8d9af92e9a8641f40cdc05bd219`
  (`v0.24.0-alpha`).
- Before merging: 17 fork-only commits and 42 upstream-only commits.
- Integration branch: `manni07/upstream-sync-20260910`.
- Recovery ref: `manni07/backup-before-upstream-sync-20260910`, pointing to
  the unmodified fork starting point.

Connection profiles, per-utility models, profile capability fixes, Settings
layout fixes, and release metadata come from upstream. The fork's MCP transport,
controller, startup routes, authentication/admission tests, and token-file
contract are retained. Upstream's optional inline-token mode would weaken the
fork's existing mandatory authentication and is deliberately not adopted.
The upstream release notes remain as history, with this fork difference stated
in the current changelog and Settings dialog.

The profile merge also extends the existing private-key migration to every
profile. The new regression tests exercise inactive utility credentials and
rollback when a later profile fails. Release metadata consistently declares
`0.24.0-alpha` / `0.24.0a0`; this does not add host-runtime qualification claims.

Two of upstream's Settings geometry tests also failed unchanged on macOS:
the scroll area reported a 540 px hint for 611 px content. The integration
uses the actual content width plus margins and scrollbar allowance, fixing
the clipping without relaxing those tests.

This synchronization concerns the committed GitHub fork. Additional modified
and untracked files in the original local checkout are not included. It is
performed in an isolated worktree and does not install or activate the combined
addon in a running FreeCAD session.

## Verification

Fresh local verification on 2026-09-10 used Python 3.12.11, pytest 9.1.1,
and PySide6 Essentials 6.11.2 with offscreen Qt:

- Original fork commit: 1,660 unit tests passed, no skips.
- Final combined tree: 1,837 unit tests passed, no skips (155.28 s).
- The two new credential-migration regressions failed before the migration
  update and passed after it. The unchanged upstream geometry suite reproduced
  two failures before the layout correction; all five geometry tests then passed.
- Critical Ruff diagnostics and staged whitespace checks passed.
- No matches in the staged private-key/provider-token signature scan.

Run the full unit suite with Python 3.11+ and PySide6 installed:

```sh
QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 \
  python -m pytest -q -p no:cacheprovider tests/unit
```

The fork's GitHub regression workflow includes both its existing protection
tests and the new profile/migration tests. Native FreeCAD integration tests
require a separately qualified runtime and are not represented by unit-test
success. PR verification records the actual results and any remaining limits.
