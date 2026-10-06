"""MCP szerver a Claude appnak (`git-graph --mcp`): stdio JSON-RPC, a lap ezt hívja."""
from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import MCP_NAME
from .diff import file_diff
from .gitio import set_repo
from .graph import collect_payload
from .install import RUNNING_VERSION, STABLE, SYSTEM_PYTHON, UPDATED, stable_version, watch_plugin
from .page import PAGE_FILES, page_api_mismatch, page_code, page_file
from .registry import repo_for_slug
from .state import log
from .watch import WAKE, wait_changes

WAITERS_MAX = 32              # ennél több nyitott hívásnál nem várunk (árva hívások ellen)
_WAITERS = {"n": 0}           # nyitott várakozó hívások (a `restart` kivárja őket)
_WAITERS_LOCK = threading.Lock()
_REPO_ARG = {"type": "object", "required": ["repo"], "properties": {
    "repo": {"type": "string", "description": "a repó slugja (~/.git-graph/repos.json)"}}}
_CHANGES_ARG = {"type": "object", "required": ["repo"], "properties": {
    **_REPO_ARG["properties"],
    "since": {"type": "string", "description": "az előző válasz since tokenje (üresen azonnal válaszol)"},
    "wait": {"type": "number", "description": "legfeljebb ennyi s-ig vár változásra (max. 50)"}}}
MCP_TOOLS = [
    {"name": "changes", "inputSchema": _CHANGES_ARG, "annotations": {"readOnlyHint": True},
     "description": "Vár, amíg a repó állapota (refek, worktree-k HEAD-je és munkakönyvtára) "
                    "vagy az előtérben lévő session eltér a since-étől; az állapot hashét, "
                    "a fókuszt és az új since-et adja — ha a state változott, kérd a graph_data-t."},
    {"name": "graph_data", "inputSchema": _REPO_ARG, "annotations": {"readOnlyHint": True},
     "description": "A commit-gráf teljes adata: commitok, élek, fájlstatisztika, ágak, meta."},
    {"name": "file_diff", "annotations": {"readOnlyHint": True},
     "inputSchema": {"type": "object", "required": ["repo", "sha", "path"], "properties": {
         **_REPO_ARG["properties"],
         "sha": {"type": "string", "description": "commit sha, vagy *uncommitted:<worktree-slug>"},
         "path": {"type": "string", "description": "a fájl útja, ahogy a graph_data adja"}}},
     "description": "Egy fájl diffje egy commitban, hunkokra és sorokra bontva."},
    {"name": "page_code", "annotations": {"readOnlyHint": True},
     "inputSchema": {"type": "object", "required": ["repo", "api"], "properties": {
         **_REPO_ARG["properties"],
         "api": {"type": "integer", "description": "a lap betöltőjének szerződés-verziója"}}},
     "description": "A git-graph lap élő kódja (CSS, HTML, JS) a publikált betöltőnek."},
]


def tool_text(value: object, error: bool = False) -> dict:
    """Egy tool-hívás eredménye: JSON, a hiba sima szöveg (`isError`)."""
    body = value if error else json.dumps(value)
    return {"content": [{"type": "text", "text": body}], "isError": error}


def slug_repo(args: dict) -> Path | dict:
    """A hívás repója (a fő checkout, a regiszter szerint) a lap slugjából, vagy a hiba-eredmény."""
    repo = repo_for_slug(str(args.get("repo", "")))
    if repo is None:
        return tool_text(f"ismeretlen repó: {args.get('repo')!r} — nyiss benne egy Claude sessiont (a git-graph hookja regisztrálja)", True)
    if not repo.is_dir():
        return tool_text(f"A(z) {repo} mappa nem létezik — a repót áthelyezték vagy törölték.", True)
    return repo


def changes_tool(args: dict, wait: float) -> dict:
    """A `changes` eredménye — a várakozó szálon."""
    repo = slug_repo(args)
    if isinstance(repo, dict):
        return repo
    try:
        return tool_text(wait_changes(repo, str(args.get("since") or ""), wait))
    except subprocess.CalledProcessError as exc:
        return tool_text(short_error(exc), True)


def mcp_tool(name: str, args: dict, limit: int | None) -> dict:
    """Egy tool-hívás eredménye (MCP `tools/call`). A hiba is eredmény: `isError`."""
    text = tool_text
    repo = slug_repo(args)
    if isinstance(repo, dict):
        return repo
    set_repo(repo)
    try:
        if name == "graph_data":
            return text(collect_payload(limit))
        if name == "file_diff":
            return text(file_diff(str(args.get("sha", "")), str(args.get("path", ""))))
        if name == "page_code":
            mismatch = page_api_mismatch(args.get("api"))
            return text(mismatch, True) if mismatch else text(page_code())
    except subprocess.CalledProcessError as exc:
        return text(short_error(exc), True)
    except (OSError, ValueError) as exc:
        return text(f"hiba: {exc}", True)
    return text(f"ismeretlen tool: {name}", True)


