"""Git-hívások (csak olvasnak) és a kimenetük értelmezése; a vizsgált repó."""
from __future__ import annotations

import functools
import os
import re
import subprocess
from pathlib import Path

# A vizsgált repó gyökere — a `set_repo` állítja (a CLI a --repo / CWD alapján, a
# `git-graph --mcp` hívásonként a lap slugja szerint). Más modulból `gitio.REPO`-ként
# olvasandó: egy `from … import REPO` a régi értéket tartaná meg.
REPO = Path.cwd()


def set_repo(repo: Path) -> None:
    """A vizsgált repó váltása; a remote-ok gyorstára repónként más."""
    global REPO, _REMOTES
    REPO, _REMOTES = repo, None

# Mezőelválasztó (unit separator) és rekordelválasztó (record separator):
# commit-üzenetben nem fordulhatnak elő, ellentétben bármilyen látható jellel.
FS = "\x1f"
RS = "\x1e"


@functools.cache
def git_bin() -> str:
    """A valódi git bináris (`git --exec-path` mellől), különben a PATH-on lévő `git`.

    macOS-en a `/usr/bin/git` csak shim (`xcrun`), hívásonként ~6 ms-mal lassabb
    (mérve: 12 → 6 ms) — az app szűk PATH-tal indítja a szervert, így azt kapná.
    """
    try:
        path = os.path.realpath(os.path.join(subprocess.run(
            ["git", "--exec-path"], capture_output=True, text=True, check=True).stdout.strip(), "git"))
    except (OSError, subprocess.CalledProcessError):
        return "git"
    return path if os.access(path, os.X_OK) else "git"


def git(*args: str, repo: Path | None = None) -> str:
    # --no-optional-locks: a `git status` egyébként FRISSÍTI az indexet, ahhoz
    # pedig `index.lock`-ot vesz. A szerver kétmásodpercenként kérdez — ez a
    # Fejlesztő saját git-parancsait akasztaná meg („Unable to create
    # index.lock"). Olvasó eszköznek úgyis felesleges.
    return subprocess.run(
        [git_bin(), "--no-optional-locks", "-C", str(repo or REPO), *args],
        capture_output=True, text=True, check=True,
    ).stdout


