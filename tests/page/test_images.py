"""Képek a diffben (#53, #54): a képfájl és a markdown-kép képként, a Mermaid-diagramok páros
elrendezésében; új / törölt kép bal csíkkal, a változott pár színes kerettel, sakktábla, a
túl nagy kép mérete, az SVG kódnézete, és a markdown-kép oldalanként a saját változatából.
A kép a panelbe illeszkedik; a változott pár Side-by-side, Swipe és Onion skin nézetben
összevethető, nagyítható, teljes lapos nézetben is; a bináris fájl sora a méretét mutatja."""
from __future__ import annotations

import os
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
TALL_MD = "# Magas\n\n![magas](img/magas.png)\n\n{}\n"
BIG_PNG = png(20, 20, RED)[:-12] + b"\0" * int(3.5 * 1048576) + png(20, 20, RED)[-12:]


def noise_png(width: int, height: int) -> bytes:
    """Véletlen pixelű, tömöríthetetlen PNG: a mérete ~szélesség × magasság × 4 bájt."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    raw = b"".join(b"\0" + os.urandom(width * 4) for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 0)) + chunk(b"IEND", b""))

# a figurák: [osztály a `img-fig` nélkül, van-e képe]
FIGS = "fs => fs.map(f => [f.className.replace('img-fig', '').trim(), !!f.querySelector('img')])"
# a nézet közepe és a két keret széle: [a régi jobb széle a középtől, az új bal széle a középtől]
EDGES = ("v => { const r = v.getBoundingClientRect(), [a, b] = [...v.querySelectorAll('.img-fig')]"
         ".map(f => f.getBoundingClientRect()); return [r.left + r.width / 2 - a.right, b.left - (r.left + r.width / 2)]; }")


class ImageFixture(PageTestCase):
    SUBJECT = "kép"

    @classmethod
    def prepare(cls, repo: Path) -> None:
        (repo / "docs" / "img").mkdir(parents=True)
        files = {
            "logo.png": (png(300, 240, RED), png(300, 240, BLUE)),
            "tall.png": (None, png(400, 2000, RED)),
            "icon.png": (None, png(16, 16, RED)),
            "screenshot.png": (png(1600, 300, RED), png(1600, 300, BLUE)),
            "grow.png": (png(100, 100, RED), png(200, 150, BLUE)),
            "nagy.png": (BIG_PNG, png(20, 20, BLUE)),
            "docs/img/magas.png": (png(50, 30, RED), png(300, 1500, BLUE)),
            "docs/MAGAS.md": (TALL_MD.format("Régi."), TALL_MD.format("Új.")),
            "uj.png": (None, png(70, 20, (40, 160, 40, 255))),
            "torolt.png": (png(30, 30, RED), None),
            "wide.png": (png(500, 20, RED), png(500, 20, BLUE)),
            "atlatszo.png": (None, png(40, 40, CLEAR)),
            "icon.svg": (SVG_OLD, SVG_NEW),
            "photo.jpg": (None, b"\xff\xd8\xff" + b"\0" * int(3.5 * 1048576)),
            "big.png": (noise_png(790, 790), noise_png(790, 790)),
            "zzz-magas.png": (None, png(400, 2000, BLUE)),
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

    def loaded(self, scope: str = ".diff .img-view") -> None:
        """Kivárja, hogy a nézet képei betöltődjenek és elrendeződjenek."""
        self.page.wait_for_function(f"""(() => {{ const v = document.querySelector('{scope}');
          return v && [...v.querySelectorAll('img')].every(i => i.complete && i.naturalWidth && i.style.width); }})()""")
        self.settle()

    def open_image(self, name: str) -> None:
        self.open_file(name)
        self.loaded()

    def rect(self, sel: str, i: int = 0) -> dict:
        return self.page.locator(sel).nth(i).evaluate(
            "e => { const r = e.getBoundingClientRect(); return {l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height}; }")

    def hover_image(self, sel: str = ".diff .img-pane") -> None:
        box = self.rect(sel)
        self.page.mouse.move(box["l"] + box["w"] / 2, box["t"] + box["h"] / 2)
        self.settle()

    def bar_shown(self, sel: str = ".img-bar") -> bool:
        return self.page.locator(sel).first.evaluate("b => getComputedStyle(b).opacity === '1'")

    def click_bar(self, button: str, scope: str = ".diff") -> None:
        """A sáv egy gombja: előbb a képre mutat (a sáv csak akkor kattintható)."""
        self.hover_image(f"{scope} .img-pane")
        self.page.locator(f"{scope} {button}").first.click()
        self.settle()

    def mode(self, name: str) -> None:
        """Nézetváltás a sávból."""
        self.click_bar(f"[data-img-mode={name}]")

    def pct(self, sel: str = ".diff .img-pct") -> str:
        return self.page.locator(sel).first.inner_text()

    def zoom_in(self, times: int, scope: str = ".diff") -> None:
        for _ in range(times):
            self.click_bar('[data-img-zoom="1"]', scope)


class ImagesTest(ImageFixture):
    def added_or_deleted(self, name: str, kind: str, color: str) -> None:
        self.open_file(name)
        self.assertEqual(self.figs(), [[kind, True]])
        gap, stripe, want = self.page.locator(".diff .img-view").evaluate(
            f"""v => {{ const f = v.querySelector('.img-fig'), s = getComputedStyle(f);
              const probe = Object.assign(document.createElement('i'), {{ style: 'color: var({color})' }});
              f.append(probe); const c = getComputedStyle(probe).color; probe.remove();
              const r = f.getBoundingClientRect(), w = v.getBoundingClientRect();
              return [(r.left + r.width / 2) - (w.left + w.width / 2),
                      s.borderLeftWidth + ' ' + s.borderLeftColor, '3px ' + c]; }}""")
        self.assertLessEqual(abs(gap), 1)                 # középen (#54)
        self.assertEqual(stripe, want)

    def test_added(self) -> None:
        """R-1 — Az új kép egyedül, középen, zöld bal csíkkal."""
        self.added_or_deleted("uj.png", "img-add img-whole", "--add")

    def test_deleted(self) -> None:
        """R-1 — A törölt kép egyedül, középen, piros bal csíkkal."""
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
        self.assertEqual(self.page.locator(".img-big").inner_text(), "Túl nagy kép (3,5 MB).")

    def test_big_image(self) -> None:
        """A limit alatti nagy kép (~2,4 MB) mindkét oldala megjelenik."""
        self.open_image("big.png")
        self.assertEqual(self.figs(), [["img-del", True], ["img-add", True]])
        sizes = self.page.locator(".diff .img-view img").evaluate_all("is => is.map(i => i.naturalWidth)")
        self.assertEqual(sizes, [790, 790])

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
        self.page.locator('.diff [data-svg-mode="code"]').click()
        self.page.wait_for_selector(".diff .diff-line")
        self.assertEqual(self.page.locator(".diff .img-fig").count(), 0)
        self.assertIn("blue", self.page.locator(".diff:has([data-svg-mode])").inner_text())
        self.page.locator('.diff [data-svg-mode="image"]').click()         # vissza: a lap megjegyzi
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
        sha = self.page.locator(".row.uncommitted").first.get_attribute("data-sha")
        sides = [self.client.call("file_diff", repo="fixture", sha=sha, path="docs/README.md", image="img/graph.png",
                                  side=side) for side in ("old", "new")]
        self.assertEqual(srcs, [sides[0]["uri"], sides[1]["uri"]])
        self.assertNotEqual(*srcs)


class FitTest(ImageFixture):
    """A kép legfeljebb természetes méretben jelenik meg, és a hasáb szélességébe és a panel
    látható magasságába illeszkedik."""

    def fits(self) -> None:
        panel, file = self.rect(".details"), self.rect(".details .file[aria-expanded=true]")
        for i in range(self.page.locator(".diff .img-view img").count()):
            img = self.rect(".diff .img-view img", i)
            self.assertLessEqual(img["h"], panel["h"] - file["h"], img)

    def test_tall(self) -> None:
        """Magas kép: arányosan kicsinyedik; a fájlsor, a teljes diff-doboz és a következő fájl
        sora görgetés nélkül látszik."""
        self.open_image("tall.png")
        img, panel, file = self.rect(".diff img"), self.rect(".details"), self.rect(".details .file[aria-expanded=true]")
        self.assertLess(img["h"], 2000)
        self.assertAlmostEqual(img["w"] / img["h"], 0.2, delta=0.01)
        self.assertGreaterEqual(file["t"], panel["t"] - 1)
        box = self.rect(".diff:not([hidden])")
        after = self.page.locator(".details .file[aria-expanded=true] + .diff + .file").evaluate(
            "f => f.getBoundingClientRect().bottom")
        self.assertLessEqual(box["b"], panel["b"] + 1)
        self.assertLessEqual(after, panel["b"] + 1)

    def test_tall_last(self) -> None:
        """Magas kép az utolsó fájlban: a panel aljáig nőhet, a diff-doboz teljesen látszik."""
        self.open_image("zzz-magas.png")
        panel, box = self.rect(".details"), self.rect(".diff:not([hidden])")
        self.assertLessEqual(box["b"], panel["b"] + 1)
        self.assertGreater(box["b"], panel["b"] - 30)

    def test_small(self) -> None:
        """Kis kép: 16×16 px-es marad."""
        self.open_image("icon.png")
        img = self.rect(".diff img")
        self.assertEqual((img["w"], img["h"]), (16, 16))

    def test_panel_resize(self) -> None:
        """A panel átméreteződik: a kép újra illeszkedik az új magasságba."""
        self.open_image("tall.png")
        before = self.rect(".diff img")["h"]
        self.page.set_viewport_size({"width": self.WIDTH, "height": 500})
        self.settle()
        after = self.rect(".diff img")["h"]
        self.assertLess(after, before)
        self.fits()

    def test_markdown_pair(self) -> None:
        """Markdown-képpár: a két kép ugyanígy illeszkedik a szélességbe és a panel magasságába."""
        self.open_file("MAGAS.md")
        self.page.wait_for_selector(".diff .md-pic .img-view img")
        self.loaded(".diff .md-pic .img-view")
        view = self.rect(".diff .md-pic .img-view")
        self.assertEqual(self.page.locator(".diff .md-pic .img-view").first.locator("img").count(), 2)
        for i in range(2):
            self.assertLessEqual(self.rect(".diff .md-pic .img-view img", i)["w"], view["w"] / 2)
        panel, file = self.rect(".details"), self.rect(".details .file[aria-expanded=true]")
        self.assertLessEqual(self.rect(".diff .md-pic .img-view img", 1)["h"], panel["h"] - file["h"])


class CenterTest(ImageFixture):
    """A képfájl diffjében a kép középen áll; a markdown-nézet képei a helyükön maradnak."""

    def centered(self, i: int = 0) -> None:
        fig, view = self.rect(".diff:not([hidden]) .img-view > .img-half > .img-fig", i), self.rect(".diff:not([hidden]) .img-view")
        self.assertAlmostEqual(fig["l"] + fig["w"] / 2, view["l"] + view["w"] / 2, delta=1)

    def test_single(self) -> None:
        """Egy kép (új, törölt, változatlan) és a fedő nézet: vízszintesen középen."""
        for name in ("uj.png", "torolt.png", "uj-nev.png"):
            with self.subTest(name):
                self.open_image(name)
                self.centered()
                self.page.locator(".details .file", has_text=name).click()
                self.settle()
        self.open_image("logo.png")
        for name in ("swipe", "onion"):
            self.mode(name)
            self.centered()

    def test_markdown(self) -> None:
        """A markdown-nézet egyedül álló képe a szöveg bal szélénél marad (a pár a középvonalon, mint eddig)."""
        self.open_file("README.md")
        self.page.wait_for_selector(".diff-uni .md-pic .img-fig")
        self.settle()
        view = self.rect(".diff-uni .md-pic >> nth=1")
        self.assertAlmostEqual(self.rect(".diff-uni .md-pic >> nth=1 >> .img-fig")["l"], view["l"], delta=20)
        self.assertLess(self.rect(".diff-uni .md-pic >> nth=1 >> .img-fig")["l"], view["l"] + view["w"] / 4)


class SideBySideTest(ImageFixture):
    """A változott pár Side-by-side nézetben mindig egymás mellett áll, a félhasábba illesztve."""

    def test_wide_pair(self) -> None:
        """Széles pár: a két kép egymás mellett, mindkettő a fél hasábszélességre kicsinyítve."""
        self.open_image("screenshot.png")
        view = self.rect(".diff .img-view")
        old, new = self.rect(".diff .img-view img", 0), self.rect(".diff .img-view img", 1)
        self.assertEqual(old["t"], new["t"])
        self.assertLess(old["r"], new["l"])
        for img in (old, new):
            self.assertLess(img["w"], 1600)
            self.assertLessEqual(img["w"], view["w"] / 2)
            self.assertGreater(img["w"], view["w"] / 2 - 30)


class SwipeTest(ImageFixture):
    """A változott pár Swipe nézetben a választóvonalnál vált a régi és az új között."""

    def clips(self) -> list:
        return self.page.locator(".diff .img-view > .img-half").evaluate_all(
            "hs => hs.map(h => getComputedStyle(h).clipPath)")

    def test_start(self) -> None:
        """Kezdőállás: a két kép egymást fedi, a vonal 0%-on, csak az új kép látszik."""
        self.open_image("logo.png")
        self.mode("swipe")
        old, new = self.rect(".diff .img-view img", 0), self.rect(".diff .img-view img", 1)
        self.assertEqual((old["l"], old["t"]), (new["l"], new["t"]))
        fig = self.rect(".diff .img-fig")
        self.assertAlmostEqual(self.rect(".diff .img-line")["l"] + self.rect(".diff .img-line")["w"] / 2, fig["l"], delta=1)
        self.assertEqual(self.clips(), ["inset(0px 100% 0px 0px)", "inset(0px 0px 0px 0%)"])

    def test_drag(self) -> None:
        """Húzás: a vonal 40%-on — a bal 40%-on a régi, a többin az új kép."""
        self.open_image("logo.png")
        self.mode("swipe")
        line, fig = self.rect(".diff .img-line"), self.rect(".diff .img-fig")
        self.page.mouse.move(line["l"] + line["w"] / 2, fig["t"] + fig["h"] / 2)
        self.page.mouse.down()
        self.page.mouse.move(fig["l"] + fig["w"] * 0.4, fig["t"] + fig["h"] / 2, steps=5)
        self.page.mouse.up()
        self.settle()
        self.assertEqual(self.clips(), ["inset(0px 60% 0px 0px)", "inset(0px 0px 0px 40%)"])

    def test_click(self) -> None:
        """Kattintás a képre: a vonal oda ugrik."""
        self.open_image("logo.png")
        self.mode("swipe")
        fig = self.rect(".diff .img-fig")
        self.page.mouse.click(fig["l"] + fig["w"] * 0.7, fig["t"] + fig["h"] / 3)
        self.settle()
        line = self.rect(".diff .img-line")
        self.assertAlmostEqual(line["l"] + line["w"] / 2, fig["l"] + fig["w"] * 0.7, delta=1.5)


    def cursor(self, sel: str) -> str:
        return self.page.locator(sel).first.evaluate("e => getComputedStyle(e).cursor")

    def test_cursor(self) -> None:
        """Kurzor: nagyítatlan képen és húzás közben végig ew-resize; nagyítva a kép grab."""
        self.open_image("logo.png")
        self.mode("swipe")
        self.assertEqual(self.cursor(".diff .img-pane >> nth=1"), "ew-resize")
        line, fig = self.rect(".diff .img-line"), self.rect(".diff .img-fig")
        self.page.mouse.move(line["l"] + line["w"] / 2, fig["t"] + fig["h"] / 2)
        self.page.mouse.down()
        self.page.mouse.move(fig["r"] + 60, fig["b"] + 30, steps=4)          # a képen kívülre is
        self.assertEqual(self.page.evaluate("getComputedStyle(document.elementFromPoint("
                                            f"{fig['r'] + 60}, {fig['b'] + 30})).cursor"), "ew-resize")
        self.page.mouse.up()
        self.settle()
        self.assertNotEqual(self.page.evaluate("getComputedStyle(document.body).cursor"), "ew-resize")
        self.zoom_in(1)
        self.assertEqual(self.cursor(".diff .img-pane >> nth=1"), "grab")
        self.assertEqual(self.cursor(".diff .img-line"), "ew-resize")


class OnionTest(ImageFixture):
    """A változott pár Onion skin nézetben áttetszőséggel vált a régi és az új között."""

    def opacities(self) -> list:
        return self.page.locator(".diff .img-view > .img-half").evaluate_all(
            "hs => hs.map(h => getComputedStyle(h).opacity)")

    def test_start(self) -> None:
        """Kezdőállás: a csúszka 100%-on, csak az új kép látszik."""
        self.open_image("logo.png")
        self.mode("onion")
        self.assertEqual(self.page.locator(".diff .img-opacity").input_value(), "100")
        self.assertEqual(self.opacities(), ["0", "1"])

    def test_slider(self) -> None:
        """A csúszka 0%-on: csak a régi kép látszik."""
        self.open_image("logo.png")
        self.mode("onion")
        self.page.locator(".diff .img-opacity").evaluate(
            "r => { r.value = 0; r.dispatchEvent(new Event('input', { bubbles: true })); }")
        self.settle()
        self.assertEqual(self.opacities(), ["1", "0"])


class OverlayAlignTest(ImageFixture):
    """Swipe és Onion skin nézetben az eltérő méretű pár középre igazítva fedi egymást."""

    def test_grown(self) -> None:
        """Megnőtt kép: természetes arányban, egymás közepéhez igazítva."""
        self.open_image("grow.png")
        for name in ("swipe", "onion"):
            with self.subTest(name):
                self.mode(name)
                old, new = self.rect(".diff .img-view img", 0), self.rect(".diff .img-view img", 1)
                self.assertEqual((old["w"], old["h"], new["w"], new["h"]), (100, 100, 200, 150))
                self.assertAlmostEqual(old["l"] + old["w"] / 2, new["l"] + new["w"] / 2, delta=0.5)
                self.assertAlmostEqual(old["t"] + old["h"] / 2, new["t"] + new["h"] / 2, delta=0.5)


class ModeMemoryTest(ImageFixture):
    """A választott nézetet a lap egy közös beállításként jegyzi meg."""

    def test_other_pair(self) -> None:
        """Másik pár nyitása: az is Onion skin nézetben nyílik — a markdown-képpár is."""
        self.open_image("logo.png")
        self.mode("onion")
        self.page.locator(".details .file", has_text="logo.png").click()
        self.open_file("screenshot.png")
        self.loaded(".diff:not([hidden]) .img-view")
        self.assertEqual(self.page.locator(".diff:not([hidden]) .img-view").get_attribute("data-mode"), "onion")
        self.open_file("MAGAS.md")
        self.loaded(".diff:not([hidden]) .md-pic .img-view")
        self.assertEqual(self.page.locator(".diff:not([hidden]) .md-pic .img-view").first.get_attribute("data-mode"), "onion")

    def test_reload(self) -> None:
        """Újratöltés után a következő pár Swipe nézetben nyílik."""
        self.open_image("logo.png")
        self.mode("swipe")
        self.page.reload()
        self.page.wait_for_selector("#rows .row")
        self.settle()
        self.open_image("screenshot.png")
        self.assertEqual(self.page.locator(".diff .img-view").get_attribute("data-mode"), "swipe")


class BarTest(ImageFixture):
    """A kép alján rámutatásra lebegő sáv, a képet takarja; a 200 px-nél alacsonyabb képnél a
    kép alatt lebeg, ha ott elfér."""

    def buttons(self) -> list:
        return self.page.locator(".diff .img-bar").first.evaluate(
            "b => [...b.querySelectorAll('button, input')].filter(e => getComputedStyle(e).display !== 'none')"
            ".map(e => e.dataset.imgMode || (e.dataset.imgZoom ? 'zoom' + e.dataset.imgZoom : '')"
            " || ('imgFull' in e.dataset ? 'full' : e.className))")

    def test_pair(self) -> None:
        """Változott pár: a kép alján, középen a sáv — nézetek, zoom, teljes lap —, a kép nem mozdul."""
        self.open_image("logo.png")
        before = self.rect(".diff .img-view img", 1)
        self.assertFalse(self.bar_shown())
        self.hover_image(".diff .img-pane >> nth=1")
        self.assertTrue(self.bar_shown())
        self.assertEqual(self.buttons(), ["sbs", "swipe", "onion", "zoom-1", "zoom1", "full"])
        bar, view = self.rect(".diff .img-bar"), self.rect(".diff .img-view")
        fig = self.rect(".diff .img-fig", 1)
        self.assertAlmostEqual(bar["l"] + bar["w"] / 2, view["l"] + view["w"] / 2, delta=2)
        self.assertAlmostEqual(bar["b"], fig["b"] - 12, delta=1)
        self.assertEqual(self.rect(".diff .img-view img", 1), before)

    def test_titles(self) -> None:
        """Súgó: a gombok súgójában a teljes lapos nézet billentyűje is áll."""
        self.open_image("logo.png")
        titles = self.page.locator(".diff .img-bar button").evaluate_all(
            "bs => bs.map(b => b.dataset.tip + (b.dataset.kbd ? ` (${b.dataset.kbd})` : ''))")
        self.assertEqual(titles, ["Side-by-side (2)", "Swipe (S)", "Onion skin (O)", "Kicsinyítés (−)",
                                  "Nagyítás (+)", "Teljes lapos nézet", "Bezárás (Esc)"])

    def test_low(self) -> None:
        """Alacsony kép: a sáv a kép alatt lebeg, nem takarja, a kép nem mozdul."""
        self.open_image("icon.png")
        before = self.rect(".diff img")
        self.hover_image()
        self.assertTrue(self.bar_shown())
        self.assertGreaterEqual(self.rect(".diff .img-bar")["t"], self.rect(".diff .img-fig")["b"])
        self.assertEqual(self.rect(".diff img"), before)

    def test_low_no_room(self) -> None:
        """Alacsony kép a panel alján: a sáv a kép alján, a képet takarva."""
        self.open_image("icon.png")
        # a panel alja közvetlenül a kép alatt (mint egy alacsony ablakban)
        self.page.locator(".details").evaluate(
            "p => { p.style.maxHeight = `${p.querySelector('.diff .img-fig').getBoundingClientRect().bottom"
            " - p.getBoundingClientRect().top + 4}px`; }")
        self.settle()
        fig = self.rect(".diff .img-fig")
        self.assertLessEqual(fig["b"], self.rect(".details")["b"])
        self.hover_image()
        self.assertTrue(self.bar_shown())
        self.assertLessEqual(self.rect(".diff .img-bar")["b"], fig["b"])

    def test_onion(self) -> None:
        """Onion skin nézetben a sávban az áttetszőség csúszkája is."""
        self.open_image("logo.png")
        self.mode("onion")
        self.hover_image()
        self.assertIn("img-opacity", self.buttons())

    def test_leave(self) -> None:
        """Ha az egér elhagyja a képet, a sáv eltűnik."""
        self.open_image("logo.png")
        self.hover_image()
        self.assertTrue(self.bar_shown())
        self.page.mouse.move(2, 2)
        self.settle()
        self.assertFalse(self.bar_shown())

    def test_one_sided(self) -> None:
        """Egyoldalú kép: csak a zoom és a teljes lapos nézet gombja."""
        for name in ("uj.png", "torolt.png"):
            with self.subTest(name):
                self.open_image(name)
                self.hover_image()
                self.assertEqual(self.buttons(), ["zoom-1", "zoom1", "full"])
                self.page.locator(".details .file", has_text=name).click()
                self.settle()

    def test_too_big_side(self) -> None:
        """Az egyik oldal túl nagy: nincs nézetgomb, a pár Side-by-side."""
        self.open_file("nagy.png")
        self.page.wait_for_selector(".diff .img-big")
        self.loaded()
        self.hover_image()
        self.assertEqual(self.buttons(), ["zoom-1", "zoom1", "full"])
        self.assertEqual(self.page.locator(".diff .img-view").get_attribute("data-mode"), "sbs")
        self.assertEqual(self.page.locator(".diff .img-view > .img-half").count(), 2)

    def test_inline_markdown(self) -> None:
        """Szövegbeli markdown-kép: ugyanez a sáv, nézetgombok nélkül."""
        self.open_file("README.md")
        self.page.wait_for_selector(".diff-uni img.md-inl")
        self.loaded(".diff-uni .img-inline")
        self.hover_image(".diff-uni .img-inline .img-pane")
        self.assertTrue(self.bar_shown(".diff-uni .img-inline .img-bar"))
        btns = self.page.locator(".diff-uni .img-inline .img-bar [data-img-mode]")
        self.assertEqual(btns.count(), 0)


class ZoomTest(ImageFixture):
    """A kép nagyítható: 100% fölött élesen, pixelesen, legfeljebb 1600%-ig."""

    def rendering(self, sel: str = ".diff .img-view img") -> str:
        return self.page.locator(sel).first.evaluate("i => getComputedStyle(i).imageRendering")

    def test_bar_zoom(self) -> None:
        """Nagyítás a sáv + gombjával 800%-ra: a pixelek élesek; a kép a keretében mozgatható."""
        self.open_image("icon.png")
        self.zoom_in(3)
        self.assertEqual(self.pct(), "800%")
        self.assertEqual(self.rect(".diff img")["w"], 128)
        self.assertEqual(self.rendering(), "pixelated")

    def test_svg(self) -> None:
        """SVG nagyítása: vektorosan, simítva rajzolódik, nem pixelesen."""
        self.open_image("icon.svg")
        self.zoom_in(3)
        self.assertEqual(self.pct(), "800%")
        self.assertEqual(self.rect(".diff .img-view img", 1)["w"], 320)
        self.assertNotEqual(self.rendering(".diff .img-view img >> nth=1"), "pixelated")

    def test_zoom_stays_visible(self) -> None:
        """A panelben elférő kis kép nagyításkor nő: a panel utána görget, a diff-doboz alja és a
        fájlsor is látszik."""
        self.open_image("icon.png")
        self.zoom_in(6)
        panel, box = self.rect(".details"), self.rect(".diff:not([hidden])")
        file = self.rect(".details .file[aria-expanded=true]")
        self.assertGreater(box["h"], 256)
        self.assertLessEqual(box["b"], panel["b"] + 1)
        self.assertGreaterEqual(file["t"], panel["t"] - 1)

    def test_zoom_fills_panel(self) -> None:
        """A panel magasságáig nőtt nagyított kép: felül a saját fájlsora, alul a diff-doboz és
        a következő fájl sora látszik."""
        self.open_image("logo.png")
        self.zoom_in(2)
        panel = self.rect(".details")
        file = self.rect(".details .file[aria-expanded=true]")
        after = self.page.locator(".details .file[aria-expanded=true] + .diff + .file").evaluate(
            "f => f.getBoundingClientRect().bottom")
        self.assertLessEqual(after, panel["b"] + 1)
        self.assertGreaterEqual(file["t"], panel["t"] - 1)
        self.assertLess(file["t"] - panel["t"], 4)         # fölötte nem látszik másik fájl

    def test_limit(self) -> None:
        """Felső határ: 1600% fölé nem nagyít."""
        self.open_image("icon.png")
        self.zoom_in(6)
        self.assertEqual(self.pct(), "1600%")

    def test_drag(self) -> None:
        """Húzás a diffben: nagyított képen a kivágás a húzással mozog."""
        self.open_image("logo.png")
        self.zoom_in(2)
        pane = self.rect(".diff .img-pane >> nth=1")
        x, y = pane["l"] + pane["w"] / 2, pane["t"] + pane["h"] / 2
        img = self.rect(".diff .img-view img", 1)
        self.page.mouse.move(x, y)
        self.page.mouse.down()
        self.page.mouse.move(x + 30, y + 20, steps=4)
        self.page.mouse.up()
        self.settle()
        moved = self.rect(".diff .img-view img", 1)
        self.assertAlmostEqual(moved["l"] - img["l"], 30, delta=1)
        self.assertAlmostEqual(moved["t"] - img["t"], 20, delta=1)

    def test_ctrl_wheel(self) -> None:
        """⌘/Ctrl+görgő a diffben: a lap nem nagyít (az app elkapja)."""
        self.open_image("icon.png")
        self.hover_image()
        self.page.keyboard.down("Control")
        self.page.mouse.wheel(0, -200)
        self.page.keyboard.up("Control")
        self.settle()
        self.assertEqual(self.pct(), "100%")

    def test_plain_wheel(self) -> None:
        """Sima görgő a képen: a panel görget, a nagyítás nem változik."""
        self.open_image("icon.png")
        self.zoom_in(2)
        top = self.page.locator(".details").evaluate("p => p.scrollTop")
        self.hover_image()
        self.page.mouse.wheel(0, 120)
        self.settle()
        self.assertEqual(self.pct(), "400%")
        self.assertNotEqual(self.page.locator(".details").evaluate("p => p.scrollTop"), top)

    def test_pair_sync(self) -> None:
        """Egymás melletti pár: a másik oldal ugyanakkora nagyítással, ugyanazt a kivágást mutatja."""
        self.open_image("logo.png")
        self.zoom_in(2)
        pane = self.rect(".diff .img-pane >> nth=0")
        self.page.mouse.move(pane["l"] + 40, pane["t"] + 40)
        self.page.mouse.down()
        self.page.mouse.move(pane["l"] + 10, pane["t"] + 20, steps=4)
        self.page.mouse.up()
        self.settle()
        a, b = self.rect(".diff .img-view img", 0), self.rect(".diff .img-view img", 1)
        pa, pb = self.rect(".diff .img-pane >> nth=0"), self.rect(".diff .img-pane >> nth=1")
        self.assertEqual((a["w"], a["h"]), (b["w"], b["h"]))
        self.assertAlmostEqual(a["l"] - pa["l"], b["l"] - pb["l"], delta=0.5)
        self.assertAlmostEqual(a["t"] - pa["t"], b["t"] - pb["t"], delta=0.5)
        self.assertNotEqual(a["l"], pa["l"])

    def center(self) -> tuple:
        """A pane közepén álló képpont, a kép arányában (az új oldalon)."""
        img, pane = self.rect(".diff .img-view img", 1), self.rect(".diff .img-pane >> nth=-1")
        return ((pane["l"] + pane["w"] / 2 - img["l"]) / img["w"], (pane["t"] + pane["h"] / 2 - img["t"]) / img["h"])

    def test_mode_switch_keeps_zoom(self) -> None:
        """Nézetváltás nagyított képen: a nagyítás és a kivágás megmarad."""
        self.open_image("logo.png")
        self.zoom_in(2)
        self.assertEqual(self.pct(), "400%")
        pane = self.rect(".diff .img-pane >> nth=1")
        self.page.mouse.move(pane["l"] + 50, pane["t"] + 50)
        self.page.mouse.down()
        self.page.mouse.move(pane["l"] + 90, pane["t"] + 70, steps=4)
        self.page.mouse.up()
        self.settle()
        before = self.center()
        self.mode("swipe")
        self.assertEqual(self.pct(), "400%")
        after = self.center()
        self.assertAlmostEqual(before[0], after[0], delta=0.02)
        self.assertAlmostEqual(before[1], after[1], delta=0.02)

    def test_reopen(self) -> None:
        """Újranyitás: a kép illesztett méretben."""
        self.open_image("logo.png")
        fit = self.rect(".diff .img-view img", 1)
        self.zoom_in(2)
        self.page.locator(".details .file", has_text="logo.png").click()
        self.settle()
        self.page.locator(".details .file", has_text="logo.png").click()
        self.loaded()
        self.assertEqual(self.rect(".diff .img-view img", 1)["w"], fit["w"])


class FullTest(ImageFixture):
    """A teljes lapos nézet a lapot fedi, a sávja mindig látszik, billentyűkkel is kezelhető."""

    def open_full(self) -> None:
        self.open_image("logo.png")
        self.click_bar("[data-img-full]")
        self.loaded(".img-full .img-view")

    def test_open_close(self) -> None:
        """Megnyitás ugyanabban a nézetben, a sáv rámutatás nélkül is; az Esc és a bezárás gomb bezárja."""
        self.open_image("logo.png")
        self.mode("swipe")
        self.click_bar("[data-img-full]")
        self.loaded(".img-full .img-view")
        full = self.rect(".img-full")
        self.assertEqual((full["l"], full["t"], full["w"], full["h"]), (0, 0, self.WIDTH, self.HEIGHT))
        self.assertEqual(self.page.locator(".img-full .img-view").get_attribute("data-mode"), "swipe")
        self.page.mouse.move(2, 2)
        self.settle()
        self.assertTrue(self.bar_shown(".img-full .img-bar"))
        self.page.keyboard.press("Escape")
        self.settle()
        self.assertEqual(self.page.locator(".img-full").count(), 0)
        self.assertEqual(self.page.locator("#rows .details").count(), 1)   # az Esc a commitot nem csukja
        self.page.locator(".diff [data-img-full]").evaluate("b => b.click()")
        self.loaded(".img-full .img-view")
        self.page.locator(".img-full [data-img-close]").click()
        self.settle()
        self.assertEqual(self.page.locator(".img-full").count(), 0)

    def test_wheel(self) -> None:
        """Görgő a teljes lapos nézetben: a mutató körül nagyít."""
        self.open_full()
        pane = self.rect(".img-full .img-pane >> nth=1")
        x, y = pane["l"] + pane["w"] * 0.25, pane["t"] + pane["h"] * 0.25
        img = self.rect(".img-full .img-view img", 1)
        u = ((x - img["l"]) / img["w"], (y - img["t"]) / img["h"])
        self.page.mouse.move(x, y)
        self.page.mouse.wheel(0, -400)
        self.settle()
        self.assertGreater(int(self.pct(".img-full .img-pct").rstrip("%")), 100)
        img = self.rect(".img-full .img-view img", 1)
        self.assertAlmostEqual((x - img["l"]) / img["w"], u[0], delta=0.02)
        self.assertAlmostEqual((y - img["t"]) / img["h"], u[1], delta=0.02)

    def test_keys(self) -> None:
        """Billentyűk: + − 0 1 2 S O, → 10%, Shift+→ 1%; a W semmit nem tesz."""
        self.open_full()
        sel = ".img-full .img-pct"
        start = int(self.pct(sel).rstrip("%"))
        self.page.keyboard.press("+")
        self.assertGreater(int(self.pct(sel).rstrip("%")), start)
        self.page.keyboard.press("+")
        big = int(self.pct(sel).rstrip("%"))
        self.page.keyboard.press("-")
        self.assertLess(int(self.pct(sel).rstrip("%")), big)
        self.page.keyboard.press("0")
        self.assertEqual(int(self.pct(sel).rstrip("%")), start)
        self.page.keyboard.press("1")
        self.assertEqual(self.pct(sel), "100%")
        view = self.page.locator(".img-full .img-view")
        for key, mode in (("o", "onion"), ("w", "onion"), ("s", "swipe"), ("2", "sbs"), ("S", "swipe")):
            self.page.keyboard.press(key)
            self.assertEqual(view.get_attribute("data-mode"), mode, key)
        clip = "h => getComputedStyle(h).clipPath"
        self.page.keyboard.press("ArrowRight")
        self.assertEqual(self.page.locator(".img-full .img-view > .img-half").first.evaluate(clip), "inset(0px 90% 0px 0px)")
        self.page.keyboard.press("Shift+ArrowRight")
        self.assertEqual(self.page.locator(".img-full .img-view > .img-half").first.evaluate(clip), "inset(0px 89% 0px 0px)")
        self.page.keyboard.press("o")
        self.page.keyboard.press("ArrowLeft")
        self.assertEqual(self.page.locator(".img-full .img-opacity").input_value(), "90")


SIZES = {
    "add.png": (None, b"\0\2" * 6144),
    "del.png": (b"\0\3" * 6144, None),
    "grow.png": (b"\0" * 12390, b"\0\1" * 7116 + b"\0"),
    "shrink.png": (b"\0" * 2000, b"\0\1" * 795),
    "same.png": (b"\0\4" * 250, b"\0\5" * 250),
    "doc.pdf": (None, b"\0" * 3145728),
}


class SizeTest(PageTestCase):
    """A bináris fájl sora a `bin` címke helyett a méretet vagy a méretváltozást mutatja."""
    SUBJECT = "méret"

    @classmethod
    def prepare(cls, repo: Path) -> None:
        for side, msg in ((0, cls.SUBJECT), (1, f"{cls.SUBJECT}: módosítva")):
            for name, versions in SIZES.items():
                if versions[side] is None:
                    (repo / name).unlink(missing_ok=True)
                else:
                    (repo / name).write_bytes(versions[side])
            git_in(repo, "add", "-A")
            git_in(repo, "commit", "-qm", msg)

    def test_labels(self) -> None:
        """Méretfelirat: előjeles különbség, + zöld, − piros, ±0 semleges."""
        self.page.locator("#rows .row", has_text=f"{self.SUBJECT}: módosítva").click()
        self.settle()
        got = self.page.locator(".details .file").evaluate_all(
            """fs => Object.fromEntries(fs.map(f => { const c = f.querySelector('.churn > span');
              return [f.dataset.path, [c.textContent, getComputedStyle(c).color]]; }))""")
        colors = self.page.evaluate("""() => Object.fromEntries(['--add', '--del', '--fg-2'].map(v => {
            const p = Object.assign(document.createElement('i'), { style: `color: var(${v})` });
            document.querySelector('.details').append(p); const c = getComputedStyle(p).color; p.remove(); return [v, c]; }))""")
        want = {"add.png": ("+12,0 KB", "--add"), "del.png": ("−12,0 KB", "--del"), "grow.png": ("+1,8 KB", "--add"),
                "shrink.png": ("−410 B", "--del"), "same.png": ("±0 B", "--fg-2"), "doc.pdf": ("+3,0 MB", "--add")}
        self.assertEqual(got, {k: [t, colors[c]] for k, (t, c) in want.items()})


if __name__ == "__main__":
    unittest.main()
