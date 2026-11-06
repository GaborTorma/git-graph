"""A merge-commitok a lapon: gyűrűs pont, a beolvasztott commitok összecsukása a merge alá,
merge-enkénti kibontás nyíllal, és a fogaskerék-menü „Merge-ek összecsukása” kapcsolója."""
from __future__ import annotations

import os
import shutil
import subprocess
import unittest
from pathlib import Path

from harness import DAY, T0, PageTestCase, git_in

MERGE = "Merge branch 'feat/login'"
INNER = "Merge branch 'feat/helper' into feat/login"


def login_history(repo: Path, *, tag: bool = False, remote: bool = False, inner: bool = False,
                  adjacent: bool = False) -> None:
    """A fixture-történet helyett: a `main`-en „Indulás”, „README javítás” és a `feat/login`
    merge-e; a beolvasztott ág („Login váz”, „Login űrlap”) branche törölve. Napok: az „Indulás” a
    0., a login-commitok az 1., a README és a merge a 2. napon.

    `tag`: „v0.9” a „Login váz”-on; `remote`: `origin/feat/login` a „Login űrlap”-on; `inner`: a
    login-ágba egy törölt segédág („Segédfüggvény”) merge-e; `adjacent`: a merge 2. szülője
    közvetlenül az „Indulás”-ból ágazik, más commit nélkül a `main`-en."""
    shutil.rmtree(repo)
    repo.mkdir()
    n = 0

    def git(*args: str, day: int = 0) -> None:
        nonlocal n
        n += 1
        date = f"@{T0 + day * DAY + n * 60} +0000"
        git_in(repo, *args, env={**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})

    def commit(subject: str, day: int) -> None:
        (repo / f"c{n}.txt").write_text(f"{subject}\n", encoding="utf-8")
        git("add", ".", day=day)
        git("commit", "-qm", subject, day=day)

    git("init", "-q", "-b", "main")
    commit("Indulás", 0)
    if adjacent:
        git("switch", "-q", "-c", "feat/login", day=1)
        commit("Login váz", 1)
        git("switch", "-q", "main", day=1)
        git("merge", "-q", "--no-ff", "-m", MERGE, "feat/login", day=1)
        git("branch", "-q", "-D", "feat/login", day=1)
        return
    git("switch", "-q", "-c", "feat/login", day=1)
    commit("Login váz", 1)
    if tag:
        git("tag", "v0.9", day=1)
    if inner:
        git("switch", "-q", "-c", "feat/helper", day=1)
        commit("Segédfüggvény", 1)
        git("switch", "-q", "feat/login", day=1)
        git("merge", "-q", "--no-ff", "-m", INNER, "feat/helper", day=1)
        git("branch", "-q", "-D", "feat/helper", day=1)
    commit("Login űrlap", 1)
    if remote:
        git("remote", "add", "origin", "https://example.invalid/fixture.git", day=1)
        git("update-ref", "refs/remotes/origin/feat/login", "HEAD", day=1)
    git("switch", "-q", "main", day=2)
    commit("README javítás", 2)
    git("merge", "-q", "--no-ff", "-m", MERGE, "feat/login", day=2)
    git("branch", "-q", "-D", "feat/login", day=2)


# A gráf élei: a kezdő- és végpont Y-ja (az SVG koordinátáiban) és a szaggatás.
EDGES = """() => [...document.querySelectorAll('#lanes path')].map(p => {
  const n = p.getAttribute('d').match(/-?[\\d.]+/g).map(Number);
  return { y1: n[1], y2: n.at(-1), dash: p.getAttribute('stroke-dasharray') };
})"""

# Egy sor közepének Y-ja a gráf SVG-jében.
ROW_MID = """subject => {
  const row = [...document.querySelectorAll('#rows .row')]
    .find(r => r.querySelector('.subject').textContent === subject);
  const r = row.getBoundingClientRect(), s = document.querySelector('#lanes').getBoundingClientRect();
  return r.top + r.height / 2 - s.top;
}"""

