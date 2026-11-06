"""Egyesített fejléc (#64): keret nélküli ghost gombok, az ágválasztó gombja a kijelölést mutatja,
a remote-ok az ágválasztó szakaszfejlécén kapcsolhatók, a keresés lenyíló gomb a ref-szűrővel."""
from __future__ import annotations

import json
from pathlib import Path

from harness import CSP, SLUG, URL, PageTestCase, git_in
from test_cds import TRANSPARENT, rgb
from test_subtree import add_origin

ACCENT = rgb("#257de0")
ICONS = json.loads((Path(__file__).resolve().parents[2] / "design/icons/anthropicons.json").read_text(encoding="utf-8"))
MD = ICONS["icons_md"]
LONG_QUERY = "nagyon-hosszu-keresett-kifejezes-a-commitokban"
NINE = ("dev", "main origin/main", "feat/menu", "wt-test", "fix/scroll upstream/fix/scroll",
        "extra-1", "extra-2", "hotfix/meg-egy-hosszu-ag-nev", "release/2026-oszi-kiadas-hosszu-nevvel")


def commit(repo: Path, subject: str, name: str) -> None:
    (repo / name).write_text(f"{subject}\n", encoding="utf-8")
    git_in(repo, "add", ".")
    git_in(repo, "commit", "-qm", subject)


def prepare_header(repo: Path) -> None:
    """Két remote: az `origin`-en a `main`, a `dev` (pusholatlan committal) és a csak remote
    `test-branch-origin`; az `upstream`-en csak a `fix/scroll`, a helyi párjával egy helyen."""
    add_origin(repo)
    git_in(repo, "switch", "-q", "-c", "dev")
    commit(repo, "menü: a lenyíló keresés", "menu.txt")
    git_in(repo, "push", "-q", "-u", "origin", "dev")
    commit(repo, "dev: pusholatlan munka", "dev.txt")
    for name in ("feat/menu", "wt-test", "extra-1", "extra-2", "long/feature-branch-name",
                 "another/long-branch", "fix/scroll"):
        git_in(repo, "branch", name, "main")
    git_in(repo, "push", "-q", "origin", "main:test-branch-origin")
    upstream = repo.parent / "upstream.git"
    git_in(repo.parent, "init", "-q", "--bare", "-b", "main", str(upstream))
    git_in(repo, "remote", "add", "upstream", str(upstream))
    git_in(repo, "push", "-q", "-u", "upstream", "fix/scroll")


class HeaderCase(PageTestCase):
    WIDTH = 1100

    @classmethod
    def prepare(cls, repo: Path) -> None:
        prepare_header(repo)

    def style(self, selector: str, prop: str) -> str:
        return self.page.locator(selector).first.evaluate(f"e => getComputedStyle(e)['{prop}']")

    def box(self, selector: str) -> dict:
        return self.page.locator(selector).first.bounding_box()

    def open_branches(self) -> None:
        if self.page.locator("#branchPop").is_hidden():
            self.page.locator("#branchBtn").click()
        self.settle()

    def close_menu(self) -> None:
        self.page.keyboard.press("Escape")
        self.settle()

    def select(self, *keys: str) -> None:
        """A menü soraiból a `keys` refjei (a sor pipája: `data-refs`) kijelölve, utána a menü zárva."""
        self.open_branches()
        for key in keys:
            self.page.locator(f'#branchPop .ckc[data-refs="{key}"]').first.click()
            self.settle()
        self.close_menu()

    def remote(self, name: str):
        return self.page.locator(f'#branchPop .menu-remote[data-remote="{name}"]')

    def toggle_remote(self, name: str) -> None:
        self.open_branches()
        self.remote(name).locator('[role="switch"]').click()
        self.settle()

    def items(self) -> list:
        """A gomb elemei: (név, névvel áll-e) — az ikonos elemnél a név a súgóból."""
        return self.page.locator("#branchBtn .sel-item").evaluate_all(
            "es => es.map(e => [e.querySelector('.sel-name')?.textContent || e.dataset.tip, Boolean(e.querySelector('.sel-name'))])")

    def tip(self, selector: str) -> str:
        self.page.locator(selector).first.hover()
        self.page.wait_for_selector("#tip.on")
        return self.page.locator("#tip").inner_text()

    def open_search(self) -> None:
        if self.page.locator("#searchPop").is_hidden():
            self.page.locator("#searchBtn").click()
        self.settle()

    def search(self, text: str, refs: bool = False) -> None:
        """Szűrés a keresés popupjában, utána a popup zárva."""
        self.open_search()
        self.page.locator("#search").fill(text)
        if refs:
            self.page.locator("#onlyRefs").click()
        self.settle()
        self.page.locator("#repoName").click()          # kívülre kattintva zár (az Esc a szöveget törölné)
        self.settle()

    def subjects(self) -> list:
        return self.page.locator("#rows .row .subject").all_inner_texts()


