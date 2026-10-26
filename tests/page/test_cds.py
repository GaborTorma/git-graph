"""A lap a Claude app design-systemjével (CDS): tokenek, méretek, sávszínek, chipek, git- és
állapot-színek, lenyitás, nézetváltók, tooltip, monogram, keresési kiemelés (#55)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from harness import DAY, T0, PageTestCase, git_in
from test_subtree import add_origin

# A `cds` commit két változata (`PageTestCase.open_file`): markdown, kód, SVG.
VERSIONS = {
    "README.md": ("# Cím\n\nRégi bekezdés.\n", "# Cím\n\nÚj bekezdés, más szavakkal.\n"),
    "settings.py": ("DEBUG = False\n", "DEBUG = True\nLEVEL = 2\n"),
    "logo.svg": ('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20" fill="red"/></svg>\n',
                 '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20" fill="blue"/></svg>\n'),
}
FILES_SUBJECT = "fájlok: új, törölt, módosított"


def rgb(hex_color: str, alpha: float | None = None) -> str:
    """`#2a78d6` → `rgb(42, 120, 214)`, a `getComputedStyle` alakja."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgb({r}, {g}, {b})" if alpha is None else f"rgba({r}, {g}, {b}, {alpha})"


TRANSPARENT = "rgba(0, 0, 0, 0)"


def prepare_cds(repo: Path) -> None:
    """A fixture-történet fölé: `origin`, a `dev` (a HEAD, upstreammel, pusholatlan committal) a
    forgatókönyvek commitjaival, és két nem beolvasztott ág (3. sáv)."""
    n = 0

    def git(*args: str) -> None:
        nonlocal n
        n += 1
        date = f"@{T0 + 5 * DAY + n * 60} +0000"      # a fixture napjai után, nem friss
        git_in(repo, *args, env={**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})

    def commit(subject: str, files: dict | None = None, remove: tuple = ()) -> None:
        for name, text in (files or {}).items():
            (repo / name).write_text(text, encoding="utf-8")
        for name in remove:
            (repo / name).unlink()
        git("add", "-A")
        git("commit", "-q", "--allow-empty", "-m", subject)

    add_origin(repo)
    for k, base in enumerate(("main~5", "main~4")):             # két ág régebbről: külön sávok
        git("switch", "-q", "-c", f"kiserlet-{k}", base)
        commit(f"kiserlet-{k}: félbehagyott próba", {f"kiserlet-{k}.txt": "próba\n"})
    git("switch", "-q", "-c", "dev", "main")
    commit(FILES_SUBJECT, {"uj.txt": "új\n", "main-0-1.txt": "módosítva\n"}, remove=("main-0-0.txt",))
    commit("feat(auth): login oldal")
    commit("Merge pull request #42 from teszt/ag")
    commit("cds", {name: v[0] for name, v in VERSIONS.items()})
    commit("cds: módosítva", {name: v[1] for name, v in VERSIONS.items()})
    git("push", "-q", "-u", "origin", "dev")
    commit("dev: pusholatlan munka")