def short_error(exc: subprocess.CalledProcessError) -> str:
    """Egy git-hiba a lap láblécének: a parancs és a git első hibasora — a Python-kivétel
    teljes argumentumlistája helyett, ami a láblécet több sorba tördelte."""
    cmd = [str(a) for a in exc.cmd] if isinstance(exc.cmd, (list, tuple)) else [str(exc.cmd)]
    if "-C" in cmd:                       # git --no-optional-locks -C <repó> <alparancs> …
        cmd = cmd[cmd.index("-C") + 2:]
    reason = next((line.strip() for line in (exc.stderr or "").splitlines() if line.strip()),
                  f"kilépési kód {exc.returncode}")
    return f"git {cmd[0] if cmd else ''}: {reason}"


def mcp_serve(limit: int | None) -> int:
    """MCP szerver stdio-n — a Claude app indítja a configjából (a plugin hookja írja be).

    Az Artifact vékony lapja a Claude app host-hídján át ezt hívja: egy nyitva
    tartott `changes`-t, a `graph_data`-t csak változáskor. Stdlib JSON-RPC
    2.0, soronként egy üzenet; a stdout-ra csak protokoll mehet. Mindkét tool
    read-only-nak jelölt: így az app nem kér hívásonként megerősítést. Közben
    figyeli, eltávolították-e vagy frissítették-e a plugint (`watch_plugin`).
    """
    out = sys.stdout.buffer
    # A lap fájljai most: a futó verzió kódja, nem amit a hook később másol.
    for name in PAGE_FILES:
        try:
            page_file(name)
        except OSError as exc:
            log(f"git-graph: a lap fájlja hiányzik: {exc}")
    threading.Thread(target=watch_plugin, daemon=True).start()

    lock = threading.Lock()                # a várakozó hívások saját szálról válaszolnak

    def send(message: dict) -> None:
        with lock:
            out.write(json.dumps(message).encode() + b"\n")   # ASCII: nem függ a locale-tól
            out.flush()

    # Puffereletlen olvasás, saját sorpufferrel: újraindulni (`restart`) csak
    # akkor szabad, ha nincs beolvasott, de feldolgozatlan bemenet — a csőben
    # maradt bájtokat az új folyamat olvassa tovább. A `select` időkorlátja
    # azért kell, hogy kérés nélkül is észrevegyük a frissítést.
    fd, pending = sys.stdin.fileno(), b""
    while True:
        if UPDATED.is_set() and not pending:
            restart()
        if not select.select([fd], [], [], 1.0)[0]:
            continue
        chunk = os.read(fd, 65536)
        if not chunk:
            return 0
        pending += chunk
        while b"\n" in pending:
            raw, pending = pending.split(b"\n", 1)
            respond(raw, send, limit)


def respond(raw: bytes, send, limit: int | None) -> None:
    """Egy JSON-RPC üzenet megválaszolása (az értesítésre nincs válasz).

    Állapotot nem tart: egy `restart` utáni folyamat a kézfogás nélkül is
    kiszolgálja a következő kérést.
    """
    try:
        msg = json.loads(raw.decode("utf-8"))
    except ValueError:
        return
    mid, method = msg.get("id"), msg.get("method")
    if mid is None:
        return                                 # értesítés, pl. notifications/initialized
    params = msg.get("params") or {}
    if method == "initialize":
        result: dict = {"protocolVersion": params.get("protocolVersion", "2025-06-18"),
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": MCP_NAME, "version": "1"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": MCP_TOOLS}
    elif method == "tools/call" and params.get("name") == "changes":
        # Változásig vár: külön szálon, hogy közben a többi kérés is kiszolgálódjon.
        args = params.get("arguments") or {}
        with _WAITERS_LOCK:
            _WAITERS["n"] += 1
            crowded = _WAITERS["n"] > WAITERS_MAX

        def waiter() -> None:
            try:
                wait = 0.0 if crowded else float(args.get("wait") or 0)
                body = changes_tool(args, wait)
            except Exception as exc:           # a szerver éljen tovább
                body = tool_text(f"hiba: {exc}", True)
            send({"jsonrpc": "2.0", "id": mid, "result": body})
            with _WAITERS_LOCK:
                _WAITERS["n"] -= 1

        threading.Thread(target=waiter, daemon=True).start()
        return
    elif method == "tools/call":
        try:
            result = mcp_tool(params.get("name", ""), params.get("arguments") or {}, limit)
        except Exception as exc:               # a szerver éljen tovább
            result = {"content": [{"type": "text", "text": f"hiba: {exc}"}], "isError": True}
    else:
        send({"jsonrpc": "2.0", "id": mid,
              "error": {"code": -32601, "message": f"ismeretlen metódus: {method}"}})
        return
    send({"jsonrpc": "2.0", "id": mid, "result": result})


def restart() -> None:
    """A frissült stabil másolat futtatása ugyanebben a folyamatban (stdio marad)."""
    log(f"git-graph: frissült ({RUNNING_VERSION} → {stable_version()}) — újraindulás")
    WAKE.set()                                 # a nyitott várakozó hívások most válaszolnak
    deadline = time.monotonic() + 1
    while _WAITERS["n"] and time.monotonic() < deadline:
        time.sleep(0.02)
    sys.stdout.flush()
    python = sys.executable or SYSTEM_PYTHON
    os.execv(python, [python, str(STABLE), *sys.argv[1:]])

