"""A gép állapota (`~/.git-graph`), a napló és a fájlírás eszközei."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

STATE_DIR = Path.home() / ".git-graph"


def log(message: str) -> None:
    """Napló stderr-re — a hook és az MCP stdout-ja a protokollé."""
    print(message, file=sys.stderr, flush=True)


def read_json(path: Path) -> dict | None:
    """A JSON-fájl tartalma; `{}`, ha nincs; None, ha olvashatatlan (akkor nem nyúlunk hozzá)."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_json(path: Path, data: dict) -> None:
    """Írás mentéssel — idegen config-fájlt csak így írunk felül."""
    if path.exists():
        shutil.copy2(path, path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d%H%M%S')}"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def place(new: bytes, dst: Path, mode: int) -> None:
    """Atomi csere, csak ha a tartalom változott — folyamatonként saját ideiglenes fájlból."""
    if dst.exists() and dst.read_bytes() == new:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f".{dst.name}.{os.getpid()}.tmp")
    tmp.write_bytes(new)
    tmp.chmod(mode)
    tmp.replace(dst)