class CdsCase(PageTestCase):
    SUBJECT = "cds"

    @classmethod
    def prepare(cls, repo: Path) -> None:
        prepare_cds(repo)

    def style(self, selector: str, prop: str) -> str:
        return self.page.locator(selector).first.evaluate(f"e => getComputedStyle(e)['{prop}']")

    def token(self, name: str) -> str:
        return self.page.evaluate(f"getComputedStyle(document.documentElement).getPropertyValue('{name}').trim()")

    def box(self, selector: str) -> dict:
        return self.page.locator(selector).first.bounding_box()

    def lane_colors(self) -> dict:
        """A commit-pöttyök (r 4) körvonala sávonként (x → szín), a képernyőn számolva."""
        return self.page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#lanes circle[r="4"]')]
          .map(c => [c.getAttribute('cx'), getComputedStyle(c).stroke]))""")

    def row(self, subject: str):
        return self.page.locator("#rows .row", has_text=subject)

    def open_commit(self, subject: str) -> None:
        self.row(subject).click()
        self.settle()


# ── A színek a CDS-tokenek, témánként ──────────────────────────────────────

class FontTest(CdsCase):
    def test_anthropic_sans(self) -> None:
        """A lap betűje az Anthropic Sans (a kódé az Anthropic Mono): a git-graph adja, a lap
        FontFace-ként regisztrálja, és a sorok szövege ezzel rajzolódik (a szélessége az Anthropic
        Sans-é, nem a tartalék fonté)."""
        for family in ("Anthropic Sans", "Anthropic Mono"):
            self.page.wait_for_function(f"[...document.fonts].some(f => f.family.replace(/\"/g, '') === '{family}'"
                                        " && f.status === 'loaded')")
        width = """f => { const c = document.createElement('canvas').getContext('2d'); c.font = f;
          return c.measureText(document.querySelector('#rows .subject').textContent).width; }"""
        subject = self.page.locator("#rows .subject").first.evaluate("e => e.getBoundingClientRect().width")
        sans = self.page.evaluate(f"({width})('360 14px \"Anthropic Sans\"')")
        fallback = self.page.evaluate(f"({width})('360 14px -apple-system, system-ui, sans-serif')")
        self.assertNotAlmostEqual(sans, fallback, delta=1)
        self.assertAlmostEqual(subject, sans, delta=1)


class FontWeightTest(CdsCase):
    def test_weights(self) -> None:
        """A szöveg vastagsága az app tengelyértékei: törzs 360, kontroll 395, fejléc 480; a monó
        (Anthropic Mono) a környezetéé."""
        weight = lambda sel: self.style(sel, "fontWeight")   # noqa: E731
        self.assertEqual(weight("#rows .subject"), "360")
        self.assertEqual(weight("#branchBtn"), "395")
        self.assertEqual(weight(".repo-name"), "480")
        self.open_file("settings.py")
        self.page.wait_for_selector(".diff .diff-line")
        self.assertEqual(weight(".diff .diff-line"), "360")


class LightTokensTest(CdsCase):
    def test_light_base(self) -> None:
        """Világos téma alapszínei (az app fizzy-lake színtémája): háttér, szöveg, akcentus,
        hover 5 %, kijelölt 10 %."""
        self.assertEqual(self.style("body", "backgroundColor"), rgb("#ffffff"))
        self.assertEqual(self.style("#rows .desc", "color"), rgb("#1a1a1a"))
        self.assertEqual(self.token("--accent"), "#257de0")
        self.assertEqual(self.token("--bg-3"), "#e5e5e5")
        self.row("main-3-2").hover()
        self.settle()
        self.assertEqual(self.row("main-3-2").locator(".row-in").evaluate("e => getComputedStyle(e).backgroundColor"),
                         rgb("#f2f2f2"))


class DarkTokensTest(CdsCase):
    COLOR_SCHEME = "dark"

    def test_dark_base(self) -> None:
        """Sötét téma alapszínei."""
        self.assertEqual(self.style("body", "backgroundColor"), rgb("#191919"))
        self.assertEqual(self.style("#rows .desc", "color"), rgb("#efefef"))
        self.assertEqual(self.token("--accent"), "#257de0")
        self.assertEqual(self.token("--bg-2"), "#2a2a2a")
        self.assertEqual(self.token("--bg-3"), "#3b3b3b")


# ── Méretek: 14 px-es alapszöveg, comfortable kontrollok ──────────────────

class SizesTest(CdsCase):
    def test_sizes(self) -> None:
        """A subject 14, az idő 13, a badge 12 px és 20 magas; a sor 34, a kontroll 32 / 8 px-es
        sarok; a fejléc kapcsolója 36 × 20, a beállítások menüjéé 28 × 16."""
        self.assertEqual(self.style("#rows .subject", "fontSize"), "14px")
        self.assertEqual(self.style("#rows .meta .time", "fontSize"), "13px")
        self.assertEqual(self.style("#rows .badge", "fontSize"), "12px")
        self.assertEqual(self.box("#rows .badge")["height"], 20)
        self.assertEqual(self.box("#rows .row:not(:has(.refs))")["height"], 34)
        for ctrl in (".search", "#branchBtn", "#settingsBtn"):
            self.assertEqual(self.box(ctrl)["height"], 32, ctrl)
            self.assertEqual(self.style(ctrl, "borderTopLeftRadius"), "8px", ctrl)
        track = self.box(".chrome .switch .track")
        self.assertEqual((track["width"], track["height"]), (36, 20))
        self.page.locator("#settingsBtn").click()
        track = self.box(".option.setting .track")
        self.assertEqual((track["width"], track["height"]), (28, 16))


# ── Sávszínek: chart-categorical, témánként ──────────────────────────────

class LaneColorsTest(CdsCase):
    def test_light_lanes(self) -> None:
        """Világos sávok: kék, narancs, aqua."""
        lanes = self.lane_colors()
        self.assertEqual([lanes["16"], lanes["30"], lanes["44"]], [rgb("#2a78d6"), rgb("#eb6834"), rgb("#1baf7a")])

    def test_theme_switch(self) -> None:
        """A téma menüből sötétre váltva az első sáv a sötét kék."""
        self.page.locator("#themeBtn").click()
        self.page.locator('#themePop [data-value="dark"]').click()
        self.settle()
        self.assertEqual(self.lane_colors()["16"], rgb("#3987e5"))
        # a kézzel választott sötét téma tokenjei a rendszer sötétjéével azonosak (a chip kerete is)
        self.assertEqual(self.token("--lane-0-bd"), "#257de066")
        self.assertEqual(self.token("--border"), "rgba(255, 255, 255, .04)")

    def test_system_switch(self) -> None:
        """Automatikus témánál a rendszer sötétre váltása is átszínezi a gráfot."""
        self.page.emulate_media(color_scheme="dark")
        self.settle()
        self.assertEqual(self.lane_colors()["16"], rgb("#3987e5"))


# ── Branch-badge: a sáv tintje, az app Badge-ének alakja ─────────────────

class BadgeTest(CdsCase):
    def test_blue_badge(self) -> None:
        """A `main` badge-e (az első, kék sávon) a kék tint: háttér, szöveg, 1,5 px-es keret; a
        sarka a magasság negyede."""
        main = self.page.locator("#rows .badge.ref-branch", has=self.page.locator(".badge-name", has_text="main"))
        main = main.filter(has_not=self.page.locator(".badge-name", has_text="kiserlet")).first
        css = lambda p: main.evaluate(f"e => getComputedStyle(e)['{p}']")   # noqa: E731
        self.assertEqual(css("backgroundColor"), "rgba(37, 125, 224, 0.12)")
        self.assertEqual(css("color"), rgb("#1757ac"))
        self.assertEqual(css("boxShadow"), "rgba(37, 125, 224, 0.224) 0px 0px 0px 1.5px inset")
        self.assertEqual(float(css("borderTopLeftRadius")[:-2]), main.bounding_box()["height"] / 4)
        self.assertEqual(css("fontWeight"), "520")   # az app font-badge tengelyértéke

    def test_icons(self) -> None:
        """A chip ikonja 16 px, az első a chip szélétől 4 px-re; a worktree-jel és a branch-ikon
        közt 3 px."""
        boxes = self.page.locator("#rows .badge.ref-branch").first.evaluate("""b => {
          const r = b.getBoundingClientRect();
          return [...b.querySelectorAll('svg.ic')].map(i => { const q = i.getBoundingClientRect();
            return [q.left - r.left, q.width, q.height]; }); }""")
        self.assertEqual(boxes[0], [4, 16, 16])

    def test_glyph_icons(self) -> None:
        """Az ikon, aminek van Anthropicons-párja, a glifa: kitöltött kontúr, vonal nélkül."""
        fill, stroke, color = self.page.locator("#rows .badge svg.ic .ic-ag").first.evaluate(
            "e => [getComputedStyle(e).fill, getComputedStyle(e).stroke, getComputedStyle(e.closest('.badge')).color]")
        self.assertEqual((fill, stroke), (color, "none"))


# ── Git-színek ────────────────────────────────────────────────────────────

class DistanceGapTest(CdsCase):
    def test_arrow_gap(self) -> None:
        """A chip távolságában a nyíl és a száma közt 3 px üres tinta, mint a chip két ikonja közt."""
        self.page.wait_for_function("[...document.fonts].some(f => f.family.replace(/\"/g, '') === 'Anthropic Sans'"
                                    " && f.status === 'loaded')")
        self.settle()
        gaps = self.page.locator("#rows .badge .dist .n").evaluate_all("""ns => ns.map(n => {
          const arr = n.querySelector('.arr'), num = arr.nextSibling, cs = getComputedStyle(arr);
          const c = document.createElement('canvas').getContext('2d'); c.font = `${cs.fontWeight} ${cs.fontSize} "Anthropic Sans"`;
          const r = document.createRange(); r.selectNodeContents(num);
          return (r.getBoundingClientRect().left - c.measureText(num.textContent).actualBoundingBoxLeft)
            - (arr.getBoundingClientRect().left + c.measureText(arr.textContent).actualBoundingBoxRight); })""")
        self.assertTrue(gaps)
        for gap in gaps:
            self.assertAlmostEqual(gap, 3, delta=0.4)


class GitColorsTest(CdsCase):
    def test_file_colors(self) -> None:
        """Az új fájl neve és a + szám added-zöld, a törölté removed-piros, a módosítotté modified."""
        self.open_commit(FILES_SUBJECT)
        files = self.page.locator("#rows .details .file")
        added = files.filter(has_text="uj.txt")
        color = lambda loc: loc.evaluate("e => getComputedStyle(e).color")   # noqa: E731
        self.assertEqual(color(added.locator(".path")), rgb("#1e9e3c"))
        self.assertEqual(color(added.locator(".churn > .a")), rgb("#1e9e3c"))
        self.assertEqual(color(files.filter(has_text="main-0-0.txt").locator(".path")), rgb("#cd2054"))
        self.assertEqual(color(files.filter(has_text="main-0-1.txt").locator(".path")), rgb("#98801f"))

    def test_pr_chip(self) -> None:
        """A `Merge pull request #42` chipje a merged színt viseli."""
        chip = self.row("Merge pull request").locator(".badge.ref-pr")
        self.assertEqual(chip.evaluate("e => getComputedStyle(e).color"), rgb("#8e6bd9"))


# ── Lenyitás: a fejléc és a tartalom egy keret ────────────────────────────

class ExpandTest(CdsCase):
    def test_hover_collapsed(self) -> None:
        """A csukott sor hoverre a hover szürkéjét kapja."""
        row = self.row("main-3-2")
        row.hover()
        self.settle()
        self.assertEqual(row.locator(".row-in").evaluate("e => getComputedStyle(e).backgroundColor"), rgb("#f2f2f2"))

    def test_expanded_commit(self) -> None:
        """Lenyitva a fejléc átlátszó (hover alatt is), és egy 12 px-es kerek keret fogja körbe a
        részletekkel együtt."""
        row = self.row("main-3-2")
        row.click()
        row.hover()
        self.settle()
        head = row.locator(".row-in")
        details = self.page.locator("#rows .details")
        css = lambda loc, p: loc.evaluate(f"e => getComputedStyle(e)['{p}']")   # noqa: E731
        self.assertEqual(css(head, "backgroundColor"), TRANSPARENT)
        self.assertEqual(css(head, "borderTopLeftRadius"), "12px")
        self.assertEqual(css(details, "borderBottomLeftRadius"), "12px")
        self.assertEqual(css(details, "borderTopWidth"), "0px")
        self.assertEqual(css(details, "borderLeftWidth"), "1px")
        self.assertEqual(css(details, "backgroundColor"), TRANSPARENT)
        self.assertAlmostEqual(details.bounding_box()["y"], head.bounding_box()["y"] + head.bounding_box()["height"], delta=1)

    def test_expanded_file(self) -> None:
        """A lenyitott fájlsor és a diffje egy 12 px-es keret; a diff alja 11 px."""
        self.open_file("settings.py")
        self.page.wait_for_selector("#rows .details .diff .diff-line")
        self.settle()
        file = self.page.locator('#rows .details .file[aria-expanded="true"]')
        diff = self.page.locator("#rows .details .file + .diff:not([hidden])")
        css = lambda loc, p: loc.evaluate(f"e => getComputedStyle(e)['{p}']")   # noqa: E731
        self.assertEqual(css(file, "backgroundColor"), TRANSPARENT)
        self.assertEqual(css(file, "borderTopLeftRadius"), "12px")
        self.assertEqual(css(diff, "borderBottomLeftRadius"), "12px")
        self.assertEqual(css(diff, "borderTopWidth"), "0px")
        self.assertEqual(css(diff, "paddingBottom"), "11px")


# ── Nyilak: 16 px ─────────────────────────────────────────────────────────

class ChevronTest(CdsCase):
    def test_chevrons(self) -> None:
        """A fájlsor nyila 12 × 12 (`xs`); az ágválasztóé az app menügombjáé: 16 × 16 (`sm`), 60 %-os."""
        self.open_commit(FILES_SUBJECT)
        b = self.box("#rows .details .file .chev .ic")
        self.assertEqual((b["width"], b["height"]), (12, 12))
        b = self.box("#branchBtn .chev")
        self.assertEqual((b["width"], b["height"]), (16, 16))
        self.assertEqual(self.style("#branchBtn .chev", "opacity"), "0.6")

    def test_file_icons(self) -> None:
        """A fájlikon 16 px, mint az app fájllistájában (a Catppuccin-ikon és az általános is)."""
        self.open_commit(FILES_SUBJECT)
        sizes = self.page.locator("#rows .details .file .fic").evaluate_all(
            "es => es.map(e => [e.getBoundingClientRect().width, e.getBoundingClientRect().height])")
        self.assertTrue(sizes)
        self.assertEqual({tuple(x) for x in sizes}, {(16, 16)})


# ── A lenyílóban a pipa jobbra, egy oszlopban ─────────────────────────────

class MenuCheckTest(CdsCase):
    def test_branch_checks(self) -> None:
        """A „Minden ág” és a `dev` pipája egy x-en, a távolságoktól jobbra; a szűrő nagyítója és
        az ágak ikonja egy oszlopban."""
        self.page.locator("#branchBtn").click()
        self.settle()
        dev = self.page.locator("#branchPop .option.blk", has=self.page.locator(".name", has_text="dev")).first
        all_ck = self.box("#branchPop .menu-all .ckc")
        dev_ck = dev.locator(".ln").first.locator(".ckc").bounding_box()
        self.assertAlmostEqual(dev_ck["x"], all_ck["x"], delta=0.5)
        dists = dev.locator(".dc").evaluate_all("ds => ds.map(d => d.getBoundingClientRect().right)")
        self.assertTrue(dists)
        self.assertGreater(dev_ck["x"], max(dists))
        lens = self.box("#branchPop .menu-search .ic")
        col = dev.locator(".col").first.bounding_box()
        self.assertAlmostEqual(lens["x"] + lens["width"] / 2, col["x"] + col["width"] / 2, delta=0.5)


class MenuIndentTest(CdsCase):
    """Több worktree-nél az ágválasztó worktree-fejlécei alatt a saját ágaik."""

    @classmethod
    def prepare(cls, repo: Path) -> None:
        prepare_cds(repo)
        git_in(repo, "worktree", "add", "-q", "-b", "wt-ag", str(repo.parent / "wt"), "main")
        (repo.parent / "wt" / "piszkos.txt").write_text("nem commitolt\n", encoding="utf-8")   # WIP-jel a fejlécen

    def test_branches_indented(self) -> None:
        """A fejléc alá tartozó ág ikonja a fejléc nevével egy vonalban, beljebb a fejléc ikonjánál."""
        self.page.locator("#branchBtn").click()
        self.settle()
        grp = self.page.locator("#branchPop .menu-grp:has(> .menu-wt)").first
        head_ic, head_name = (grp.locator(sel).first.bounding_box()["x"] for sel in (".menu-wt .ic", ".menu-wt .name"))
        col = grp.locator(".option.blk .col").first.bounding_box()["x"]
        self.assertGreater(col, head_ic + 16)
        self.assertAlmostEqual(col, head_name, delta=0.5)
        # a jelenlegi worktree neve az app bold-ja (560), a többié medium (460)
        self.assertEqual(self.style("#branchPop .menu-wt-cur", "fontWeight"), "560")
        self.assertEqual(self.style("#branchPop .menu-wt .name:not(.menu-wt-cur)", "fontWeight"), "460")
        # a worktree-fejléc kattintható (kijelöli az ágait): a szövege nem halvány, mint a remote csoporté
        self.assertEqual(self.style("#branchPop .option.menu-wt", "color"), rgb("#1a1a1a"))

    def test_wip_mark(self) -> None:
        """A nem commitolt változás jele a worktree-fejlécen akkora, mint a gráfon (12 px), és a
        pipák oszlopának közepén áll."""
        self.page.locator("#branchBtn").click()
        self.settle()
        wip = self.box("#branchPop .menu-wt .wip")
        ck = self.box("#branchPop .blk .ckc .ic")
        self.assertEqual((wip["width"], wip["height"]), (12, 12))
        self.assertAlmostEqual(wip["x"] + 6, ck["x"] + ck["width"] / 2, delta=0.5)

    def test_worktree_chip_icons(self) -> None:
        """A worktree-jellel kezdődő chip (a kiemelt körvonalú is): a jel a széltől 4 px-re, a
        branch-ikon 3 px-re tőle, a név 3,2 px-re az ikontól."""
        for chip in self.page.locator("#rows .badge:has(> .wt-lead)").all():
            left, gap, text = chip.evaluate("""b => {
              const r = b.getBoundingClientRect(), [a, c] = [...b.querySelectorAll('svg.ic')].slice(0, 2).map(i => i.getBoundingClientRect());
              const n = b.querySelector('.badge-name').getBoundingClientRect();
              return [a.left - r.left, c.left - a.right, n.left - c.right]; }""")
            self.assertAlmostEqual(left, 4, delta=0.05)
            self.assertAlmostEqual(gap, 3, delta=0.05)
            self.assertAlmostEqual(text, 3.2, delta=0.05)


class UpstreamPairTest(CdsCase):
    """Az ágválasztóban a helyi ág mellett csak az azonos nevű upstream áll."""

    @classmethod
    def prepare(cls, repo: Path) -> None:
        prepare_cds(repo)
        git_in(repo, "branch", "-q", "--track", "feat-uj", "origin/main")    # az origin/HEAD-ből indítva
        git_in(repo, "push", "-q", "origin", "kiserlet-0:masnev")
        git_in(repo, "branch", "-q", "-u", "origin/masnev", "kiserlet-1")   # más nevű, saját párja nincs

    def blocks(self) -> list:
        self.page.locator("#branchBtn").click()
        self.settle()
        return self.page.locator("#branchPop .option.blk[data-refs]").evaluate_all("bs => bs.map(b => b.dataset.refs)")

    def test_same_name_only(self) -> None:
        """A `dev` mellett az `origin/dev`; a `main`-ből indított `feat-uj` mellett nincs `origin/main`,
        az a `main` párja marad."""
        refs = self.blocks()
        self.assertIn("dev origin/dev", refs)
        self.assertIn("main origin/main", refs)
        self.assertIn("feat-uj", refs)
        self.assertEqual(sum("origin/main" in r.split() for r in refs), 1)

    def test_unpaired_remote(self) -> None:
        """A más nevű upstream, amelynek nincs azonos nevű helyi párja, a remote ágak közt látszik."""
        refs = self.blocks()
        self.assertIn("kiserlet-1", refs)
        self.assertIn("origin/masnev", refs)


# ── A markdown- és SVG-diff nézetváltója: kétgombos szegmens ──────────────

class SegmentTest(CdsCase):
    def test_md_segment(self) -> None:
        """A `</>` gombra a nyers diff, és az a lenyomott."""
        self.open_file("README.md")
        self.page.wait_for_selector(".diff .md-doc")
        raw = self.page.locator('.diff .md-seg [data-md-mode="raw"]')
        self.assertEqual(raw.get_attribute("aria-pressed"), "false")
        raw.click()
        self.page.wait_for_selector(".diff .diff-line")
        self.assertEqual(self.page.locator('.diff .md-seg [data-md-mode="raw"]').get_attribute("aria-pressed"), "true")
        self.assertEqual(self.page.locator('.diff .md-seg [data-md-mode="rendered"]').get_attribute("aria-pressed"), "false")

    def test_svg_segment(self) -> None:
        """Az SVG képnézetében a kód gombra a kód, és az a lenyomott."""
        self.open_file("logo.svg")
        self.page.wait_for_selector(".diff .img-fig")
        self.page.locator('.diff .md-seg [data-svg-mode="code"]').click()
        self.page.wait_for_selector(".diff .diff-line")
        self.assertEqual(self.page.locator('.diff .md-seg [data-svg-mode="code"]').get_attribute("aria-pressed"), "true")
        self.assertEqual(self.page.locator('.diff .md-seg [data-svg-mode="image"]').get_attribute("aria-pressed"), "false")


# ── Tooltip: a lap saját, kétszintű buboréka ──────────────────────────────

class TooltipTest(CdsCase):
    def tip(self) -> dict:
        self.page.wait_for_selector("#tip.on")
        return self.page.locator("#tip").evaluate("""t => ({
          bg: getComputedStyle(t).backgroundColor,
          lines: [...t.children].map(e => [e.className, e.textContent, getComputedStyle(e).fontSize, getComputedStyle(e).color]),
        })""")

    def test_multiline(self) -> None:
        """A 3 soros branch-badge tooltipje: fekete buborék, a fő sor 13 px, a többi 11 px, halványabb."""
        badge = self.page.locator("#rows .badge.ref-head").first
        self.assertEqual(len(badge.get_attribute("data-tip").split("\n")), 3)
        badge.hover()
        tip = self.tip()
        self.assertEqual(tip["bg"], rgb("#0b0b0b"))
        main, *subs = tip["lines"]
        self.assertEqual(main[2], "13px")
        self.assertEqual(main[3], rgb("#ffffff"))
        self.assertEqual(len(subs), 2)
        for sub in subs:
            self.assertEqual(sub[0], "sub")
            self.assertEqual(sub[2], "11px")
            self.assertEqual(sub[3], rgb("#ffffff", 0.57))

    def test_shortcut(self) -> None:
        """A képnéző bezáró gombjának buboréka: „Bezárás”, mellette halványan „Esc”."""
        self.open_file("logo.svg")
        self.page.wait_for_selector(".diff .img-fig")
        self.page.locator(".diff .img-fig").first.hover()
        self.page.locator(".diff [data-img-full]").click()
        self.settle()                              # a teljes lapos nézet elrendezése (görgetés rejti a buborékot)
        self.page.locator(".img-full [data-img-close]").hover()
        self.page.wait_for_selector("#tip.on")
        main = self.page.locator("#tip > :first-child")
        self.assertEqual(main.evaluate("e => e.firstChild.textContent"), "Bezárás")
        kbd = main.locator(".kbd")
        self.assertEqual(kbd.inner_text(), "Esc")
        self.assertEqual(kbd.evaluate("e => getComputedStyle(e).color"), rgb("#ffffff", 0.4))

    def test_no_native_title(self) -> None:
        """Egyetlen elemnek sincs `title` attribútuma — nyitott commit és menü mellett sem."""
        count = "document.querySelectorAll('[title]').length"
        self.assertEqual(self.page.evaluate(count), 0)
        self.open_commit(FILES_SUBJECT)
        self.page.locator("#branchBtn").click()
        self.settle()
        self.assertEqual(self.page.evaluate(count), 0)


# ── Állapot-színek ────────────────────────────────────────────────────────

class LiveStateTest(CdsCase):
    def test_live(self) -> None:
        """Élőben a pötty a good-zöld."""
        self.page.wait_for_selector(".foot.on")
        self.assertEqual(self.style(".foot .dot", "backgroundColor"), rgb("#0ca30c"))


class StaleStateTest(CdsCase):
    """A nyitva tartott `changes` hívás azonnal, nem átmeneti hibával bukik: a frissítés elakad."""

    INIT = """
    const use = window.claude.use;
    window.claude.use = async name => { const mcp = await use(name); return mcp && { callTool: (s, tool, args, opts) =>
      tool === 'changes' && args.wait > 0
        ? Promise.reject(Object.assign(new Error('nincs'), { code: 'server_not_connected' }))
        : mcp.callTool(s, tool, args, opts) }; };"""

    def test_stale(self) -> None:
        """Elakadt frissítésnél a pötty a critical-piros."""
        self.page.wait_for_selector(".foot.stale")
        self.assertEqual(self.style(".foot .dot", "backgroundColor"), rgb("#d03b3b"))


class StaleVersionTest(CdsCase):
    """A futó verzió más, mint a telepített: a lábléc figyelmeztet."""

    def mcp(self, tool: str, args: dict) -> str:
        out = json.loads(super().mcp(tool, args))
        if tool == "changes" and out["ok"]:
            out["value"].update(version="1.0.0", installed="1.0.1")
        return json.dumps(out)

    def test_version_warning(self) -> None:
        """A figyelmeztetés jele a warning-sárga, a szövege olvasható (nem sárga)."""
        self.page.wait_for_selector(".foot .ver.warn")
        self.assertEqual(self.style(".foot .ver.warn .ic", "color"), rgb("#fab219"))
        self.assertEqual(self.style(".foot .ver.warn", "color"), rgb("#1a1a1a"))


# ── Monogram: szerzőnként egy munkatárs-szín ──────────────────────────────

COLLABORATOR = [rgb(c) for c in ("#7161e0", "#c04873", "#0f7e5c", "#008300", "#945d00", "#6d6b67")]


class MonogramTest(CdsCase):
    def test_same_author_same_color(self) -> None:
        """Teszt Elek minden monogramja ugyanazt a munkatárs-színt kapja, fehér betűvel."""
        colors = self.page.locator("#rows .author.ini").evaluate_all(
            "es => es.map(e => [getComputedStyle(e).backgroundColor, getComputedStyle(e).color])")
        self.assertGreater(len(colors), 1)
        self.assertEqual(len(set(map(tuple, colors))), 1)
        self.assertIn(colors[0][0], COLLABORATOR)
        self.assertEqual(colors[0][1], rgb("#ffffff"))


# ── A keresés találata kiemelt a subjectben ───────────────────────────────

class SearchHighlightTest(CdsCase):
    def test_highlight(self) -> None:
        """A „login” szóra keresve a subjectben a szó bg-highlight hátteret kap."""
        self.page.locator("#search").fill("login")
        self.settle()
        mark = self.row("login oldal").locator(".subject mark")
        self.assertEqual(mark.inner_text(), "login")
        self.assertEqual(mark.evaluate("e => getComputedStyle(e).backgroundColor"), rgb("#fab219", 0.33))


# ── Kontrollok az app komponensei szerint ────────────────────────────────

class ControlsTest(CdsCase):
    def test_trigger_button(self) -> None:
        """A lenyíló gomb az app secondary gombja: szürke tint, keret és árnyék nélkül."""
        self.assertEqual(self.style("#branchBtn", "backgroundColor"), "rgba(0, 0, 0, 0.05)")
        self.assertEqual(self.style("#branchBtn", "boxShadow"), "none")

    def test_search_field(self) -> None:
        """A keresőmező az app TextInput-ja: halvány mező, 1 px-es keret, 12 px a bal szélén;
        a gyorsbillentyű billentyűnként egy négyzetes sapka, 2 px-es közzel."""
        self.assertEqual(self.style(".search", "backgroundColor"), "rgba(255, 255, 255, 0.5)")
        self.assertEqual(self.style(".search", "paddingLeft"), "12px")
        caps = self.page.locator(".search kbd").evaluate_all(
            "ks => ks.map(k => { const r = k.getBoundingClientRect(); return [k.textContent, r.width, r.height, r.left]; })")
        self.assertEqual([c[0] for c in caps], ["⌘", "F"])
        self.assertTrue(all(c[1] == c[2] == 18 for c in caps), caps)
        self.assertEqual(caps[1][3] - caps[0][3], 20)

    def test_focus_ring(self) -> None:
        """A fókuszgyűrű az app focus-shadow-ja: elöl a háttér színű belső vonal."""
        self.page.locator("#search").focus()
        self.assertTrue(self.style(".search", "boxShadow").startswith("rgb(255, 255, 255) 0px 0px 0px 1px inset"))

    def test_switch(self) -> None:
        """A kapcsoló gombja bekapcsolva 16 px-szel csúszik; hoverre a kikapcsolt sáv erősebb."""
        track = ".chrome .switch:not(:has(input:checked)) .track"
        off = self.style(track, "backgroundColor")
        self.page.locator(".chrome .switch:not(:has(input:checked))").first.hover()
        self.page.wait_for_timeout(250)   # a sáv színe .15 s alatt vált
        self.assertNotEqual(self.style(track, "backgroundColor"), off)
        self.page.locator(".chrome .switch:not(:has(input:checked))").first.click()
        self.page.wait_for_timeout(250)
        moved = self.page.locator(".chrome .switch:has(input:checked) .track").first.evaluate(
            "t => new DOMMatrix(getComputedStyle(t, '::after').transform).m41")
        self.assertEqual(moved, 16)

    def test_menu(self) -> None:
        """A menü az app Menu-je: 4 px-es gutter, a keret a border token, a tétel 10 px-es
        paddingje; a worktree-fejléc nélküli menüben is."""
        self.page.locator("#themeBtn").click()
        self.assertEqual(self.style("#themePop", "paddingTop"), "4px")
        self.assertTrue(self.style("#themePop", "boxShadow").startswith("rgba(0, 0, 0, 0.08) 0px 0px 0px 1px"))
        self.assertEqual(self.style("#themePop .option", "paddingLeft"), "10px")

    def test_link(self) -> None:
        """A szöveges link az app TextLink-je: text-accent, mindig aláhúzva, 3 px-re."""
        self.open_commit("cds: módosítva")
        link = ".details .chip button.hash"
        self.assertEqual(self.style(link, "color"), rgb("#184f95"))
        self.assertEqual(self.style(link, "textDecorationLine"), "underline")
        self.assertEqual(self.style(link, "textUnderlineOffset"), "3px")

    def test_segment(self) -> None:
        """A szegmens választott gombja a sávon belül 1 px-re, a sarka 7; a többi ikon halvány."""
        self.open_file("README.md")
        self.page.wait_for_selector(".diff .md-doc")
        seg, on = self.box(".diff .md-seg"), self.box('.diff .md-seg [aria-pressed="true"]')
        self.assertEqual((on["y"] - seg["y"], on["height"]), (1, 26))
        self.assertEqual(self.style('.diff .md-seg [aria-pressed="true"]', "borderTopLeftRadius"), "7px")
        self.assertEqual(self.style('.diff .md-seg [aria-pressed="false"]', "color"), rgb("#888888"))

    def test_panel_and_text(self) -> None:
        """A commit-panel az app panelje (keret + shadow-sm); a törzsszöveg sormagassága 20 px;
        a görgetősáv vékony."""
        self.open_commit("cds: módosítva")
        self.assertNotEqual(self.style(".details", "boxShadow"), "none")
        self.assertEqual(self.style("body", "lineHeight"), "20px")
        self.assertEqual(self.style("#rows", "scrollbarWidth"), "thin")

    def test_spinner(self) -> None:
        """A betöltés jele az app Spinner-e: 12 px-es forgó kör a felirat előtt."""
        size = self.page.evaluate("""() => { const p = document.createElement('p'); p.className = 'diff-note loading';
          document.body.append(p); const s = getComputedStyle(p, '::before'); const r = [s.width, s.animationName]; p.remove(); return r; }""")
        self.assertEqual(size, ["12px", "spin"])


# ── Ikonméretek: az app skálája (12 / 16 / 20), a menüben 20 ─────────────

class IconSizesTest(CdsCase):
    def sizes(self, selector: str) -> set:
        return {tuple(round(v) for v in (b["width"], b["height"]))
                for b in (e.bounding_box() for e in self.page.locator(selector).all()) if b}

    def test_menu_icons(self) -> None:
        """Az ágválasztó és a téma menüjének ikonjai 20 px-esek (az app comfortable `md`-je), a pipa
        is, akcentus színnel; a gombok és a chipek ikonja 16 marad."""
        self.page.locator("#branchBtn").click()
        self.settle()
        self.assertEqual(self.sizes("#branchPop .col svg.ic, #branchPop .menu-search .ic, #branchPop .ic.ck:visible"), {(20, 20)})
        self.assertEqual(self.style("#branchPop .ic.ck", "color"), rgb("#257de0"))
        self.assertEqual(self.sizes("#branchBtn .select-ic svg.ic, #rows .badge svg.ic"), {(16, 16)})
        self.page.keyboard.press("Escape")
        self.page.locator("#themeBtn").click()
        self.assertEqual(self.sizes("#themePop .option > svg.ic:not(.ck)"), {(20, 20)})

    def test_head_chip(self) -> None:
        """A fejléc HEAD-chipje akkora, mint a sor chipje: 20 px magas, 12 px-es betű."""
        self.assertEqual(self.box(".head-chip")["height"], self.box("#rows .badge")["height"])
        self.assertEqual(self.style(".head-chip", "fontSize"), "12px")

    def test_panel_icons(self) -> None:
        """A commit-panel ikonjai (hash-chip, másolás, megnyitás) 16 px-esek, nem 14."""
        self.open_commit("cds: módosítva")
        self.assertEqual(self.sizes(".details .chip svg.ic, .details .mini svg.ic"), {(16, 16)})

    def test_branch_menu_reach(self) -> None:
        """Az ágválasztó a lap magasságának ~80 %-áig nyúlhat le; alacsony lapon tovább, az aljáig."""
        for height in (900, 420):
            self.page.set_viewport_size({"width": 1300, "height": height})
            self.page.locator("#branchBtn").click()
            self.settle()
            top = self.box("#branchPop")["y"]
            limit = float(self.page.locator("#branchPop").evaluate("p => parseFloat(getComputedStyle(p).maxHeight)"))
            expected = max(height * 0.8 - top, min(height - top - 8, 320))
            self.assertAlmostEqual(limit, max(120, round(expected)), delta=1, msg=height)
            self.page.keyboard.press("Escape")