# ── A fejléc gombjai keret nélküli ghost gombok ──────────────────────────

class GhostButtonsTest(HeaderCase):
    BUTTONS = ("#branchBtn", "#searchBtn", "#sideBtn")

    def test_rest(self) -> None:
        """Nyugalomban a három gomb háttere áttetsző, kerete nincs, 28 px magas (az app egérrel
        használt kontrollja), 8 px-es sarokkal; a
        régi kapcsolók és a remote-szűrő eltűnt a fejlécből."""
        for btn in self.BUTTONS:
            self.assertEqual(self.style(btn, "backgroundColor"), TRANSPARENT, btn)
            self.assertEqual(self.style(btn, "boxShadow"), "none", btn)
            self.assertEqual(self.style(btn, "borderTopWidth"), "0px", btn)
            self.assertEqual(self.box(btn)["height"], 28, btn)
            self.assertEqual(self.style(btn, "borderTopLeftRadius"), "8px", btn)
        for gone in ("#showRemotes", "#remotesBtn", ".chrome .switch"):
            self.assertEqual(self.page.locator(gone).count(), 0, gone)
        self.assertFalse(self.page.locator("#onlyRefs").is_visible())

    def test_open(self) -> None:
        """Nyitott lenyílónál a gomb háttere a fill-ghost-selected (10 %), amíg nyitva van."""
        self.page.locator("#branchBtn").click()
        self.settle()
        self.page.mouse.move(600, 600)
        self.assertEqual(self.style("#branchBtn", "backgroundColor"), "rgba(0, 0, 0, 0.1)")
        self.close_menu()
        self.page.mouse.move(600, 600)
        self.assertEqual(self.style("#branchBtn", "backgroundColor"), TRANSPARENT)


class GhostDarkTest(HeaderCase):
    COLOR_SCHEME = "dark"

    def test_hover(self) -> None:
        """Sötétben hoverre a gomb háttere a fill-ghost-hover (7,5 %-os fehér), a szöveg text-primary."""
        self.page.locator("#branchBtn").hover()
        self.page.wait_for_timeout(200)
        self.assertEqual(self.style("#branchBtn", "backgroundColor"), "rgba(255, 255, 255, 0.075)")
        self.assertEqual(self.style("#branchBtn", "color"), rgb("#efefef"))


# ── A keresés egy gomb, ami lenyílik a mezővel és a ref-kapcsolóval ──────

