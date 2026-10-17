"""Képek a diffben (#53): a képfájl és a markdown-kép képként, a Mermaid-diagramok páros
elrendezésében; új / törölt kép bal csíkkal, a változott pár színes kerettel, sakktábla, a
túl nagy kép mérete, az SVG kódnézete, és a markdown-kép oldalanként a saját változatából."""
from __future__ import annotations

import struct
import unittest
import zlib
from pathlib import Path

from harness import PageTestCase, git_in


def png(width: int, height: int, rgba: tuple) -> bytes:
    """Egyszínű PNG (a stdlib-ből)."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    row = b"\0" + bytes(rgba) * width
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * height)) + chunk(b"IEND", b""))


RED, BLUE, CLEAR = (200, 40, 40, 255), (40, 40, 200, 255), (0, 0, 0, 0)
SVG_OLD = '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" fill="red"/></svg>\n'
SVG_NEW = SVG_OLD.replace("red", "blue")
MD_OLD = """# Doksi

![gráf](img/graph.png)

Egy sor ![pont](img/dot.png) a szövegben, és egy ![badge](https://img.shields.io/badge/x-y-green) is.

![hiány](img/nincs.png)

Régi mondat.
"""
MD_NEW = MD_OLD.replace("Régi mondat.", "Új mondat.").replace("Egy sor", "Egy új sor")

# a figurák: [osztály a `img-fig` nélkül, van-e képe]
FIGS = "fs => fs.map(f => [f.className.replace('img-fig', '').trim(), !!f.querySelector('img')])"
# a nézet közepe és a két keret széle: [a régi jobb széle a középtől, az új bal széle a középtől]
EDGES = ("v => { const r = v.getBoundingClientRect(), [a, b] = [...v.querySelectorAll('.img-fig')]"
         ".map(f => f.getBoundingClientRect()); return [r.left + r.width / 2 - a.right, b.left - (r.left + r.width / 2)]; }")


class ImagesTest(PageTestCase):
    SUBJECT = "kép"

    @classmethod
    def prepare(cls, repo: Path) -> None:
        (repo / "docs" / "img").mkdir(parents=True)
        files = {
            "logo.png": (png(60, 40, RED), png(60, 40, BLUE)),
            "uj.png": (None, png(70, 20, (40, 160, 40, 255))),
            "torolt.png": (png(30, 30, RED), None),
            "wide.png": (png(500, 20, RED), png(500, 20, BLUE)),
            "atlatszo.png": (None, png(40, 40, CLEAR)),
            "icon.svg": (SVG_OLD, SVG_NEW),
            "photo.jpg": (None, b"\xff\xd8\xff" + b"\0" * int(2.4 * 1048576)),
            "regi-nev.png": (png(20, 20, RED), None),
            "uj-nev.png": (None, png(20, 20, RED)),
            "docs/img/graph.png": (png(50, 30, RED), png(50, 30, BLUE)),
            "docs/img/dot.png": (png(8, 8, RED), png(8, 8, RED)),
            "docs/README.md": (MD_OLD, MD_NEW),
        }
        for side, msg in ((0, cls.SUBJECT), (1, f"{cls.SUBJECT}: módosítva")):
            for name, versions in files.items():
                path, data = repo / name, versions[side]
                if data is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(data if isinstance(data, bytes) else data.encode())
            git_in(repo, "add", "-A")
            git_in(repo, "commit", "-qm", msg)
        # a nem commitolt sor: a kép a lemezen más, mint az indexben
        (repo / "docs" / "img" / "graph.png").write_bytes(png(50, 30, (40, 160, 40, 255)))
        (repo / "docs" / "README.md").write_text(MD_NEW.replace("Egy új sor", "Egy lemezen sor"), encoding="utf-8")

    def figs(self, scope: str = ".diff") -> list:
        self.page.wait_for_selector(f"{scope} .img-fig")
        self.settle()
        return self.page.locator(f"{scope} .img-fig").evaluate_all(FIGS)

    def added_or_deleted(self, name: str, kind: str, color: str) -> None:
        self.open_file(name)
        self.assertEqual(self.figs(), [[kind, True]])
        gap, stripe, want = self.page.locator(".diff .img-view").evaluate(
            f"""v => {{ const f = v.querySelector('.img-fig'), s = getComputedStyle(f);
              const probe = Object.assign(document.createElement('i'), {{ style: 'color: var({color})' }});
              f.append(probe); const c = getComputedStyle(probe).color; probe.remove();
              return [f.getBoundingClientRect().left - v.getBoundingClientRect().left,
                      s.borderLeftWidth + ' ' + s.borderLeftColor, '3px ' + c]; }}""")
        self.assertEqual(gap, 0)
        self.assertEqual(stripe, want)

    def test_added(self) -> None:
        """R-1 — Az új kép egyedül, balra, zöld bal csíkkal."""
        self.added_or_deleted("uj.png", "img-add img-whole", "--add")

    def test_deleted(self) -> None:
        """R-1 — A törölt kép egyedül, balra, piros bal csíkkal."""
        self.added_or_deleted("torolt.png", "img-del img-whole", "--del")

    def test_changed_pair(self) -> None:
        """R-1 — A változott pár a középvonalon találkozik: a régi piros, az új zöld kerettel."""
        self.resize(1400)
        self.open_file("logo.png")
        self.assertEqual(self.figs(), [["img-del", True], ["img-add", True]])
        edges = self.page.locator(".img-view").evaluate(EDGES)
        self.assertTrue(all(0 <= e <= 4 for e in edges), edges)
        widths = self.page.locator(".img-fig").evaluate_all("fs => fs.map(f => getComputedStyle(f).borderTopWidth)")
        self.assertEqual(widths, ["2px", "2px"])

    def test_pair_breaks(self) -> None:
        """R-1 — Ha a pár nem fér el egymás mellett, egymás alá kerül, mindkettő balra, a régi az első."""
        self.resize(900)
        self.open_file("wide.png")
        self.figs()
        pos = self.page.locator(".img-view").evaluate(
            "v => [...v.querySelectorAll('.img-fig')].map(f => [Math.round(f.getBoundingClientRect().left"
            " - v.getBoundingClientRect().left), f.getBoundingClientRect().top, f.className])")
        (left_a, top_a, cls_a), (left_b, top_b, cls_b) = pos
        self.assertEqual((left_a, left_b), (0, 0))
        self.assertLess(top_a, top_b)
        self.assertIn("img-del", cls_a)
        # szélesen újra egymás mellett
        self.resize(1600)
        tops = self.page.locator(".img-fig").evaluate_all("fs => fs.map(f => f.getBoundingClientRect().top)")
        self.assertEqual(tops[0], tops[1])

    def test_renamed_unchanged(self) -> None:
        """R-1 — Az átnevezett, változatlan kép egyszer, semleges kerettel."""
        self.open_file("uj-nev.png")
        self.assertEqual(self.figs(), [["", True]])

    def test_look(self) -> None:
        """R-2 — Sakktábla a kép mögött (sötét témában is), természetes méret."""
        self.page.emulate_media(color_scheme="dark")
        self.open_file("atlatszo.png")
        self.figs()
        bg, width = self.page.locator(".img-fig img").evaluate(
            "i => [getComputedStyle(i).backgroundImage, i.getBoundingClientRect().width]")
        self.assertIn("conic-gradient", bg)
        self.assertEqual(width, 40)                       # a keskeny kép nem nő

    def test_too_big(self) -> None:
        """R-2 — A túl nagy kép helyén a mérete."""
        self.open_file("photo.jpg")
        self.page.wait_for_selector(".img-big")
        self.assertEqual(self.page.locator(".img-big").inner_text(), "Túl nagy kép (2,4 MB).")

    def test_wide_image_shrinks(self) -> None:
        """R-2 — A hasábnál szélesebb kép a hasáb szélességére kicsinyedik."""
        self.resize(500)
        self.open_file("wide.png")
        self.figs()
        over = self.page.locator(".img-view").evaluate(
            "v => [...v.querySelectorAll('img')].map(i => i.getBoundingClientRect().right - v.getBoundingClientRect().right)")
        self.assertTrue(all(o <= 0 for o in over), over)

    def test_svg_toggle(self) -> None:
        """R-3 — Az SVG alapból kép (a pár elrendezésében), a gombbal a szöveges diff."""
        self.open_file("icon.svg")
        self.assertEqual(self.figs(), [["img-del", True], ["img-add", True]])
        self.page.locator(".diff [data-svg-mode]").click()
        self.page.wait_for_selector(".diff .diff-line")
        self.assertEqual(self.page.locator(".diff .img-fig").count(), 0)
        self.assertIn("blue", self.page.locator(".diff:has([data-svg-mode])").inner_text())
        self.page.locator(".diff [data-svg-mode]").click()                 # vissza: a lap megjegyzi
        self.page.wait_for_selector(".diff .img-fig")

    def test_markdown_images(self) -> None:
        """R-4 — A markdown-kép oldalanként a saját változatából; a szövegbeli a helyén; a hiányzó
        alt szöveggel, `nem található` jelöléssel; a külső alt szöveg marad."""
        self.open_file("README.md")
        self.page.wait_for_selector(".md-doc img.md-inl")
        self.settle()
        pic = self.page.locator(".diff-uni .md-pic").first
        self.assertEqual(pic.locator(".img-fig").evaluate_all(FIGS), [["img-del", True], ["img-add", True]])
        old, new = pic.locator("img").evaluate_all("is => is.map(i => i.src)")
        self.assertNotEqual(old, new)                      # a szülő és a commit képe
        inline = self.page.locator(".diff-uni img.md-inl").first.evaluate(
            "i => [getComputedStyle(i).float, i.closest('p') !== null, i.alt]")
        self.assertEqual(inline, ["none", True, "pont"])
        self.assertIn("badge", self.page.locator(".diff-uni .md-img:not([data-img])").all_inner_texts())
        missing = self.page.locator(".diff-uni .md-pic").nth(1)
        self.assertEqual(missing.locator(".img-fig").first.inner_text(), "hiány nem található")

    def test_markdown_split(self) -> None:
        """R-4 — Side-by-side-ban a csak képből álló bekezdés egyszer, a teljes szélességen."""
        self.resize(1400)
        self.open_file("README.md")
        self.page.wait_for_selector(".diff-split .md-pic img")
        self.settle()
        row = self.page.locator(".diff-split .md-mmd-row .md-pic").first
        self.assertEqual(row.locator(".img-fig").evaluate_all(FIGS), [["img-del", True], ["img-add", True]])
        edges = row.locator(".img-view").evaluate(EDGES)
        self.assertTrue(all(0 <= e <= 4 for e in edges), edges)

    def test_markdown_uncommitted(self) -> None:
        """R-4 — A nem commitolt sorban a régi oldal az index, az új a lemez képe."""
        self.page.locator('.row.uncommitted:has-text("Nem commitolt")').click()
        self.settle()
        self.page.locator(".details .file", has_text="README.md").click()
        self.page.wait_for_selector(".md-doc .md-pic img")
        srcs = self.page.locator(".md-doc .md-pic").first.locator("img").evaluate_all("is => is.map(i => i.src)")
        sides = self.client.call("file_diff", repo="fixture", sha=self.page.locator(
            ".row.uncommitted").first.get_attribute("data-sha"), path="docs/README.md", image="img/graph.png")
        self.assertEqual(srcs, [sides["old"]["uri"], sides["new"]["uri"]])
        self.assertNotEqual(*srcs)


if __name__ == "__main__":
    unittest.main()
