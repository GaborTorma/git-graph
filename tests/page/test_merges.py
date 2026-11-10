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
STACKED = "Merge branch 'feat/profile'"


def login_history(repo: Path, *, tag: bool = False, remote: bool = False, inner: bool = False,
                  adjacent: bool = False, fork: bool = False, stacked: bool = False, start_day: int = 0) -> None:
    """A fixture-történet helyett: a `main`-en „Indulás”, „README javítás” és a `feat/login`
    merge-e; a beolvasztott ág („Login váz”, „Login űrlap”) branche törölve. Napok: az „Indulás” a
    0., a login-commitok az 1., a README és a merge a 2. napon.

    `tag`: „v0.9” a „Login váz”-on; `remote`: `origin/feat/login` a „Login űrlap”-on; `inner`: a
    login-ágba egy törölt segédág („Segédfüggvény”) merge-e; `adjacent`: a merge 2. szülője
    közvetlenül az „Indulás”-ból ágazik, más commit nélkül a `main`-en; `fork`: a „Login váz”-ból
    leágazó, megmaradt `side` branch egy „Mellékág” committal; `start_day`: az „Indulás” napja
    (1-nél a login-commitokkal egy napon, köztük nincs napfejléc); `stacked`: a login-ág csúcsára
    épülő `feat/profile` („Profil oldal”, az 1. napon), külön merge-dzsel a login merge-e után (3. nap)."""
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
    commit("Indulás", start_day)
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
    if fork:
        git("switch", "-q", "-c", "side", day=1)
        commit("Mellékág", 1)
        git("switch", "-q", "feat/login", day=1)
    commit("Login űrlap", 1)
    if remote:
        git("remote", "add", "origin", "https://example.invalid/fixture.git", day=1)
        git("update-ref", "refs/remotes/origin/feat/login", "HEAD", day=1)
    if stacked:
        git("switch", "-q", "-c", "feat/profile", day=1)
        commit("Profil oldal", 1)
    git("switch", "-q", "main", day=2)
    commit("README javítás", 2)
    git("merge", "-q", "--no-ff", "-m", MERGE, "feat/login", day=2)
    git("branch", "-q", "-D", "feat/login", day=2)
    if stacked:
        git("merge", "-q", "--no-ff", "-m", STACKED, "feat/profile", day=3)
        git("branch", "-q", "-D", "feat/profile", day=3)


# A gráf élei: a kezdő- és végpont Y-ja (az SVG koordinátáiban) és a szaggatás.
EDGES = """() => [...document.querySelectorAll('#lanes path')].map(p => {
  const n = p.getAttribute('d').match(/-?[\\d.]+/g).map(Number);
  return { y1: n[1], y2: n.at(-1), dash: p.getAttribute('stroke-dasharray') };
})"""

# A gráf éleinek összes koordinátája (x, y párok sorban) és a szaggatás.
PATHS = """() => [...document.querySelectorAll('#lanes path')].map(p => ({
  n: p.getAttribute('d').match(/-?[\\d.]+/g).map(Number), dash: p.getAttribute('stroke-dasharray') }))"""

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

def rotation(loc) -> list[int]:
    """Egy elem `transform`-mátrixának forgató része (a, b, c, d), egészre kerekítve."""
    m = loc.evaluate("el => getComputedStyle(el).transform")
    return [round(float(v)) for v in m[7:-1].split(",")[:4]]


BG = """() => getComputedStyle(document.body).backgroundColor"""