# A sor közepének magasságában ülő körök a gráfban.
DOTS_AT = """subject => {
  const row = [...document.querySelectorAll('#rows .row')]
    .find(r => r.querySelector('.subject').textContent === subject);
  const r = row.getBoundingClientRect(), mid = r.top + r.height / 2;
  return [...document.querySelectorAll('#lanes circle')].filter(c => {
    const b = c.getBoundingClientRect();
    return Math.abs(b.top + b.height / 2 - mid) < 1;
  }).map(c => ({ r: c.getAttribute('r'), fill: c.getAttribute('fill'), stroke: c.getAttribute('stroke'),
                 width: c.getAttribute('stroke-width'), opacity: c.getAttribute('opacity') }));
}"""

ACCENT = """() => { const d = document.createElement('span'); d.style.color = 'var(--accent)';
  document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; }"""


class MergeCase(PageTestCase):
    """A login-történet egy változatán (`HISTORY`: a `login_history` kapcsolói)."""

    HISTORY: dict = {}

    @classmethod
    def prepare(cls, repo: Path) -> None:
        login_history(repo, **cls.HISTORY)

    def subjects(self) -> list[str]:
        return self.page.locator("#rows .row .subject").all_inner_texts()

    def row(self, subject: str):
        return self.page.locator("#rows .row", has=self.page.locator(".subject", has_text=subject)).first

    def expand(self, subject: str = MERGE) -> None:
        row = self.row(subject)
        row.hover()
        row.locator(".merge-chev").click()
        self.settle()


class MergeDotTest(MergeCase):
    HISTORY = {"remote": True}            # a beolvasztott ág látszik: a sima commit sora is ott van

    @classmethod
    def prepare(cls, repo: Path) -> None:
        super().prepare(repo)
        (repo / "c1.txt").write_text("félretéve\n", encoding="utf-8")
        git_in(repo, "stash", "push", "-q", "-m", "félretéve")
        (repo / "c1.txt").write_text("módosítva\n", encoding="utf-8")

    def test_ring(self) -> None:
        """A merge pontja 3,5 px sugarú telt mag, körülötte 6 px sugarú, 2 px-es gyűrű háttérszínű
        réssel; a subject színe a sima commité."""
        dots = self.page.evaluate(DOTS_AT, MERGE)
        ring = next(d for d in dots if d["r"] == "6")
        core = next(d for d in dots if d["r"] == "3.5")
        self.assertEqual((ring["width"], ring["fill"]), ("2", "var(--bg)"))
        self.assertEqual(core["fill"], ring["stroke"])
        color = "el => getComputedStyle(el).color"
        self.assertEqual(self.row(MERGE).locator(".subject").evaluate(color),
                         self.row("README javítás").locator(".subject").evaluate(color))

    def test_wip_and_stash_hollow(self) -> None:
        """Az Uncommitted sor és a stash pontja üres karika marad."""
        stash = self.page.evaluate(DOTS_AT, "On main: félretéve")
        self.assertIn({"r": "5", "fill": "var(--bg)"}, [{"r": d["r"], "fill": d["fill"]} for d in stash])
        pend = self.page.locator("#pending .pend-lane circle")
        self.assertEqual((pend.get_attribute("r"), pend.get_attribute("fill")), ("5", "var(--bg)"))


class FreshMergeTest(MergeCase):
    HISTORY = {"remote": True}

    def test_fresh_halo(self) -> None:
        """A lap megnyitása óta érkezett merge udvara 10 px, a vele érkezett sima commité 8 px."""
        git_in(self.repo, "switch", "-q", "-c", "feat/uj")
        (self.repo / "uj.txt").write_text("új\n", encoding="utf-8")
        git_in(self.repo, "add", ".")
        git_in(self.repo, "commit", "-qm", "Új funkció")
        git_in(self.repo, "switch", "-q", "main")
        git_in(self.repo, "merge", "-q", "--no-ff", "-m", "Merge branch 'feat/uj'", "feat/uj")
        self.poke()
        halo = lambda s: [d["r"] for d in self.page.evaluate(DOTS_AT, s) if d["opacity"] == ".28"]  # noqa: E731
        self.assertEqual(halo("Merge branch 'feat/uj'"), ["10"])
        self.assertEqual(halo("Új funkció"), ["8"])