class SearchPopupTest(HeaderCase):
    def test_icon_only(self) -> None:
        """Szűrő nélkül a keresés-gomb egy 28 px-es ikongomb az app 20 px-es (`md`) Search glifájával,
        akkora, mint a fájlok gombja; „Keresés ⌘F” súgóval."""
        box = self.box("#searchBtn")
        self.assertEqual((box["width"], box["height"]), (28, 28))
        self.assertEqual(box["width"], self.box("#sideBtn")["width"])
        self.assertEqual(self.page.locator("#searchBtn svg path").get_attribute("d"), MD["Search"])
        ic = self.box("#searchBtn svg.ic")
        self.assertEqual((ic["width"], ic["height"]), (20, 20))
        self.assertEqual(self.tip("#searchBtn"), "Keresés⌘F")
        self.assertEqual(self.page.locator("#tip .kbd").inner_text(), "⌘F")

    def test_click_opens(self) -> None:
        """Kattintásra a popupban a keresőmező (ikon nélkül, mint az app beágyazott keresője) kapja a
        fókuszt, alatta teljes szélességű vonal után a „Csak ref-es commitok” kapcsoló-sor áll."""
        self.page.locator("#searchBtn").click()
        self.settle()
        self.assertTrue(self.page.locator("#searchPop").is_visible())
        self.assertTrue(self.page.locator("#search").evaluate("e => e === document.activeElement"))
        head, row, pop = self.box("#searchPop .menu-search"), self.box("#onlyRefs"), self.box("#searchPop")
        self.assertEqual(self.page.locator("#searchPop .menu-search svg").count(), 0)
        self.assertEqual(self.style("#searchPop .menu-search", "borderBottomWidth"), "1px")
        self.assertEqual((head["x"], head["width"]), (pop["x"], pop["width"]))
        self.assertGreaterEqual(row["y"], head["y"] + head["height"])
        self.assertEqual(head["height"], 36)                      # az app beágyazott keresője
        self.assertTrue(self.page.evaluate("""() => [...document.styleSheets].flatMap(s => [...s.cssRules])
          .some(r => r.selectorText?.includes('.search-pop input::-webkit-search-cancel-button') && r.style.display === 'none')"""))   # nincs x a mezőben
        self.assertIn("Csak ref-es commitok", self.page.locator("#onlyRefs").inner_text())
        self.assertEqual(self.page.locator('#onlyRefs').get_attribute("aria-checked"), "false")

    def test_cmd_f(self) -> None:
        """⌘F a popupot nyitja, a fókusz a keresőmezőben."""
        self.page.locator("#rows .row").first.hover()
        self.page.keyboard.press("Meta+f")
        self.settle()
        self.assertTrue(self.page.locator("#searchPop").is_visible())
        self.assertTrue(self.page.locator("#search").evaluate("e => e === document.activeElement"))

    def test_cmd_f_closes_other_menu(self) -> None:
        """⌘F a nyitott ágválasztót bezárja: egyszerre egy lenyíló van nyitva."""
        self.open_branches()
        self.page.keyboard.press("Meta+f")
        self.settle()
        self.assertTrue(self.page.locator("#branchPop").is_hidden())
        self.assertTrue(self.page.locator("#searchPop").is_visible())

    def test_escape_closed_clears_text(self) -> None:
        """Zárt popupnál az Esc a keresett szöveget törli, a ref-szűrő marad."""
        self.search("menü", refs=True)
        self.page.keyboard.press("Escape")
        self.settle()
        self.assertEqual(self.page.locator("#search").input_value(), "")
        self.assertEqual(self.page.locator("#onlyRefs").get_attribute("aria-checked"), "true")
        self.assertTrue(self.page.locator("#searchBtn").evaluate("b => b.classList.contains('filtered')"))

    def test_typing_filters(self) -> None:
        """Gépelés közben a lista a „menü” szóra szűr, a popup nyitva marad."""
        self.open_search()
        self.page.locator("#search").fill("menü")
        self.settle()
        subjects = self.subjects()
        self.assertIn("menü: a lenyíló keresés", subjects)
        self.assertNotIn("main-0-0: egy commit a fixture-ből", subjects)
        self.assertTrue(self.page.locator("#searchPop").is_visible())

    def test_refs_switch(self) -> None:
        """A popup „Csak ref-es commitok” sora csak a reffel jelölt commitokat hagyja, a popup nyitva marad."""
        total = self.page.locator("#rows .row").count()
        self.open_search()
        self.page.locator("#onlyRefs").click()
        self.settle()
        self.assertEqual(self.page.locator("#onlyRefs").get_attribute("aria-checked"), "true")
        rows = self.page.locator("#rows .row")
        self.assertLess(rows.count(), total)
        self.assertEqual(self.page.locator("#rows .row:not(:has(.refs))").count(), 0)
        self.assertTrue(self.page.locator("#searchPop").is_visible())

    def test_escape_clears_text(self) -> None:
        """A mezőben az Esc előbb a keresett szöveget törli (a ref-szűrő és a popup marad), üres
        mezőben a popupot zárja."""
        self.open_search()
        self.page.locator("#onlyRefs").click()
        self.page.locator("#search").fill("menü")
        self.settle()
        self.page.keyboard.press("Escape")
        self.settle()
        self.assertEqual(self.page.locator("#search").input_value(), "")
        self.assertEqual(self.page.locator("#onlyRefs").get_attribute("aria-checked"), "true")
        self.assertTrue(self.page.locator("#searchPop").is_visible())
        self.page.keyboard.press("Escape")
        self.settle()
        self.assertTrue(self.page.locator("#searchPop").is_hidden())
        self.assertEqual(self.page.locator("#onlyRefs").get_attribute("aria-checked"), "true")

    def test_click_outside_keeps_filter(self) -> None:
        """A commitlistára kattintás bezárja a popupot, a szűrés megmarad."""
        self.open_search()
        self.page.locator("#search").fill("menü")
        self.settle()
        self.page.mouse.click(600, 500)
        self.settle()
        self.assertTrue(self.page.locator("#searchPop").is_hidden())
        self.assertNotIn("main-0-0: egy commit a fixture-ből", self.subjects())