# Egy CSS-szín (pl. `var(--lane-1)`) kiszámolt értéke.
COLOR_OF = """c => { const d = document.createElement('span'); d.style.color = c;
  document.body.append(d); const v = getComputedStyle(d).color; d.remove(); return v; }"""


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
        row.locator(".merge-hit").hover(position={"x": 4, "y": 4})
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
        réssel; a subject színe a sima commité, a vastagsága picit nagyobb."""
        dots = self.page.evaluate(DOTS_AT, MERGE)
        ring = next(d for d in dots if d["r"] == "6")
        self.assertIn("3.5", [d["r"] for d in dots])
        self.assertEqual((ring["width"], ring["fill"]), ("2", "var(--bg)"))
        style = "el => { const s = getComputedStyle(el); return [s.color, +s.fontWeight]; }"
        merge, plain = (self.row(s).locator(".subject").evaluate(style) for s in (MERGE, "README javítás"))
        self.assertEqual(merge[0], plain[0])
        self.assertGreater(merge[1], plain[1])

    def test_core_color(self) -> None:
        """A merge pontja egyszínű: a mag és a gyűrű a merge sávjának színe."""
        dots = self.page.evaluate(DOTS_AT, MERGE)
        ring = next(d for d in dots if d["r"] == "6")
        core = next(d for d in dots if d["r"] == "3.5")
        readme = self.page.evaluate(DOTS_AT, "README javítás")[0]
        self.assertEqual(ring["stroke"], readme["fill"])
        self.assertEqual(core["fill"], ring["stroke"])

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
        """A törölt branch commitjai a merge alá csukódnak; a merge-soron „+2” és a nyíl a beolvasztott ág
        színében; a szám halvány, tint hátterű kis címke kerettel, a nyílnak nincs háttere."""
        self.assertEqual(self.subjects(), [MERGE, "README javítás", "Indulás"])
        n = self.row(MERGE).locator(".merge-n")
        self.assertEqual(n.inner_text(), "+2")
        bg = "el => getComputedStyle(el).backgroundColor"
        self.assertNotIn(n.evaluate(bg), ("rgba(0, 0, 0, 0)", self.page.evaluate(BG)))
        self.assertIn("inset", n.evaluate("el => getComputedStyle(el).boxShadow"))
        self.assertEqual(self.row(MERGE).locator(".merge-chev").evaluate(bg), "rgba(0, 0, 0, 0)")
        color = "el => getComputedStyle(el).color"
        chev = self.row(MERGE).locator(".merge-chev")
        ring = self.page.evaluate(COLOR_OF, self.page.locator("#lanes circle[r='6']").get_attribute("stroke"))
        self.assertEqual(chev.evaluate(color), n.evaluate(color))
        self.assertNotEqual(n.evaluate(color), ring)
        self.expand()
        branch = self.page.evaluate(DOTS_AT, "Login űrlap")[0]["fill"]
        self.assertEqual(chev.evaluate(color), self.page.evaluate(COLOR_OF, branch))

    def test_day_header(self) -> None:
        """A csupa rejtett commitból álló napnak nincs fejléce; kibontás után visszajön."""
        self.assertEqual(self.page.locator("#rows .day").count(), 2)
        self.expand()
        self.assertEqual(self.page.locator("#rows .day").count(), 3)

    def test_hover_chevron(self) -> None:
        """A merge pontja mellett „+2”, utána hoverkor jobbra mutató nyíl, mind a gráfoszlopban; a
        subject végén nincs szám, és a hoverre nem mozdul."""
        row = self.row(MERGE)
        chev, n = row.locator(".merge-chev"), row.locator(".merge-n")
        x = row.locator(".subject").bounding_box()["x"]
        self.assertEqual(row.locator(".desc .merge-n").count(), 0)
        self.assertEqual(chev.evaluate("el => getComputedStyle(el).opacity"), "0")
        row.hover()                                            # a sor sávja: a nyíl nem jelenik meg
        self.settle()
        self.assertEqual(chev.evaluate("el => getComputedStyle(el).opacity"), "0")
        row.locator(".merge-hit").hover(position={"x": 4, "y": 4})
        self.settle()
        self.assertEqual(chev.evaluate("el => getComputedStyle(el).opacity"), "1")
        self.assertEqual(chev.get_attribute("aria-expanded"), "false")
        # a lenyíló menü 16 px-es CaretDown-ja, jobbra fordítva (−90°)
        self.assertEqual(chev.locator(".ic").evaluate("el => [el.clientWidth, el.clientHeight]"), [16, 16])
        self.assertEqual(rotation(chev.locator(".ic")), [0, -1, 1, 0])
        dot = self.page.locator("#lanes circle[r='6']").bounding_box()
        nb, cb, inner = n.bounding_box(), chev.bounding_box(), row.locator(".row-in").bounding_box()
        self.assertAlmostEqual(nb["x"], dot["x"] + dot["width"] + 2, delta=2)   # a gyűrű mellett
        self.assertAlmostEqual(cb["x"], nb["x"] + nb["width"], delta=2)         # a szám után
        self.assertLessEqual(cb["x"] + cb["width"], inner["x"] + 1)               # a gráfoszlopban
        # a nyíl után csak a sor paddingje (10 px) a subjectig: a gráfoszlop a nyílig ér
        self.assertAlmostEqual(row.locator(".subject").bounding_box()["x"] - (cb["x"] + cb["width"]), 10, delta=2)
        self.assertEqual(row.locator(".subject").bounding_box()["x"], x)

    def test_expand(self) -> None:
        """A nyílra kattintva a beolvasztott commitok szerverhívás nélkül, 50 ms-on belül, 150 ms-os
        lenyílással a merge alá kerülnek; a merge-sor a helyén marad, a panel nem nyílik."""
        row = self.row(MERGE)
        top = row.bounding_box()["y"]
        row.locator(".merge-hit").hover(position={"x": 4, "y": 4})
        res = row.locator(".merge-chev").evaluate("""el => {
          const t = performance.now();
          el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          const ms = performance.now() - t;
          const rows = [...document.querySelectorAll('#rows .row')]
            .filter(r => r.querySelector('.subject').textContent.startsWith('Login'));
          return { ms, n: rows.length, anim: rows.map(r => r.getAnimations().map(a => a.effect.getTiming().duration)) };
        }""")
        self.assertLess(res["ms"], 50)
        self.assertEqual(res["n"], 2)
        self.assertEqual(res["anim"], [[200], [200]])             # a sorok magassága 0-ról nő
        self.settle()
        self.assertEqual(self.subjects(), [MERGE, "README javítás", "Login űrlap", "Login váz", "Indulás"])
        self.assertEqual(self.row(MERGE).bounding_box()["y"], top)
        self.assertEqual(self.row(MERGE).locator(".merge-chev").get_attribute("aria-expanded"), "true")
        self.assertEqual(self.row(MERGE).locator(".merge-n").count(), 0)
        self.assertEqual(self.page.locator("#rows .details").count(), 0)
        # kibontva a nyíl felfelé mutat (a CaretDown 180°-kal elforgatva)
        self.assertEqual(rotation(self.row(MERGE).locator(".merge-chev .ic")), [-1, 0, 0, -1])

    def test_expanded_chevron_between_lanes(self) -> None:
        """Kibontva a nyíl közepe pont a merge melletti két sáv (+1 és +2) között áll."""
        # Adott egy kibontott merge
        self.expand()
        # Ha a nyíl látszik (hover)
        row = self.row(MERGE)
        row.locator(".merge-hit").hover(position={"x": 4, "y": 4})
        self.settle()
        # Akkor a közepe a merge sávjától 1,5 sávnyira (21 px) van; a `.merge-fold` a sávtól 10 px-re kezdődik
        fold, ic = (row.locator(s).bounding_box() for s in (".merge-fold", ".merge-chev .ic"))
        self.assertAlmostEqual(ic["x"] + ic["width"] / 2 - (fold["x"] - 10), 1.5 * 14, delta=0.5)

    def test_graph_column_expands(self) -> None:
        """A merge gráfoszlopára (a „+2”-re is) kattintás a merge-et bontja ki, a panelt nem nyitja."""
        self.row(MERGE).locator(".merge-n").click()
        self.settle()
        self.assertIn("Login űrlap", self.subjects())
        self.assertEqual(self.page.locator("#rows .details").count(), 0)
        self.row(MERGE).locator(".merge-hit").click(position={"x": 4, "y": 4})
        self.settle()
        self.assertNotIn("Login űrlap", self.subjects())

    def test_collapse_animates(self) -> None:
        """Összecsukáskor a beolvasztott sorok 200 ms alatt felcsukódnak, és csak utána tűnnek el."""
        self.expand()
        res = self.row(MERGE).locator(".merge-hit").evaluate("""el => {
          el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          return [...document.querySelectorAll('#rows .row')]
            .filter(r => r.querySelector('.subject').textContent.startsWith('Login'))
            .map(r => r.getAnimations().map(a => a.effect.getTiming().duration));
        }""")
        self.assertEqual(res, [[200], [200]])
        self.settle()
        self.assertEqual(self.subjects(), [MERGE, "README javítás", "Indulás"])
        self.assertEqual(self.row(MERGE).locator(".merge-n").inner_text(), "+2")

    def test_collapse_fades_to_dotted(self) -> None:
        """Összecsukáskor a pontozott él a felcsukódás alatt beúszik, a felcsukódó ág élei és
        pöttyei kihalványulnak: a végén nincs ugrás."""
        # Adott egy kibontott merge
        self.expand()
        # Ha a User összecsukja, és a felcsukódás félúton tart
        res = self.row(MERGE).locator(".merge-hit").evaluate("""async el => {
          el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          const anim = [...document.querySelectorAll('#rows .row')]
            .find(r => r.querySelector('.subject').textContent.startsWith('Login')).getAnimations()[0];
          anim.pause(); anim.currentTime = 100;
          await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
          const fold = [...document.querySelectorAll('#lanes path.fold')].map(p => Number(p.getAttribute('opacity') ?? 1));
          const faded = [...document.querySelectorAll('#lanes [opacity]')].filter(e => !e.matches('.fold'))
            .map(e => Number(e.getAttribute('opacity')));
          anim.play();
          return { fold, faded };
        }""")
        # Akkor a pontozott él már ott van, de még nem teljes; a régi ág halványul
        self.assertEqual(len(res["fold"]), 1)
        self.assertTrue(0 < res["fold"][0] < 1, res)
        self.assertTrue(res["faded"] and all(0 < o < 1 for o in res["faded"]), res)
        # És a végén a pontozott él teljes, halványított elem nem marad
        self.settle()
        self.assertEqual(self.page.locator("#lanes path.fold").get_attribute("opacity"), None)
        self.assertEqual(self.page.locator("#lanes [opacity]:not(circle)").count(), 0)

    def test_expand_fades_from_dotted(self) -> None:
        """Kibontáskor fordítva: a pontozott él a lenyílás alatt halványul el, a lenyíló ág élei és
        pöttyei beúsznak."""
        # Adott egy összecsukott merge
        # Ha a User kibontja, és a lenyílás félúton tart
        row = self.row(MERGE)
        row.locator(".merge-hit").hover(position={"x": 4, "y": 4})
        res = row.locator(".merge-chev").evaluate("""async el => {
          el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          const anim = [...document.querySelectorAll('#rows .row')]
            .find(r => r.querySelector('.subject').textContent.startsWith('Login')).getAnimations()[0];
          anim.pause(); anim.currentTime = 100;
          await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
          const fold = [...document.querySelectorAll('#lanes path.fold')].map(p => Number(p.getAttribute('opacity') ?? 1));
          const faded = [...document.querySelectorAll('#lanes [opacity]')].filter(e => !e.matches('.fold'))
            .map(e => Number(e.getAttribute('opacity')));
          anim.play();
          return { fold, faded };
        }""")
        # Akkor a pontozott él még látszik, de halványul; az új ág beúszik
        self.assertEqual(len(res["fold"]), 1)
        self.assertTrue(0 < res["fold"][0] < 1, res)
        self.assertTrue(res["faded"] and all(0 < o < 1 for o in res["faded"]), res)
        # És a végén nincs pontozott él, halványított elem sem
        self.settle()
        self.assertEqual(self.page.locator("#lanes path.fold").count(), 0)
        self.assertEqual(self.page.locator("#lanes [opacity]:not(circle)").count(), 0)

    def test_collapse_morph(self) -> None:
        """Összecsukáskor a felcsukódással együtt (200 ms) a nyíl a helyéről jobbra fordul, és a szám
        balról jobbra nő, maga előtt tolva a nyilat; a végén a nyíl a szám után áll."""
        self.expand()
        hit = self.row(MERGE).locator(".merge-hit")
        hit.hover(position={"x": 4, "y": 4})
        res = hit.evaluate("""el => {
          el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          const n = el.querySelector('.merge-n'), chev = el.querySelector('.merge-chev');
          const anim = e => e.getAnimations().map(a => [a.effect.getKeyframes()[0], a.effect.getTiming().duration]);
          const rows = [...document.querySelectorAll('#rows .row')]
            .filter(r => r.querySelector('.subject').textContent.startsWith('Login'));
          const fade = n.getAnimations()[0].effect.getKeyframes().map(k => [k.computedOffset, k.opacity]);
          return { fade, n: anim(n).map(([k, d]) => [k.width, d]), rot: anim(chev.firstElementChild).map(([k, d]) => [k.transform, d]),
                   rows: rows.map(r => r.getAnimations().map(a => a.effect.getTiming().duration)) };
        }""")
        self.assertEqual(res["n"], [["0px", 200]])                         # a szám rögtön, 0-ról nő
        self.assertEqual(res["fade"], [[0, "0.2"], [0.5, "1"], [1, "1"]])  # 20 %-ról, félúton teljes
        self.assertEqual(res["rot"], [["rotate(-180deg)", 200]])           # a nyíl felfelől fordul
        self.assertEqual(res["rows"], [[200], [200]])                      # a sorokkal együtt ér véget
        self.settle()
        nb, cb = (self.row(MERGE).locator(s).bounding_box() for s in (".merge-n", ".merge-chev"))
        self.assertAlmostEqual(cb["x"], nb["x"] + nb["width"] + 1, delta=1.5)   # a végleges helyén
        self.assertEqual(self.row(MERGE).locator(".merge-n").count(), 1)

    def test_no_flash_after_redraw(self) -> None:
        """Az újrarajzolt merge-sor nyila rögtön látszik (a gráfoszlop fölött marad az egér): sem
        összecsukás, sem kibontás után nem villan ki és vissza."""
        hit = self.row(MERGE).locator(".merge-hit")
        hit.hover(position={"x": 4, "y": 4})
        js = """async el => {
          const old = document.querySelector('#rows .row');
          el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          while (document.querySelector('#rows .row') === old) await new Promise(r => requestAnimationFrame(r));
          return getComputedStyle(document.querySelector('#rows .row .merge-chev')).opacity;
        }"""
        self.assertEqual(hit.evaluate(js), "1")              # kibontás
        self.settle()
        hit = self.row(MERGE).locator(".merge-hit")
        self.assertEqual(hit.evaluate(js), "1")              # összecsukás

    def test_expand_rotates(self) -> None:
        """Kibontáskor a nyíl 90°-ot fordul jobbról felfelé (szöggel, nem tükrözve), 200 ms alatt."""
        hit = self.row(MERGE).locator(".merge-hit")
        hit.hover(position={"x": 4, "y": 4})
        rot = hit.evaluate("""el => {
          el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          const ic = document.querySelector('#rows .row .merge-chev .ic');
          return ic.getAnimations().map(a => [...a.effect.getKeyframes().map(k => k.transform), a.effect.getTiming().duration]);
        }""")
        self.assertEqual(rot, [["rotate(-90deg)", "rotate(-180deg)", 200]])

    def test_hover_split(self) -> None:
        """A szürke kiemelés csak a sor sávján jelenik meg, a merge gráfoszlopa mutatót kap; a sima
        commit gráfoszlopa nem reagál: nincs kiemelés, nincs nyíl, a kattintás nem nyit semmit."""
        bg = "el => getComputedStyle(el).backgroundColor"
        plain = self.row("README javítás")
        inner = plain.locator(".row-in")
        box = plain.bounding_box()
        self.assertEqual(plain.locator(".merge-hit").count(), 0)
        self.page.mouse.move(box["x"] + 6, box["y"] + box["height"] / 2)   # a gráfoszlop
        self.settle()
        self.assertEqual(inner.evaluate(bg), "rgba(0, 0, 0, 0)")
        self.assertEqual(plain.evaluate("el => getComputedStyle(el).cursor"), "default")
        self.page.mouse.click(box["x"] + 6, box["y"] + box["height"] / 2)
        self.settle()
        self.assertEqual(self.page.locator("#rows .details").count(), 0)
        inner.hover()
        self.settle()
        self.assertNotEqual(inner.evaluate(bg), "rgba(0, 0, 0, 0)")
        self.assertEqual(self.row(MERGE).locator(".merge-hit").evaluate("el => getComputedStyle(el).cursor"), "pointer")
        inner.click()
        self.settle()
        self.assertEqual(self.page.locator("#rows .details").count(), 1)

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


class StackedTest(MergeCase):
    HISTORY = {"stacked": True}

    def test_dependent_branch_joins_collapsed_stem(self) -> None:
        """Ha a ráépülő ág ki van bontva, a régebbi merge pedig össze van csukva, a ráépülő ág
        pontozott vége a régebbi merge pontozott szárába fut be: egy vonal megy tovább."""
        # Adott: a profil-ág (a login-ág csúcsára épül) kibontva, a login-merge összecsukva
        self.expand(STACKED)
        self.assertNotIn("Login űrlap", self.subjects())
        # Ha a gráf kirajzolódik
        paths = self.page.evaluate(PATHS)
        start = self.page.evaluate(ROW_MID, "Indulás")
        profile = self.page.evaluate(ROW_MID, "Profil oldal")
        dotted = [p["n"] for p in paths if p["dash"] == "2 2"]
        # Akkor egyetlen pontozott vonal ér le az Indulásig (a login-merge szára)
        self.assertEqual(sum(1 for n in dotted if abs(n[-1] - start) < 1), 1, dotted)
        # És a profil-ág pontozott vége a sora alatt egy sornyira, a szár sávjában véget ér
        join = [n for n in dotted if abs(n[1] - profile) < 1]
        self.assertEqual(len(join), 1, dotted)
        # És a szár még egyenes részén ér véget: a szár a cél előtt egy sornyival (34 px) fordul el
        self.assertLessEqual(join[0][-1], start - 34 + 0.5, join)


    def test_both_collapsed_join(self) -> None:
        """Ha mindkét merge össze van csukva, a profil-merge pontozott éle a saját sávjában a
        login-merge alá fut, és ott a login-merge szárába csatlakozik: látszik, hogy arra épül."""
        # Adott: mindkét merge összecsukva (alapállapot)
        paths = self.page.evaluate(PATHS)
        start = self.page.evaluate(ROW_MID, "Indulás")
        top, below = (self.page.evaluate(ROW_MID, s) for s in (STACKED, MERGE))
        dotted = [p["n"] for p in paths if p["dash"] == "2 2"]
        # Akkor egyetlen pontozott vonal ér le az Indulásig
        self.assertEqual(sum(1 for n in dotted if abs(n[-1] - start) < 1), 1, dotted)
        # És a profil-merge éle a login-merge alatt, a szár egyenes részén ér véget
        own = [n for n in dotted if abs(n[1] - top) < 1]
        self.assertEqual(len(own), 1, dotted)
        self.assertGreater(own[0][-1], below)
        self.assertLessEqual(own[0][-1], start - 34 + 0.5)

    def test_join_during_fold_animation(self) -> None:
        """Összecsukás és kibontás közben sincs egy pillanatra sem második pontozott vonal a célig."""
        # Adott: a profil-ág és a login-merge is kibontva
        self.expand(STACKED)
        self.expand(MERGE)
        for _ in range(2):              # összecsukás, majd kibontás
            # Ha a User a login-merge-re kattint, és az animáció félúton tart
            res = self.row(MERGE).locator(".merge-hit").evaluate("""async el => {
              el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
              const anims = document.getAnimations().filter(a => a.effect?.target?.classList?.contains('row'));
              anims.forEach(a => { a.pause(); a.currentTime = 100; });
              await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
              const row = [...document.querySelectorAll('#rows .row')]
                .find(r => r.querySelector('.subject').textContent === 'Indulás');
              const rb = row.getBoundingClientRect(), sb = document.querySelector('#lanes').getBoundingClientRect();
              const start = rb.top + rb.height / 2 - sb.top;
              const dotted = [...document.querySelectorAll('#lanes path')]
                .filter(p => p.getAttribute('stroke-dasharray') === '2 2' && p.getAttribute('opacity') !== '0')
                .map(p => p.getAttribute('d').match(/-?[\\d.]+/g).map(Number));
              anims.forEach(a => a.play());
              return { start, dotted, n: anims.length };
            }""")
            # Akkor legfeljebb egy pontozott vonal ér le az Indulásig
            self.assertGreater(res["n"], 0)
            reaching = [n for n in res["dotted"] if abs(n[-1] - res["start"]) < 1]
            self.assertLessEqual(len(reaching), 1, res)
            self.settle()


class RemoteRefTest(MergeCase):
    HISTORY = {"remote": True}

    def test_ref_visible_chain_hidden(self) -> None:
        """A megmaradt `origin/feat/login` commitja látszik, az alatta lévő beolvasztott lánc rejtett;
        a merge száma „+1”, a ref-es commitot szaggatott él köti az „Indulás”-hoz."""
        self.assertEqual(self.subjects(), [MERGE, "README javítás", "Login űrlap", "Indulás"])
        self.assertEqual(self.row(MERGE).locator(".merge-n").inner_text(), "+1")
        edges = self.page.evaluate(EDGES)
        a, b = (self.page.evaluate(ROW_MID, s) for s in ("Login űrlap", "Indulás"))
        self.assertEqual([e["dash"] for e in edges if abs(e["y1"] - a) < 1 and abs(e["y2"] - b) < 1], ["2 2"])


class FoldWidthTest(MergeCase):
    HISTORY = {"remote": True}

    def test_fold_width(self) -> None:
        """Az elrejtett commitot átugró szaggatott él olyan vastag, mint a fő vonal (2 px)."""
        widths = self.page.eval_on_selector_all("#lanes path.fold", "ps => ps.map(p => p.getAttribute('stroke-width'))")
        self.assertTrue(widths)
        self.assertEqual(set(widths), {"2"})


class RemoteSameDayTest(MergeCase):
    HISTORY = {"remote": True, "start_day": 1}

    def test_adjacent_edge_curves(self) -> None:
        """A közvetlenül alatta lévő sorba futó szaggatott él a cél fölött ívben fordul a cél sávjába:
        a forrás sávjában nem fut le a cél pöttyének magasságáig (nincs derékszögű sarok)."""
        a, b = (self.page.evaluate(ROW_MID, s) for s in ("Login űrlap", "Indulás"))
        paths = self.page.evaluate(PATHS)
        d = next(p["n"] for p in paths if abs(p["n"][1] - a) < 1 and abs(p["n"][-1] - b) < 1)
        x2 = d[-2]
        off_lane = [y for x, y in zip(d[::2], d[1::2]) if abs(x - x2) > 0.5]
        self.assertTrue(off_lane)
        self.assertLess(max(off_lane), b - 4)


class ForkTest(MergeCase):
    HISTORY = {"fork": True}

    def test_branch_off_merged(self) -> None:
        """A beolvasztott ágból leágazó branch commitja látszik, a leágazás alatti lánc a merge alatt
        rejtett; szaggatott él köti az első látható commithoz, kibontva folytonos."""
        self.assertEqual(self.subjects(), [MERGE, "README javítás", "Mellékág", "Indulás"])
        self.assertEqual(self.row(MERGE).locator(".merge-n").inner_text(), "+2")
        a, b = (self.page.evaluate(ROW_MID, s) for s in ("Mellékág", "Indulás"))
        dash = [e["dash"] for e in self.page.evaluate(EDGES) if abs(e["y1"] - a) < 1 and abs(e["y2"] - b) < 1]
        self.assertEqual(dash, ["2 2"])
        self.expand()
        self.assertIn("Login váz", self.subjects())
        a, b = (self.page.evaluate(ROW_MID, s) for s in ("Mellékág", "Login váz"))
        dash = [e["dash"] for e in self.page.evaluate(EDGES) if abs(e["y1"] - a) < 1 and abs(e["y2"] - b) < 1]
        self.assertEqual(dash, [None])


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
