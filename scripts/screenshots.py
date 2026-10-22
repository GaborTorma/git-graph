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
from test_subtree import SubtreeTest  # noqa: E402

IMG = ROOT / "docs" / "img"


class SubtreeShots(SubtreeTest):
    """Subtree-remote: a chip, a tükör-commitok és a remote-szűrő."""

    WIDTH, HEIGHT = 900, 420

    def test_shots(self) -> None:
        out = IMG / "subtree-remote"
        out.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(out / "graph.png"))
        self.page.locator("#remotesBtn").click()
        self.settle()
        self.page.screenshot(path=str(out / "remote-filter.png"), clip={"x": 0, "y": 0, "width": 900, "height": 180})


# Csak a képek készülnek, a SubtreeTest saját tesztjei nem.
for name in [n for n in dir(SubtreeTest) if n.startswith("test_")]:
    setattr(SubtreeShots, name, None)

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromName("test_shots", SubtreeShots)
    sys.exit(not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful())