# ── A szűrt keresés-gomb kiírja a szűrést, és egy x törli ────────────────

class SearchButtonTest(HeaderCase):
    def visible_parts(self) -> list:
        return self.page.locator("#searchBtn").evaluate("""b => [...b.querySelectorAll('.sb-part')]
          .filter(e => e.getClientRects().length).map(e => e.dataset.part)""")

    def test_text_and_refs(self) -> None:
        """Szöveg és ref-szűrő: sorban keresés-ikon, a szöveg, címke-ikon, x; a gomb háttere a lenyomott
        fájlok gombjáé, a szöveg és a címke akcentus színű, az ikon és az x text-primary."""
        self.search("menü", refs=True)
        self.page.mouse.move(600, 600)
        self.assertEqual(self.style("#searchBtn", "backgroundColor"), "rgba(0, 0, 0, 0.1)")
        self.page.locator("#sideBtn").click()
        self.page.mouse.move(600, 600)
        self.assertEqual(self.style("#sideBtn", "backgroundColor"), self.style("#searchBtn", "backgroundColor"))
        for part, color in (("search", rgb("#1a1a1a")), ("query", ACCENT), ("tag", ACCENT), ("clear", rgb("#1a1a1a"))):
            self.assertEqual(self.style(f'#searchBtn [data-part="{part}"]', "color"), color, part)
        self.assertEqual(self.visible_parts(), ["search", "query", "tag", "clear"])
        self.assertEqual(self.page.locator("#searchBtn .search-q").inner_text(), "menü")

    def test_refs_only(self) -> None:
        """Csak ref-szűrő: keresés-ikon, címke-ikon és x, szöveg nélkül."""
        self.search("", refs=True)
        self.assertEqual(self.visible_parts(), ["search", "tag", "clear"])

    def test_long_query(self) -> None:
        """A hosszú keresett szöveg kb. 160 px-nél „…”-ra végződik."""
        self.search(LONG_QUERY)
        q = self.page.locator("#searchBtn .search-q")
        width, scroll = q.evaluate("e => [e.getBoundingClientRect().width, e.scrollWidth]")
        self.assertLessEqual(width, 161)
        self.assertGreater(scroll, width)
        self.assertEqual(self.style("#searchBtn .search-q", "textOverflow"), "ellipsis")

    def test_clear(self) -> None:
        """Az x mindkét szűrőt törli, a popup nem nyílik meg, a gomb újra csak egy ikon."""
        total = self.page.locator("#rows .row").count()
        self.search("menü", refs=True)
        self.page.locator("#searchX").click()
        self.settle()
        self.assertEqual(self.page.locator("#search").input_value(), "")
        self.assertEqual(self.page.locator("#onlyRefs").get_attribute("aria-checked"), "false")
        self.assertEqual(self.page.locator("#rows .row").count(), total)
        self.assertTrue(self.page.locator("#searchPop").is_hidden())
        box = self.box("#searchBtn")
        self.assertEqual((box["width"], box["height"]), (28, 28))

    def test_clear_hover(self) -> None:
        """Az x saját hover-célpont: 24 px-es, 6 px-es sarkú fill-ghost-hover háttérrel."""
        self.search("menü")
        self.page.locator("#searchX").hover()
        self.page.wait_for_timeout(200)
        box = self.box("#searchX")
        self.assertEqual((box["width"], box["height"]), (24, 24))
        self.assertEqual(self.style("#searchX", "borderTopLeftRadius"), "6px")
        self.assertEqual(self.style("#searchX", "backgroundColor"), "rgba(0, 0, 0, 0.05)")


