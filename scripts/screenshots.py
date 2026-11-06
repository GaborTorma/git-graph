"""A funkcióoldalak képei (`docs/img/<funkció>/`), a lap tesztjeinek fixture-repóiból.

A lap ugyanúgy töltődik be, mint a tesztekben (`tests/page/harness.py`: valódi betöltő +
`git-graph --mcp`, kamu HOME, rögzített méret és dátumok), így a kép újragenerálható; a
fájlnév képernyőnként állandó.

  uv run --no-project --with playwright==1.63.0 python scripts/screenshots.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests" / "page"))
from test_full_view import FullViewTest  # noqa: E402
from test_header import HeaderCase  # noqa: E402
from test_subtree import SubtreeTest  # noqa: E402
from test_wip_layer import WipCase  # noqa: E402

IMG = ROOT / "docs" / "img"


def folder(name: str) -> Path:
    out = IMG / name
    out.mkdir(parents=True, exist_ok=True)
    return out


class SubtreeShots(SubtreeTest):
    """Subtree-remote: a chip, a tükör-commitok és a remote-ok kapcsolói az ágválasztóban."""

    WIDTH, HEIGHT = 900, 420

    def test_shots(self) -> None:
        out = folder("subtree-remote")
        self.page.screenshot(path=str(out / "graph.png"))
        self.page.locator("#branchBtn").click()
        self.page.mouse.move(450, 400)   # a gomb buboréka ne takarja a menüt
        self.settle()
        self.page.screenshot(path=str(out / "remote-filter.png"), clip={"x": 0, "y": 0, "width": 900, "height": 420})


class HeaderShots(HeaderCase):
    """Fejléc: a szűrt gombok, az ágválasztó a remote-kapcsolókkal, a keresés popupja."""

    WIDTH, HEIGHT = 900, 820

    def test_shots(self) -> None:
        out = folder("header")
        self.toggle_remote("upstream")
        self.close_menu()
        self.select("dev", "main origin/main", "feat/menu")
        self.search("menü", refs=True)
        self.page.mouse.move(450, 800)
        self.settle()
        self.page.screenshot(path=str(out / "header.png"), clip={"x": 0, "y": 0, "width": 900, "height": 44})
        self.open_branches()
        self.page.mouse.move(890, 800)
        self.settle()
        pop = self.page.locator("#branchPop").bounding_box()
        self.page.screenshot(path=str(out / "branches.png"),
                             clip={"x": 0, "y": 0, "width": 900, "height": pop["y"] + pop["height"] + 8})
        self.close_menu()
        self.open_search()
        self.page.mouse.move(450, 800)
        self.settle()
        pop = self.page.locator("#searchPop").bounding_box()
        self.page.screenshot(path=str(out / "search.png"),
                             clip={"x": 0, "y": 0, "width": 900, "height": pop["y"] + pop["height"] + 8})


class FullViewShots(FullViewTest):
    """Fájlfa és teljes nézet: a sidebar a lenyitott commit mellett, és egy fájl teljes képernyőn."""

    WIDTH, HEIGHT = 1100, 640

    def test_shots(self) -> None:
        out = folder("full-view")
        self.open_side()
        self.open_commit()
        self.page.mouse.move(5, 5)
        self.settle()
        self.page.screenshot(path=str(out / "sidebar.png"))
        self.open_full("page/js/diff.js")
        self.page.mouse.move(5, 5)
        self.settle()
        self.page.screenshot(path=str(out / "full.png"))


class WipShots(WipCase):
    """Kóddiff: a HEAD-commit fájlja a lemez szövegével, a WIP eltérései kék / narancs rétegben."""

    WIDTH, HEIGHT = 900, 900

    def test_shots(self) -> None:
        out = folder("code-diff")
        self.open_app()
        self.page.mouse.move(5, 5)
        self.settle()
        box = self.page.locator('.details .file[data-path="app.py"]').bounding_box()
        diff = self.page.locator('.details .file[data-path="app.py"] + .diff').bounding_box()
        top = box["y"] - 4
        self.page.screenshot(path=str(out / "wip-layer.png"), clip={
            "x": diff["x"] - 4, "y": top, "width": diff["width"] + 8, "height": min(520, diff["y"] + diff["height"] - top + 4)})


SHOTS = [SubtreeShots, HeaderShots, FullViewShots, WipShots]
# Csak a képek készülnek, a fixture-osztályok saját tesztjei nem.
for shots in SHOTS:
    for name in [n for n in dir(shots.__mro__[1]) if n.startswith("test_")]:
        setattr(shots, name, None)

if __name__ == "__main__":
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName("test_shots", s) for s in SHOTS)
    sys.exit(not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful())