def resolve_repo(start: Path) -> Path:
    """A megadott könyvtárat tartalmazó git repó gyökere."""
    result = subprocess.run(
        [git_bin(), "-C", str(start), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"HIBA: {start} nem git repó (vagy nincs git a PATH-on).")
    return Path(result.stdout.strip())

_REMOTES: set[str] | None = None


def remotes() -> set[str]:
    global _REMOTES
    if _REMOTES is None:
        _REMOTES = {r.strip() for r in git("remote").splitlines() if r.strip()}
    return _REMOTES

def worktree_list(repo: Path | None = None) -> list[dict]:
    """A repó élő worktree-jei (`git worktree list --porcelain`); az első a fő checkout.

    A csupasz (bare) és a megszűnt (prunable) bejegyzés kimarad. `head` a
    worktree HEAD-je (commit nélküli repóban None), `branch` a kivett ág
    (leválasztott HEAD-nél nincs).
    """
    out: list[dict] = []
    cur: dict = {}
    for line in git("worktree", "list", "--porcelain", repo=repo).splitlines() + [""]:
        if not line:
            if cur.get("path") and not cur.get("bare") and not cur.get("prunable"):
                out.append(cur)
            cur = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            cur = {"path": Path(value), "head": None, "branch": None}
        elif key == "HEAD":
            cur["head"] = value if value.strip("0") else None
        elif key == "branch":
            cur["branch"] = value[len("refs/heads/"):] if value.startswith("refs/heads/") else value
        elif key in ("bare", "prunable"):
            cur[key] = True
    # A hozzáadott worktree-k a létrehozásuk sorrendjében (a git az admin-mappák
    # olvasási sorrendjében adja, macOS-en ez a név szerinti ábécé).
    return out[:1] + sorted(out[1:], key=worktree_created)


def admin_dir(wt: dict) -> Path:
    """A worktree git-mappája: a fő checkoutban a `.git`, a hozzáadottban az, amire
    a `.git` fájlja mutat (`gitdir: …/.git/worktrees/<név>`). `OSError`, ha nincs."""
    dot = wt["path"] / ".git"
    return dot if dot.is_dir() else Path(dot.read_text(encoding="utf-8").partition("gitdir:")[2].strip())

def worktree_created(wt: dict) -> float:
    """A worktree létrehozásának ideje: az admin-mappája (`.git/worktrees/<név>`)
    születési ideje; ahol ez nincs (Linux), a `ctime`-ja."""
    try:
        st = admin_dir(wt).stat()
    except OSError:
        return float("inf")
    return getattr(st, "st_birthtime", st.st_ctime)


def main_checkout(repo: Path) -> Path:
    """A repó fő checkoutja — a worktree-k közös lapja ennek a slugján fut."""
    worktrees = worktree_list(repo)
    return worktrees[0]["path"] if worktrees else repo

def ahead_behind(base: str, rev: str) -> list[int]:
    """`[előny, lemaradás]`: a `rev` commitjai a `base`-en túl, és a `base`-é a `rev`-en túl."""
    behind, ahead = git("rev-list", "--left-right", "--count", f"{base}...{rev}").split()
    return [int(ahead), int(behind)]


def config_get(key: str) -> str:
    """Érték a repó lokális git configjából (hiányzó kulcsnál üres sztring)."""
    try:
        return git("config", "--local", "--get", f"git-graph.{key}").strip()
    except subprocess.CalledProcessError:
        return ""


def remember_artifact(url: str, digest: str | None = None) -> None:
    """Az Artifact URL-je + a publikált lap hashe a `.git/config`-ba.

    A hash alapján a publikálás kihagyja a változatlan lapot. A `.git/config`
    sosem commitolódik, és repónként külön tárol — pont, ami ide kell.
    """
    section = "git-graph"
    git("config", "--local", f"{section}.artifact", url)
    if digest:
        git("config", "--local", f"{section}.artifactHash", digest)
    if not digest:                        # kézi --set-artifact: a hash már nem érvényes
        try:
            git("config", "--local", "--unset", f"{section}.artifactHash")
        except subprocess.CalledProcessError:
            pass


def worktree_paths() -> list[Path]:
    """A repó worktree-jei; az első a fő checkout."""
    return [Path(line[len("worktree "):])
            for line in git("worktree", "list", "--porcelain").splitlines()
            if line.startswith("worktree ")]

def repo_name() -> str:
    """A repó neve: az `origin` remote URL-jéből, különben a mappanév.

    A mappanév félrevezető lehet (más néven klónozva, örökölt könyvtárnév) —
    a remote hordozza a repó tényleges nevét.
    """
    try:
        url = git("remote", "get-url", "origin").strip()
    except subprocess.CalledProcessError:
        return REPO.name
    if not url:
        return REPO.name
    name = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name or REPO.name

def repo_url() -> str:
    """Az `origin` GitHub-webcíme (`https://github.com/<owner>/<repo>`), különben üres.

    Ehhez linkeli a lap a commit-üzenetek `#12` issue/PR-hivatkozásait. Más
    hoston a `#szám` mást jelent (GitLabon az MR `!szám`), ott nincs link.
    """
    try:
        url = git("remote", "get-url", "origin").strip()
    except subprocess.CalledProcessError:
        return ""
    m = re.match(r"(?:https?://|ssh://)?(?:[^@/]+@)?github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    return f"https://github.com/{m[1]}/{m[2]}" if m else ""

def default_base() -> str:
    """Az alapág: amire az `origin/HEAD` mutat (pl. `origin/main`); üres, ha nincs."""
    try:
        return git("symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
    except subprocess.CalledProcessError:
        return ""

def numstat_new_path(path: str) -> str:
    """A `--numstat` átnevezés-alakjából (`a => b`, `x/{a => b}/y`) az új út."""
    if " => " not in path:
        return path
    if "{" in path:
        return re.sub(r"\{[^{}]* => ([^{}]*)\}", r"\1", path).replace("//", "/")
    return path.split(" => ", 1)[1]

def numstat_old_path(path: str) -> str:
    """A `--numstat` átnevezés-alakjából a régi út (a `numstat_new_path` párja)."""
    if " => " not in path:
        return path
    if "{" in path:
        return re.sub(r"\{([^{}]*) => [^{}]*\}", r"\1", path).replace("//", "/")
    return path.split(" => ", 1)[0]