# ── Az ágválasztó gombja a kijelölést mutatja ────────────────────────────

class BranchButtonTest(HeaderCase):
    def test_nothing(self) -> None:
        """Kijelölés nélkül a felirat „Minden ág”."""
        self.assertEqual(self.page.locator("#branchBtn").inner_text().strip(), "Minden ág")

    def test_one(self) -> None:
        """Egy ág: a sávszínű ág-ikonja és a neve."""
        self.select("dev")
        item = self.page.locator("#branchBtn .sel-item")
        self.assertEqual(self.items(), [["dev", True]])
        self.assertEqual(item.get_attribute("data-kind"), "branch")
        self.assertTrue(item.locator("svg").get_attribute("style").startswith("color:var(--lane-"))

    def test_with_upstream(self) -> None:
        """Az ág és az upstreamje: a közös ág-felhő ikon és az ág neve."""
        self.select("dev", "origin/dev")
        self.assertEqual(self.items(), [["dev", True]])
        self.assertEqual(self.page.locator("#branchBtn .sel-item").get_attribute("data-kind"), "branchCloud")

    def test_three(self) -> None:
        """Három rövid nevű ág mind ikonnal és névvel, egymás mellett."""
        self.select("dev", "main origin/main", "feat/menu")
        self.assertEqual(self.items(), [["dev", True], ["main", True], ["feat/menu", True]])
        ys = {round(b["y"]) for b in (e.bounding_box() for e in self.page.locator("#branchBtn .sel-item").all())}
        self.assertEqual(len(ys), 1)

    def test_five(self) -> None:
        """Öt ág: az első 3 ikonnal és névvel, a többi csak színes ikonnal."""
        self.select(*NINE[:5])
        self.assertEqual(self.items(), [["dev", True], ["main", True], ["feat/menu", True],
                                        ["wt-test", False], ["fix/scroll", False]])

    LONG = ("long/feature-branch-name", "another/long-branch", "dev", "main origin/main")

    def test_long_names(self) -> None:
        """Hosszabb nevekkel is 3 név áll, ha elfér; a gomb legfeljebb 500 px."""
        self.select(*self.LONG)
        self.assertEqual(self.items(), [["long/feature-branch-name", True], ["another/long-branch", True],
                                        ["dev", True], ["main", False]])
        self.assertLessEqual(self.box("#branchBtn")["width"], 500)

    def test_narrow(self) -> None:
        """Keskeny fejlécben csak annyi név áll, amennyi a repó és az eszközök mellett elfér: a
        fejléc egy sorban marad."""
        self.select(*self.LONG)
        self.resize(640)
        named = [n for _, n in self.items()]
        self.assertLess(sum(named), 3)
        self.assertTrue(named[0])
        self.assertFalse(self.page.locator(".chrome").evaluate("c => c.classList.contains('multi')"))

    def test_nine(self) -> None:
        """Kilenc ágnál 6 elem látszik (3 névvel, 3 csak ikonnal), utána „+3”."""
        self.select(*NINE)
        items = self.items()
        self.assertEqual(len(items), 6)
        self.assertEqual([named for _, named in items], [True] * 3 + [False] * 3)
        self.assertEqual(self.page.locator("#branchBtn .sel-more").inner_text(), "+3")

    def test_icon_tip(self) -> None:
        """A csak ikonnal álló ág súgója csak a neve."""
        self.select(*NINE[:5])
        self.assertEqual(self.tip('#branchBtn .sel-item[data-tip="wt-test"]'), "wt-test")

    def test_more_tip(self) -> None:
        """A „+3” súgója a kimaradt 3 ág nevét sorolja, soronként egyet."""
        self.select(*NINE)
        self.assertEqual(self.tip("#branchBtn .sel-more").split("\n"),
                         ["extra-2", "hotfix/meg-egy-hosszu-ag-nev", "release/2026-oszi-kiadas-hosszu-nevvel"])

    def test_selected_background(self) -> None:
        """Kijelölt ágnál a gomb háttere a lenyomott (fill-ghost-selected); csak rejtett remote miatt nincs háttér."""
        self.toggle_remote("upstream")
        self.close_menu()
        self.page.mouse.move(600, 600)
        self.assertEqual(self.style("#branchBtn", "backgroundColor"), TRANSPARENT)
        self.select("dev")
        self.page.mouse.move(600, 600)
        self.assertEqual(self.style("#branchBtn", "backgroundColor"), "rgba(0, 0, 0, 0.1)")

    def test_clear(self) -> None:
        """Kijelölésnél a nyíl helyén x: „Minden ág”-ra áll vissza, a menüt nem nyitja; a gomb többi
        része nyitja a menüt. Kijelölés nélkül nyíl, x nincs."""
        self.assertTrue(self.page.locator("#branchBtn .chev").is_visible())
        self.assertEqual(self.page.locator("#branchX").count(), 0)
        total = self.page.locator("#rows .row").count()
        self.select("dev")
        self.assertFalse(self.page.locator("#branchBtn .chev").is_visible())
        self.assert_x_centered("#branchBtn", "#branchX")
        self.page.locator("#branchBtn .sel-name").click()
        self.settle()
        self.assertTrue(self.page.locator("#branchPop").is_visible())
        self.close_menu()
        self.page.locator("#branchX").click()
        self.settle()
        self.assertTrue(self.page.locator("#branchPop").is_hidden())
        self.assertEqual(self.page.locator("#branchBtn .select-label").inner_text(), "Minden ág")
        self.assertEqual(self.page.locator("#rows .row").count(), total)
        self.assertTrue(self.page.locator("#branchBtn .chev").is_visible())
        self.search("menü")
        self.assert_x_centered("#searchBtn", "#searchX")

    def assert_x_centered(self, btn: str, x: str) -> None:
        """Az x ikonja függőlegesen a gomb közepén."""
        b, i = self.box(btn), self.box(f"{x} svg")
        self.assertAlmostEqual(i["y"] + i["height"] / 2, b["y"] + b["height"] / 2, delta=0.5, msg=btn)