class CollapseTest(MergeCase):
    def test_hidden_rows(self) -> None:
        """A törölt branch commitjai a merge alá csukódnak; a merge-soron akcentuskék „+2”, háttér nélkül."""
        self.assertEqual(self.subjects(), [MERGE, "README javítás", "Indulás"])
        n = self.row(MERGE).locator(".merge-n")
        self.assertEqual(n.inner_text(), "+2")
        self.assertEqual(n.evaluate("el => getComputedStyle(el).color"), self.page.evaluate(ACCENT))
        self.assertEqual(n.evaluate("el => getComputedStyle(el).backgroundColor"), "rgba(0, 0, 0, 0)")

    def test_day_header(self) -> None:
        """A csupa rejtett commitból álló napnak nincs fejléce; kibontás után visszajön."""
        self.assertEqual(self.page.locator("#rows .day").count(), 2)
        self.expand()
        self.assertEqual(self.page.locator("#rows .day").count(), 3)

    def test_hover_chevron(self) -> None:
        """Hoverkor a subject előtt, a gráfoszlop jobb szélén jobbra mutató nyíl; a subject nem mozdul."""
        row = self.row(MERGE)
        chev = row.locator(".merge-chev")
        x = row.locator(".subject").bounding_box()["x"]
        self.assertEqual(chev.evaluate("el => getComputedStyle(el).opacity"), "0")
        row.hover()
        self.settle()
        self.assertEqual(chev.evaluate("el => getComputedStyle(el).opacity"), "1")
        self.assertEqual(chev.get_attribute("aria-expanded"), "false")
        box, inner = chev.bounding_box(), row.locator(".row-in").bounding_box()
        self.assertAlmostEqual(box["x"] + box["width"], inner["x"], delta=1)
        self.assertEqual(row.locator(".subject").bounding_box()["x"], x)

    def test_expand(self) -> None:
        """A nyílra kattintva a beolvasztott commitok szerverhívás nélkül, 50 ms-on belül, 150 ms-os
        lenyílással a merge alá kerülnek; a merge-sor a helyén marad, a panel nem nyílik."""
        row = self.row(MERGE)
        top = row.bounding_box()["y"]
        row.hover()
        res = row.locator(".merge-chev").evaluate("""el => {
          const t = performance.now();
          el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          const ms = performance.now() - t;
          const rows = [...document.querySelectorAll('#rows .row')]
            .filter(r => r.querySelector('.subject').textContent.startsWith('Login'));
          return { ms, n: rows.length, anim: rows.map(r => getComputedStyle(r).animationDuration) };
        }""")
        self.assertLess(res["ms"], 50)
        self.assertEqual(res["n"], 2)
        self.assertEqual(res["anim"], ["0.15s", "0.15s"])
        self.settle()
        self.assertEqual(self.subjects(), [MERGE, "README javítás", "Login űrlap", "Login váz", "Indulás"])
        self.assertEqual(self.row(MERGE).bounding_box()["y"], top)
        self.assertEqual(self.row(MERGE).locator(".merge-chev").get_attribute("aria-expanded"), "true")
        self.assertEqual(self.row(MERGE).locator(".merge-n").count(), 0)
        self.assertEqual(self.page.locator("#rows .details").count(), 0)

    def test_count_opens_panel(self) -> None:
        """A „+2”-re kattintás a merge commit-paneljét nyitja, a merge összecsukva marad."""
        self.row(MERGE).locator(".merge-n").click()
        self.settle()
        self.assertEqual(self.page.locator("#rows .details").count(), 1)
        self.assertEqual(self.row(MERGE).get_attribute("aria-expanded"), "true")
        self.assertNotIn("Login űrlap", self.subjects())

    def test_reload_collapses(self) -> None:
        """A kézi kibontás csak az újratöltésig él."""
        self.expand()
        self.assertIn("Login űrlap", self.subjects())
        self.page.reload()
        self.page.wait_for_selector("#rows .row")
        self.settle()
        self.assertEqual(self.subjects(), [MERGE, "README javítás", "Indulás"])

    def test_arrow_key_keeps_collapsed(self) -> None:
        """A jobbra nyíl a kijelölt merge-soron nem bont ki."""
        self.row(MERGE).focus()
        self.page.keyboard.press("ArrowRight")
        self.settle()
        self.assertNotIn("Login űrlap", self.subjects())
        self.assertEqual(self.row(MERGE).locator(".merge-chev").get_attribute("aria-expanded"), "false")

    def test_search_reveals(self) -> None:
        """A rejtett commitra illő keresés kibontja a merge-et: a commit találatként látszik."""
        self.page.locator("#searchBtn").click()
        self.page.locator("#search").fill("Login űrlap")
        self.settle()
        self.assertEqual(self.subjects(), ["Login űrlap"])
        self.page.locator("#search").press("Escape")
        self.settle()
        self.assertIn("Login űrlap", self.subjects())
        self.assertEqual(self.row(MERGE).locator(".merge-chev").get_attribute("aria-expanded"), "true")

    def test_edges(self) -> None:
        """Az elrejtett ág éle szaggatott: a merge-ből az ág kiindulópontjáig."""
        edges = self.page.evaluate(EDGES)
        merge, start = self.page.evaluate(ROW_MID, MERGE), self.page.evaluate(ROW_MID, "Indulás")
        dashed = [e for e in edges if abs(e["y1"] - merge) < 1 and abs(e["y2"] - start) < 1 and e["dash"]]
        self.assertEqual(len(dashed), 1)


