"""A git-hívások (`gitio`): a `stash list` versenyhelyzete."""
from __future__ import annotations

import os
import shutil
from unittest import mock

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


# Kamu `git` a PATH elején: az `--exec-path` a `{exec_file}`-ba írt mappát adja (mint a
# Homebrew verziós Cellar-mappája), minden más hívás a valódi gitnek megy.
EXEC_PATH_GIT = """#!/bin/sh
if [ "$1" = "--exec-path" ]; then cat "{exec_file}"; exit 0; fi
exec "{git}" "$@"
"""


class GitBinTest(HomeTestCase):
    def test_binary_removed(self) -> None:
        """Ha a megjegyzett git bináris eltűnik (pl. `brew upgrade git`), a hívás az újat keresi meg."""
        repo = self.plain_repo()
        real = shutil.which("git")
        exec_file = self.home / "exec-path"
        old, new = self.home / "2.56.0", self.home / "2.56.0_1"
        for d in (old, new):
            d.mkdir()
            (d / "git").write_text(f'#!/bin/sh\nexec "{real}" "$@"\n', encoding="utf-8")
            (d / "git").chmod(0o755)
        exec_file.write_text(str(old), encoding="utf-8")
        shim = self.home / "bin"
        shim.mkdir()
        (shim / "git").write_text(EXEC_PATH_GIT.format(exec_file=exec_file, git=real), encoding="utf-8")
        (shim / "git").chmod(0o755)
        with mock.patch.dict(os.environ, {"PATH": f"{shim}:{os.environ['PATH']}"}):
            gg = self.load()
            head = gg.gitio.git("rev-parse", "HEAD", repo=repo)
            shutil.rmtree(old)
            exec_file.write_text(str(new), encoding="utf-8")
            self.assertEqual(gg.gitio.git("rev-parse", "HEAD", repo=repo), head)