class WorktreeButtonTest(HeaderCase):
    @classmethod
    def prepare(cls, repo: Path) -> None:
        prepare_header(repo)
        wt = repo.parent / "menu-merge"
        git_in(repo, "worktree", "add", "-q", "-b", "menu-merge", str(wt), "main")
        git_in(wt, "switch", "-q", "-c", "menu-merge-2")
        git_in(wt, "switch", "-q", "menu-merge")

    def test_worktree_one_item(self) -> None:
        """A worktree összes ága egy elem a worktree ikonjával és nevével; mellette a `dev`."""
        self.open_branches()
        self.page.locator('#branchPop .option.menu-wt[data-key^="wt:menu-merge"]').click()
        self.settle()
        self.select("dev")
        self.assertEqual(self.items(), [["menu-merge", True], ["dev", True]])
        self.assertEqual(self.page.locator("#branchBtn .sel-item").first.get_attribute("data-kind"), "worktree")


# ── A remote-ok az ágválasztó szakaszfejlécén kapcsolhatók ───────────────

class RemoteHeadersTest(HeaderCase):
    def test_header_per_remote(self) -> None:
        """Remote-onként egy fejléc: glóbusz-ikon, név, bekapcsolt kapcsoló, „csak remote” megjegyzés nélkül."""
        self.open_branches()
        for name in ("origin", "upstream"):
            head = self.remote(name)
            self.assertEqual(head.count(), 1, name)
            self.assertEqual(head.locator("svg.ic path").first.get_attribute("d"), MD["Globe"])
            self.assertEqual(head.locator(".name").evaluate("e => getComputedStyle(e).color"), rgb("#1a1a1a"))
            self.assertEqual(head.locator(".name").inner_text(), name)
            self.assertEqual(head.locator('[role="switch"]').get_attribute("aria-checked"), "true")
        self.assertEqual(self.page.locator("#branchPop .menu-wt .note").count(), 0)

    def test_header_without_branches(self) -> None:
        """A csak remote ág nélküli `upstream` fejléce kapcsolóval ott van, alatta nincs ág."""
        self.open_branches()
        grp = self.page.locator('#branchPop .menu-grp:has(> .menu-remote[data-remote="upstream"])')
        self.assertTrue(grp.is_visible())
        self.assertEqual(grp.locator(".option.blk").count(), 0)

    def test_filter_by_remote_name(self) -> None:
        """A remote nevére szűrve a fejléce látszik, és nincs mellette „Nincs ilyen ág”."""
        self.open_branches()
        self.page.locator("#branchQuery").fill("upstream")
        self.settle()
        self.assertTrue(self.remote("upstream").is_visible())
        self.assertFalse(self.page.locator("#branchList").evaluate("l => l.classList.contains('empty')"))

    def test_indented(self) -> None:
        """A csak remote ág a remote fejléce alatt beljebb kezdődik: az ikonja a remote nevével egy vonalban."""
        self.open_branches()
        col = self.box('#branchPop .option.blk[data-refs="origin/test-branch-origin"] .col')
        name = self.remote("origin").locator(".name").bounding_box()
        local = self.box('#branchPop .option.blk[data-refs^="dev"] .col')
        self.assertAlmostEqual(col["x"], name["x"], delta=0.5)
        self.assertGreater(col["x"], local["x"] + 16)

    def test_toggle_one(self) -> None:
        """Az `upstream` kikapcsolva halvány fejléc, az ágai és a felhői eltűnnek a menüből és a
        gráfból, az `origin` ágai látszanak, a menü nyitva marad."""
        self.assertGreater(self.page.locator("#rows .badge", has_text="upstream").count(), 0)
        self.toggle_remote("upstream")
        head = self.remote("upstream")
        self.assertEqual(head.locator('[role="switch"]').get_attribute("aria-checked"), "false")
        self.assertLess(float(self.style('#branchPop .menu-remote[data-remote="upstream"] .name', "opacity")), 1)
        self.assertEqual(self.page.locator('#branchPop .option.blk[data-refs*="upstream/"]').count(), 0)
        self.assertEqual(self.page.locator("#rows .badge", has_text="upstream").count(), 0)
        self.assertTrue(self.page.locator('#branchPop .option.blk[data-refs="origin/test-branch-origin"]').is_visible())
        self.assertTrue(self.page.locator("#branchPop").is_visible())

    def test_only_switch_clicks(self) -> None:
        """A fejléc nevére kattintva az `origin` bekapcsolva marad, a menü nyitva."""
        self.open_branches()
        self.remote("origin").locator(".name").click()
        self.settle()
        self.assertEqual(self.remote("origin").locator('[role="switch"]').get_attribute("aria-checked"), "true")
        self.assertTrue(self.page.locator("#branchPop").is_visible())

    def test_all_off(self) -> None:
        """Minden remote kikapcsolva: a menü első sora és a gomb felirata „Minden ág”, a gombon
        halvány áthúzott felhő; minden helyi ág és a helyi történet látszik."""
        self.toggle_remote("origin")
        self.toggle_remote("upstream")
        self.assertEqual(self.page.locator("#branchAll .name").inner_text(), "Minden ág")
        for name in ("dev", "main", "fix/scroll"):
            self.assertEqual(self.page.locator(f'#branchPop .option.blk[data-refs="{name}"]').count(), 1, name)
        self.close_menu()
        self.assertEqual(self.page.locator("#branchBtn .select-label").inner_text(), "Minden ág")
        off = self.page.locator("#branchBtn .cloud-off")
        self.assertTrue(off.is_visible())
        self.assertNotEqual(self.style("#branchBtn .cloud-off", "color"), self.style("#branchBtn", "color"))
        subjects = self.subjects()
        self.assertIn("dev: pusholatlan munka", subjects)
        self.assertIn("main-0-0: egy commit a fixture-ből", subjects)
        self.assertEqual(self.page.locator("#rows .badge.ref-remote").count(), 0)

    def test_partial_mark(self) -> None:
        """A kikapcsolt `upstream` mellett a kijelölt `dev` után halvány áthúzott felhő áll."""
        self.toggle_remote("upstream")
        self.close_menu()
        self.select("dev")
        order = self.page.locator("#branchBtn").evaluate(
            "b => [...b.querySelectorAll('.sel-item, .cloud-off')].map(e => e.className.baseVal ?? e.className)")
        self.assertEqual(len(order), 2)
        self.assertIn("cloud-off", order[1])

    def test_hide_selected_remote_ref(self) -> None:
        """A kijelölt `origin/test-branch-origin` az `origin` kikapcsolásakor kikerül a kijelölésből."""
        self.select("origin/test-branch-origin")
        self.assertEqual(self.items(), [["origin/test-branch-origin", True]])
        self.toggle_remote("origin")
        self.close_menu()
        self.assertEqual(self.page.locator("#branchBtn .sel-item").count(), 0)
        self.assertEqual(self.page.locator("#branchBtn .select-label").inner_text(), "Minden ág")