class RemoteRefTest(MergeCase):
    HISTORY = {"remote": True}

    def test_ref_chain_visible(self) -> None:
        """A megmaradt `origin/feat/login` lánca látszik, a merge-soron nincs szám."""
        self.assertIn("Login űrlap", self.subjects())
        self.assertIn("Login váz", self.subjects())
        self.assertEqual(self.row(MERGE).locator(".merge-n").count(), 0)


class TagTest(MergeCase):
    HISTORY = {"tag": True}

    def test_tag_visible(self) -> None:
        """A tages „Login váz” a chipjével látszik, a „Login űrlap” rejtett, a merge száma „+1”."""
        self.assertEqual(self.subjects(), [MERGE, "README javítás", "Login váz", "Indulás"])
        self.assertEqual(self.row("Login váz").locator(".badge", has_text="v0.9").count(), 1)
        self.assertEqual(self.row(MERGE).locator(".merge-n").inner_text(), "+1")

    def test_edges(self) -> None:
        """A merge-től a „Login váz”-ig szaggatott (átugorja a rejtettet), onnan az „Indulás”-ig folytonos."""
        edges = self.page.evaluate(EDGES)
        mid = {s: self.page.evaluate(ROW_MID, s) for s in (MERGE, "Login váz", "Indulás")}
        find = lambda a, b: [e for e in edges if abs(e["y1"] - mid[a]) < 1 and abs(e["y2"] - mid[b]) < 1]  # noqa: E731
        self.assertEqual([e["dash"] for e in find(MERGE, "Login váz")], ["2 2"])
        self.assertEqual([e["dash"] for e in find("Login váz", "Indulás")], [None])


class AdjacentTest(MergeCase):
    HISTORY = {"adjacent": True}

    def test_no_edge(self) -> None:
        """A közvetlenül a merge alatti sorból ágazó, rejtett 2. szülő felé nem indul él."""
        self.assertEqual(self.subjects(), [MERGE, "Indulás"])
        merge = self.page.evaluate(ROW_MID, MERGE)
        self.assertEqual(len([e for e in self.page.evaluate(EDGES) if abs(e["y1"] - merge) < 1]), 1)


class InnerMergeTest(MergeCase):
    HISTORY = {"inner": True}

    def test_inner_follows_default(self) -> None:
        """A külső merge kibontásakor a belső merge összecsukva jelenik meg, saját számmal; a külső
        száma csak a közvetlenül megjelenő sorokat számolta."""
        self.assertEqual(self.row(MERGE).locator(".merge-n").inner_text(), "+3")
        self.expand()
        self.assertEqual(self.subjects(),
                         [MERGE, "README javítás", "Login űrlap", INNER, "Login váz", "Indulás"])
        inner = self.row(INNER)
        self.assertEqual(inner.locator(".merge-n").inner_text(), "+1")
        self.assertEqual(inner.locator(".merge-chev").get_attribute("aria-expanded"), "false")


