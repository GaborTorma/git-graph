"""A teljes nézet fájlfája és a WIP sor szerkesztése: fájllista, tartalomkeresés, írás a lemezre."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path, PurePosixPath

from .diff import SHA_RE, TEXT_MAX, as_text, digest, disk_file, lf, worktree_root
from .gitio import git
from .page import file_icon, file_icons
from .worktrees import UNCOMMITTED_RE

TREE_MAX = 20000        # eddig egy válaszban a teljes lista; fölötte mappánként, lustán
GREP_MAX = 2000         # a tartalomkeresés legfeljebb ennyi fájlt ad (`more`)


def tree_source(sha: str) -> tuple:
    """A fa forrása a lapról jövő sha szerint: `(worktree, fajta)` — a fajta `commit`,
    `uncommitted` vagy `staged`. Mint a `text_diff`-ben: a sha csak hex lehet (különben
    `--opció`-ként futna), az ál-soré csak egy élő worktree-é."""
    pending = UNCOMMITTED_RE.match(sha)
    if pending:
        return worktree_root(pending[2]), pending[1]
    if not SHA_RE.match(sha):
        raise ValueError(f"érvénytelen commit: {sha!r}")
    return None, "commit"


def clean_dir(folder: str) -> str:
    """A kért mappa útja (`""`: a gyökér), záró `/` nélkül; a repón kívülre mutató hiba."""
    folder = folder.strip("/")
    parts = folder.split("/") if folder else []
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"érvénytelen mappa: {folder!r}")
    return folder


def nul_list(out: str) -> list[str]:
    return [p for p in out.split("\0") if p]


def all_paths(sha: str, root: Path | None, kind: str) -> list[str]:
    """Az állapot minden fájlja: a commité (`ls-tree -r`), WIP-en a worktree-é (a követett és a
    nem ignorált követetlen fájlok), a stage-elt soron az indexé."""
    if kind == "commit":
        return nul_list(git("ls-tree", "-r", "-z", "--name-only", sha))
    extra = ("--others", "--exclude-standard") if kind == "uncommitted" else ()
    # egy ütköző (unmerged) fájl az indexben több bejegyzés: egyszer
    return sorted(set(nul_list(git("ls-files", "-z", "--cached", *extra, repo=root))))


def entries(paths: list[str]) -> dict:
    """A fájlok a lapnak: `{"files": [{"path", "icon"}], "fileIcons": {ikonnév: svg}}` — csak a
    használt ikonok SVG-je."""
    svgs = file_icons().get("icons", {})
    files, used = [], {}
    for path in paths:
        icon = file_icon(path)
        files.append({"path": path, "icon": icon})
        if icon:
            used[icon] = svgs[icon]
    return {"files": files, "fileIcons": used}


def level(paths: list[str], folder: str) -> tuple[list[str], list[str]]:
    """Egy mappa szintje a teljes listából: (az alsó mappák teljes útja, a fájlok)."""
    prefix = f"{folder}/" if folder else ""
    dirs, files = {}, []
    for path in paths:
        if not path.startswith(prefix):
            continue
        name, slash, _ = path[len(prefix):].partition("/")
        if slash:
            dirs[prefix + name] = True
        else:
            files.append(path)
    return list(dirs), files


def commit_level(sha: str, folder: str) -> tuple[list[str], list[str]]:
    """Egy mappa szintje a commitban, nem rekurzívan (`ls-tree <sha> -- <mappa>/`)."""
    out = git("ls-tree", "-z", sha, *(["--", f"{folder}/"] if folder else []))
    dirs, files = [], []
    for entry in nul_list(out):
        meta, _, path = entry.partition("\t")
        (dirs if meta.split(" ")[1] == "tree" else files).append(path)
    return dirs, files


def grep_files(sha: str, root: Path | None, kind: str, needle: str) -> dict:
    """Tartalomkeresés (kis-nagybetűtől függetlenül, szó szerint, bináris nélkül): a commiton,
    Uncommitted soron a munkakönyvtárban (követetlen fájlban is), stage-elt soron az
    indexben. A keresett szöveg `-e`-vel megy (nem opció); útszűkítés nincs."""
    where = {"commit": [], "uncommitted": ["--untracked"], "staged": ["--cached"]}[kind]
    args = ["grep", "-l", "-z", "-I", "-F", "-i", "--no-color", *where, "-e", needle,
            *([sha] if kind == "commit" else [])]
    try:
        out = git(*args, repo=root)
    except subprocess.CalledProcessError as exc:
        if exc.returncode == 1:                   # nincs találat
            return {**entries([]), "more": False}
        raise
    paths = nul_list(out)
    if kind == "commit":                          # `<sha>:<út>`
        paths = [p[len(sha) + 1:] for p in paths]
    return {**entries(paths[:GREP_MAX]), "more": len(paths) > GREP_MAX}


def file_tree(sha: str, folder: str | None = None, grep: str | None = None) -> dict:
    """A fájlfa (`file_tree` tool). Kereséssel a találatok (`grep_files`); nélküle az állapot
    minden fájlja, ha legfeljebb `TREE_MAX`, különben — és ha a lap egy mappát kér (`dir`) —
    csak a kért szint: `{"lazy": true, "dir", "dirs", "files", "fileIcons"}`."""
    root, kind = tree_source(sha)
    if grep:
        return grep_files(sha, root, kind, grep)
    if folder is None:
        paths = all_paths(sha, root, kind)
        if len(paths) <= TREE_MAX:
            return entries(paths)
        dirs, files = level(paths, "")
        return {"lazy": True, "dir": "", "dirs": dirs, **entries(files)}
    folder = clean_dir(folder)
    dirs, files = commit_level(sha, folder) if kind == "commit" else level(all_paths(sha, root, kind), folder)
    return {"lazy": True, "dir": folder, "dirs": dirs, **entries(files)}


def write_target(root: Path, path: str) -> Path:
    """Az írható fájl (feloldott út) — vagy `ValueError`: abszolút út, `..`, `.git`, üres
    komponens, a worktree-n kívülre mutató symlink, a git által nem ismert (ignorált), nem
    létező vagy nem szabályos fájl."""
    parts = path.split("/")
    if not path or PurePosixPath(path).is_absolute() or path.startswith("~"):
        raise ValueError(f"tiltott út: {path!r}")
    if any(p in ("", ".", "..") or p.lower() == ".git" for p in parts):
        raise ValueError(f"tiltott út: {path!r}")
    file = disk_file(root, path)
    if file is None:
        raise ValueError(f"nem írható (nem ismert, nem szabályos, vagy a worktree-n kívüli) fájl: {path!r}")
    return file


def write_file(sha: str, path: str, text: str, base: str) -> dict:
    """A WIP sor egy fájljának mentése a lapról (`write_file` tool) — a munkakönyvtárba, a git
    állapotához (index, refek) nem nyúl.

    Csak az Uncommitted sor élő worktree-jébe ír (`write_target`), UTF-8 szöveget
    (`TEXT_MAX`-ig, NUL nélkül), és csak szöveges fájl helyére. Ha a lemezen lévő tartalom
    hashe nem a lap által ismert `base`, nem ír: `{"ok": false, "conflict": true, "hash",
    "text"}` (a lemezen lévő, `\\n`-es). A lap `\\n`-nel küld: CRLF-es fájlba CRLF-fel írunk; a záró
    újsor a `text` szerint. Atomi cserével ír, a fájl jogosultsága marad.
    """
    pending = UNCOMMITTED_RE.match(sha)
    if not pending or pending[1] != "uncommitted":
        raise ValueError(f"csak az Uncommitted sor fájlja írható: {sha!r}")
    if "\0" in text:
        raise ValueError("a szöveg NUL-t tartalmaz")
    file = write_target(worktree_root(pending[2]), path)
    data = file.read_bytes()
    current = as_text(data)
    if current is None or len(data) > TEXT_MAX:
        raise ValueError(f"nem szöveges (bináris, nem UTF-8 vagy túl nagy) fájl: {path!r}")
    if digest(data) != base:
        return {"ok": False, "conflict": True, "hash": digest(data), "text": lf(current)}
    text = lf(text)
    if b"\r\n" in data:
        text = text.replace("\n", "\r\n")
    out = text.encode("utf-8")
    if len(out) > TEXT_MAX:
        raise ValueError(f"túl nagy szöveg: {len(out)} bájt (legfeljebb {TEXT_MAX})")
    # atomi csere egy melletti ideiglenes fájlból: elbukott írásnál a régi tartalom ép marad; a jogosultság marad
    tmp = file.with_name(f".{file.name}.{os.getpid()}.git-graph.tmp")
    try:
        tmp.write_bytes(out)
        os.chmod(tmp, file.stat().st_mode & 0o7777)
        os.replace(tmp, file)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
    return {"ok": True, "hash": digest(out)}