class SingleRemoteHeaderTest(PageTestCase):
    @classmethod
    def prepare(cls, repo: Path) -> None:
        add_origin(repo)

    def test_single_remote(self) -> None:
        """Egy remote-nál egy `origin` fejléc kapcsolóval, külön remote-szűrő nincs."""
        self.page.locator("#branchBtn").click()
        self.settle()
        head = self.page.locator("#branchPop .menu-remote")
        self.assertEqual(head.count(), 1)
        self.assertEqual(head.get_attribute("data-remote"), "origin")
        self.assertEqual(head.locator('[role="switch"]').count(), 1)
        self.assertEqual(self.page.locator("#remotesBtn").count(), 0)


class NoRemoteHeaderTest(PageTestCase):
    def test_no_remote(self) -> None:
        """Remote nélkül nincs remote-fejléc, és a gombon nincs áthúzott felhő."""
        self.page.locator("#branchBtn").click()
        self.settle()
        self.assertEqual(self.page.locator("#branchPop .menu-remote").count(), 0)
        self.assertEqual(self.page.locator("#branchBtn .cloud-off").count(), 0)
        self.assertTrue(self.page.locator("#branchPop .option.blk").first.is_visible())


# ── A szűrők állása repónként megmarad ───────────────────────────────────

class RemotePersistTest(HeaderCase):
    def test_reload(self) -> None:
        """A kikapcsolt `upstream` újratöltés után is kikapcsolt."""
        self.toggle_remote("upstream")
        self.close_menu()
        self.page.reload()
        self.page.wait_for_selector("#rows .row")
        self.settle()
        self.open_branches()
        self.assertEqual(self.remote("upstream").locator('[role="switch"]').get_attribute("aria-checked"), "false")

    def test_other_repo(self) -> None:
        """Az A repóban kikapcsolt `origin` a B repó lapján bekapcsolt."""
        self.toggle_remote("origin")
        self.close_menu()
        repos = Path(self.tmp.name).resolve() / ".git-graph" / "repos.json"
        repos.write_text(json.dumps({SLUG: str(self.repo), "masik": str(self.repo)}), encoding="utf-8")
        other = self.html.replace(f'"slug": "{SLUG}"', '"slug": "masik"')
        self.page.unroute(URL)
        self.page.route(URL, lambda route: route.fulfill(
            content_type="text/html", headers={"Content-Security-Policy": CSP},
            body=other))
        self.page.reload()
        self.page.wait_for_selector("#rows .row")
        self.settle()
        self.open_branches()
        self.assertEqual(self.remote("origin").locator('[role="switch"]').get_attribute("aria-checked"), "true")
