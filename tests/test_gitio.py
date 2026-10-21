"""A git-hívások (`gitio`): a `stash list` versenyhelyzete."""
from __future__ import annotations

import shutil

from helpers import HomeTestCase, git_in

# Kamu git: a `stash list` első hívása úgy bukik el, mint amikor egy `stash pop` / `drop`
# a ref ellenőrzése és a reflog olvasása között tünteti el a `refs/stash`-t.
FLAKY_GIT = """#!/bin/sh
case "$*" in
  *" stash list"*)
    if [ -e "{marker}" ]; then rm "{marker}"; echo "fatal: bad revision 'refs/stash'" >&2; exit 128; fi ;;
esac
exec "{git}" "$@"
"""


class StashListTest(HomeTestCase):
    def flaky(self, gg) -> None:
        marker = self.home / "fail-once"
        marker.touch()
        script = self.home / "git"
        script.write_text(FLAKY_GIT.format(marker=marker, git=shutil.which("git")), encoding="utf-8")
        script.chmod(0o755)
        gg.gitio.git_bin = lambda: str(script)

    def test_ref_vanished(self) -> None:
        """Ha a `refs/stash` a hívás közben megszűnt, nincs stash: üres lista, nem hiba."""
        repo = self.plain_repo()
        gg = self.load()
        self.flaky(gg)
        self.assertEqual(gg.gitio.stash_list("--format=%H", repo=repo), "")

    def test_ref_rewritten(self) -> None:
        """Ha a `refs/stash` megvan, egy újrapróba olvassa a stash-eket."""
        repo = self.plain_repo()
        (repo / "a.txt").write_text("2\n", encoding="utf-8")
        git_in(repo, "stash", "-q")
        sha = git_in(repo, "rev-parse", "refs/stash").strip()
        gg = self.load()
        self.flaky(gg)
        self.assertEqual(gg.gitio.stash_list("--format=%H", repo=repo).split(), [sha])