class LiveTest(MergeCase):
    def test_live_keeps_override(self) -> None:
        """Új commit érkezésekor a kézzel kibontott merge kibontva marad."""
        self.expand()
        (self.repo / "elo.txt").write_text("élő\n", encoding="utf-8")
        git_in(self.repo, "add", ".")
        git_in(self.repo, "commit", "-qm", "Élő commit")
        self.poke()
        self.assertEqual(self.subjects()[0], "Élő commit")
        self.assertIn("Login űrlap", self.subjects())


class SettingTest(MergeCase):
    """A fogaskerék-menü kapcsolója a repó `.git/config`-ját írja: tesztenként alapállapotból."""

    def setUp(self) -> None:
        unset_collapse(self.repo)
        super().setUp()

    def toggle(self) -> None:
        if self.page.locator("#settingsPop").is_hidden():
            self.page.locator("#settingsBtn").click()
        opt = self.page.locator('#settingsPop .option[data-key="collapseMerges"]:not([disabled])')
        opt.click()
        self.settle()

    def test_switch_off(self) -> None:
        """A kapcsoló kikapcsolva minden beolvasztott commitot mutat, szám nélkül, és a repóba írja."""
        opt = self.page.locator("#settingsBtn")
        opt.click()
        item = self.page.locator('#settingsPop .option[data-key="collapseMerges"]')
        self.assertEqual(item.locator(".name").inner_text(), "Merge-ek összecsukása")
        self.assertEqual(item.locator(".sub").inner_text(), "A beolvasztott commitok a merge alatt")
        self.toggle()
        self.assertEqual(self.subjects(), [MERGE, "README javítás", "Login űrlap", "Login váz", "Indulás"])
        self.assertEqual(self.page.locator("#rows .merge-n").count(), 0)
        self.until(lambda: "collapsemerges = false" in (self.repo / ".git" / "config").read_text().lower(),
                   "a .git/config kulcsa")

    def test_switch_clears_overrides(self) -> None:
        """A kapcsoló váltása törli a merge-enként kézzel nyitott állapotot."""
        self.expand()
        self.toggle()
        self.toggle()
        self.assertNotIn("Login űrlap", self.subjects())

    def test_open_panel_stays(self) -> None:
        """Ha a nyitott panel commitja rejtetté válna, a merge-e kibontva marad, a panel nyitva."""
        self.toggle()
        self.page.keyboard.press("Escape")
        self.row("Login űrlap").click()
        self.settle()
        self.toggle()
        self.assertIn("Login űrlap", self.subjects())
        self.assertEqual(self.row("Login űrlap").get_attribute("aria-expanded"), "true")
        self.assertEqual(self.page.locator("#rows .details").count(), 1)


def unset_collapse(repo: Path) -> None:
    """A `git-graph.collapseMerges` kulcs törlése (ha nincs, nem hiba: a kilépési kód 5)."""
    try:
        git_in(repo, "config", "--local", "--unset", "git-graph.collapseMerges")
    except subprocess.CalledProcessError as exc:
        if exc.returncode != 5:
            raise


class FirstDrawTest(MergeCase):
    # Minden DOM-változáskor: látszott-e a merge összecsukva (a „Login űrlap” nélkül).
    INIT = f"""window.__flash = false;
new MutationObserver(() => {{
  const s = [...document.querySelectorAll('#rows .row .subject')].map(e => e.textContent);
  if (s.includes({MERGE!r}) && !s.includes('Login űrlap')) window.__flash = true;
}}).observe(document, {{ subtree: true, childList: true }});"""

    @classmethod
    def prepare(cls, repo: Path) -> None:
        super().prepare(repo)
        git_in(repo, "config", "--local", "git-graph.collapseMerges", "false")

    def test_first_draw_expanded(self) -> None:
        """Kikapcsolt beállítású repóban az első lista már kibontott, nem villan fel összecsukva."""
        self.assertEqual(self.subjects(), [MERGE, "README javítás", "Login űrlap", "Login váz", "Indulás"])
        self.assertFalse(self.page.evaluate("window.__flash"))


if __name__ == "__main__":
    unittest.main()
