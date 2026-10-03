#!/usr/bin/env python3
"""A `page/file-icons.json` előállítása a Catppuccin VS Code ikonjaiból.

Kézzel futtatandó, ha a készletet frissíteni kell (a `VERSION` átírása után):
`python3 scripts/file-icons.py`. Letölti a kiadás forrását, és a
`css-variables` változat ikonjait a lap saját ikonpalettájára köti
(`--ic-*`, page/page.css). A fájlnév- és kiterjesztés-hozzárendelés a készlet
saját táblájából jön (`src/defaults/fileIcons.ts`).
"""
from __future__ import annotations

import io
import json
import re
import tarfile
import urllib.request
from pathlib import Path

VERSION = "v1.26.0"
URL = f"https://codeload.github.com/catppuccin/vscode-icons/tar.gz/refs/tags/{VERSION}"
OUT = Path(__file__).resolve().parent.parent / "page" / "file-icons.json"

# A Catppuccin színei → a lap ikonpalettája (a gráf sávszíneinek tónusai).
COLORS = {"rosewater": "orange", "flamingo": "orange", "peach": "orange", "red": "red",
          "maroon": "red", "pink": "pink", "mauve": "purple", "lavender": "purple",
          "yellow": "yellow", "green": "green", "teal": "teal", "sky": "teal",
          "sapphire": "blue", "blue": "blue", "text": "fg", "overlay1": "muted"}

# Amit a készlet csak nyelv-azonosítóval rendel hozzá (a VS Code nyelvfelismerése
# nélkül nincs kiterjesztése): a gyakoriak a VS Code alapértelmezése szerint.
LANGUAGE_EXTS = {"shellscript": ["sh", "bash", "zsh"], "makefile": ["mk"],
                 "dockerfile": ["dockerfile"], "plaintext": ["txt"]}


def main() -> None:
    with urllib.request.urlopen(URL, timeout=60) as resp:
        archive = tarfile.open(fileobj=io.BytesIO(resp.read()), mode="r:gz")
    files = {m.name.split("/", 1)[1]: m for m in archive.getmembers() if m.isfile() and "/" in m.name}

    def read(name: str) -> str:
        return archive.extractfile(files[name]).read().decode()

    names: dict[str, str] = {}
    exts: dict[str, str] = {}
    langs: dict[str, str] = {}
    table = read("src/defaults/fileIcons.ts")
    for m in re.finditer(r"\n  '?([\w.-]+)'?: \{(.*?)\n  \},", table, re.S):
        icon, body = m.group(1), m.group(2)
        for field, target in (("fileNames", names), ("fileExtensions", exts), ("languageIds", langs)):
            found = re.search(field + r": \[(.*?)\]", body, re.S)
            for value in re.findall(r"'([^']+)'", found.group(1)) if found else ():
                target.setdefault(value.lower(), icon)
    for lang, lang_exts in LANGUAGE_EXTS.items():
        for ext in lang_exts:
            if lang in langs:
                exts.setdefault(ext, langs[lang])

    icons: dict[str, str] = {}
    for path in sorted(files):
        if not (path.startswith("icons/css-variables/") and path.endswith(".svg")):
            continue
        name = path.rsplit("/", 1)[1][:-4]
        if name.startswith("_folder") or name.startswith("_root") or name.startswith("folder_"):
            continue
        svg = re.sub(r"\s+", " ", read(path)).replace("> <", "><").strip()
        svg = re.sub(r'\s(width|height)="16"', "", svg)
        svg = re.sub(r"var\(--vscode-ctp-(\w+)\)", lambda c: f"var(--ic-{COLORS[c.group(1)]})", svg)
        icons[name] = svg

    used = set(names.values()) | set(exts.values()) | {"_file"}
    data = {
        "source": f"catppuccin/vscode-icons {VERSION}",
        "license": read("LICENSE").strip(),
        "names": dict(sorted(names.items())),
        "exts": dict(sorted(exts.items())),
        "icons": {k: v for k, v in icons.items() if k in used},
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{OUT.name}: {len(data['icons'])} ikon, {OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
