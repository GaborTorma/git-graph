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
    épülő `feat/profile` („Profil oldal”, „Profil 2–5”, az 1. napon; köztük a `main`-en „Közbülső”),
    külön merge-dzsel a login merge-e után (3. nap)."""
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
        # a main-en egy commit a profil-ág commitjai közé: a csukott ág legalja e sor alatt marad
        git("switch", "-q", "main", day=1)
        commit("Közbülső", 1)
        git("switch", "-q", "feat/profile", day=1)
        for k in range(2, 6):                       # hosszabb ág: a sorok mozgása látszik az animációban
            commit(f"Profil {k}", 1)
    git("switch", "-q", "main", day=2)
    commit("README javítás", 2)
    git("merge", "-q", "--no-ff", "-m", MERGE, "feat/login", day=2)
    git("branch", "-q", "-D", "feat/login", day=2)
    if stacked:
        git("merge", "-q", "--no-ff", "-m", STACKED, "feat/profile", day=3)
        git("branch", "-q", "-D", "feat/profile", day=3)


# A mérések segédei a lapon: egy sor közepe a gráf SVG-jében (null, ha nincs ilyen sor), és a gráf
# útjai (koordináták, szaggatás, erősség, pontozott-e, és ha ívvel végződik, az ív kezdetének Y-ja: `turn`).
LIB = """const mid = s => { const row = [...document.querySelectorAll('#rows .row')]
    .find(r => r.querySelector('.subject').textContent === s);
  if (!row) return null;
  const rb = row.getBoundingClientRect(), sb = document.querySelector('#lanes').getBoundingClientRect();
  return rb.top + rb.height / 2 - sb.top; };
const paths = () => [...document.querySelectorAll('#lanes path')].map(p => {
  const d = p.getAttribute('d'), n = d.match(/-?[\\d.]+/g).map(Number);
  return { n, dash: p.getAttribute('stroke-dasharray'), fold: p.matches('.fold'), op: Number(p.getAttribute('opacity') ?? 1),
           turn: d.lastIndexOf('C') > d.lastIndexOf('L') ? n.at(-7) : null }; });"""

# A gráf éleinek összes koordinátája (x, y párok sorban) és a szaggatás.
PATHS = f"""() => {{ {LIB} return paths(); }}"""

# A gráf élei: a kezdő- és végpont Y-ja (az SVG koordinátáiban) és a szaggatás.
EDGES = f"""() => {{ {LIB} return paths().map(p => ({{ y1: p.n[1], y2: p.n.at(-1), dash: p.dash }})); }}"""

# Egy sor közepének Y-ja a gráf SVG-jében.
ROW_MID = f"""s => {{ {LIB} return mid(s); }}"""

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

    def frames(self, subject: str, times: list[float], measure: str) -> list[dict]:
        """Kattintás a `subject` merge gráfoszlopára; a sorok animációja megállítva, és a `times`
        időpontjaiban (ms) képkockánként a `measure` (JS-függvény, a `LIB` segédeivel) eredménye
        (`v`), a sorok haladása (`progress`) és az animált sorok száma (`n`). Utána az animáció végig
        fut, és a lap megnyugszik."""
        hit = self.row(subject).locator(".merge-hit")
        hit.hover(position={"x": 4, "y": 4})
        res = hit.evaluate(f"""async (el, times) => {{ {LIB}
          const measure = {measure};
          el.dispatchEvent(new MouseEvent('click', {{ bubbles: true }}));
          const anims = document.getAnimations().filter(a => a.effect?.target?.classList?.contains('row'));
          anims.forEach(a => a.pause());
          const out = [];
          for (const t of times) {{
            anims.forEach(a => {{ a.currentTime = t; }});
            await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
            out.push({{ t, n: anims.length, progress: anims[0]?.effect.getComputedTiming().progress, v: measure() }});
          }}
          anims.forEach(a => a.play());
          return out;
        }}""", times)
        self.settle()
        return res


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

    def test_fold_fades(self) -> None:
        """Összecsukáskor a pontozott él a felcsukódás alatt beúszik, a felcsukódó ág élei, pöttyei és
        sorai kihalványulnak; kibontáskor fordítva. A végén nincs ugrás: halványított elem nem marad."""
        measure = """() => ({
          fold: paths().filter(p => p.fold).map(p => p.op),
          faded: [...document.querySelectorAll('#lanes [opacity]')].filter(e => !e.matches('.fold'))
            .map(e => Number(e.getAttribute('opacity'))),
          row: Number(getComputedStyle([...document.querySelectorAll('#rows .row')]
            .find(r => r.querySelector('.subject').textContent.startsWith('Login'))).opacity) })"""
        for opening in (True, False):
            # Ha a User kibontja (majd összecsukja) a merge-et, és az animáció félúton tart
            [f] = self.frames(MERGE, [100], measure)
            # Akkor a pontozott él még / már látszik, de nem teljes; az ág élei, pöttyei és sorai félig
            self.assertEqual(len(f["v"]["fold"]), 1, (opening, f))
            self.assertTrue(0 < f["v"]["fold"][0] < 1, (opening, f))
            self.assertTrue(f["v"]["faded"] and all(0 < o < 1 for o in f["v"]["faded"]), (opening, f))
            self.assertTrue(0 < f["v"]["row"] < 1, (opening, f))
            # És a végén nincs halványított elem; összecsukva a pontozott él teljes, kibontva nincs
            self.assertEqual(self.page.locator("#lanes [opacity]:not(circle)").count(), 0, opening)
            fold = self.page.locator("#lanes path.fold")
            if opening:
                self.assertEqual(fold.count(), 0)
            else:
                self.assertEqual(fold.get_attribute("opacity"), None)

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
        # És a profil-ág színét kapja, nem a login-ágét
        colors = self.page.evaluate("""y => ({
          join: [...document.querySelectorAll('#lanes path.fold')]
            .find(p => Math.abs(Number(p.getAttribute('d').match(/-?[\\d.]+/g)[1]) - y) < 1).getAttribute('stroke'),
          dot: [...document.querySelectorAll('#lanes circle')]
            .find(c => Math.abs(Number(c.getAttribute('cy')) - y) < 1).getAttribute('fill') })""", profile)
        self.assertEqual(colors["join"], colors["dot"])

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

    def test_join_under_expanded_merge(self) -> None:
        """Kibontott login-merge mellett is a login-merge alatt fut be a profil-merge pontozott éle
        a login-ág sávjába, nem alul, a login-ág csúcsánál."""
        # Adott: a login-merge kibontva, a profil-merge összecsukva
        self.expand(MERGE)
        # Ha a gráf kirajzolódik
        top, below, tip = (self.page.evaluate(ROW_MID, s) for s in (STACKED, MERGE, "Login űrlap"))
        fold = [p["n"] for p in self.page.evaluate(PATHS) if p["dash"] == "2 2" and abs(p["n"][1] - top) < 1]
        # Akkor a pontozott él a login-merge alatt, a csúcs előtt legalább egy sornyival ér véget
        self.assertEqual(len(fold), 1, fold)
        self.assertGreater(fold[0][-1], below)
        self.assertLessEqual(fold[0][-1], tip - 34 + 0.5, (fold, tip))

    def test_dotted_paths_continuous_and_smooth(self) -> None:
        """A pontozott él egyetlen folytonos útvonal (a szaggatás nem indul újra a fordulónál), és a
        ráépülő ág csatlakozó íve egyetlen sima S-ív."""
        # Adott: a profil-ág kibontva, a login-merge összecsukva
        self.expand(STACKED)
        profile = self.page.evaluate(ROW_MID, "Profil oldal")
        ds = self.page.evaluate("""() => [...document.querySelectorAll('#lanes path.fold')].map(p => p.getAttribute('d'))""")
        # Akkor minden pontozott él egy darab
        self.assertTrue(all(d.count("M") == 1 for d in ds), ds)
        # És a csatlakozó ív egyetlen görbe, egyenes szakasz nélkül
        join = next(d for d in ds if abs(float(d.split()[2]) - profile) < 1)
        self.assertEqual((join.count("C"), join.count("L")), (1, 0), join)

    # Egy képkocka a mátrixhoz: a sorok közepe és a látható (nem kihalványult) utak.
    SCENE = """() => ({ start: mid('Indulás'), below: mid("Merge branch 'feat/login'"),
      top: mid("Merge branch 'feat/profile'"), profile: mid('Profil oldal'),
      paths: paths().filter(p => p.op > 0.05) })"""

    def test_toggle_matrix(self) -> None:
        """Bármelyik merge kapcsolásakor, a másik kibontott és összecsukott állapotában, kibontáskor és
        összecsukáskor is, az animáció minden képkockáján:
        - legfeljebb egy pontozott vonal ér le a login-ág aljáig (a szár);
        - a profil-merge és a profil-ág legalsó commitja felől a login-ág sávjába egy-egy vonal fut
          (a folytonos és a pontozott rétege egy helyen végződik), és az íve nem lapul el, nem fordul
          vissza;
        - a profil-merge pontozott éle a login-merge alatt, a szár egyenes részén csatlakozik (a
          login-merge kapcsolásakor a helyén marad);
        - az utolsó képkocka a statikus rajz (az animáció után nincs ugrás)."""
        self.expand(MERGE)
        login = self.page.evaluate("""y => Number([...document.querySelectorAll('#lanes circle')]
          .find(c => Math.abs(Number(c.getAttribute('cy')) - y) < 1).getAttribute('cx'))""",
                                   self.page.evaluate(ROW_MID, "Login űrlap"))
        for toggle, other in ((MERGE, STACKED), (STACKED, MERGE)):
            for other_open in (False, True):
                # Adott: a kapcsolt merge összecsukva, a másik kibontva vagy összecsukva
                self.page.reload()
                self.page.wait_for_selector("#rows .row")
                self.settle()
                if other_open:
                    self.expand(other)
                for opening in (True, False):
                    case = (toggle, other_open, opening)
                    # Ha a User a merge-re kattint
                    frames = [f["v"] for f in self.frames(toggle, [5, 20, 60, 100, 140, 170, 199.9], self.SCENE)]
                    final = self.page.evaluate(f"() => {{ {LIB} return ({self.SCENE})(); }}")
                    for f in frames:
                        dotted = [p for p in f["paths"] if p["dash"] == "2 2"]
                        # Akkor legfeljebb egy pontozott vonal ér le az Indulásig
                        self.assertLessEqual(sum(1 for p in dotted if abs(p["n"][-1] - f["start"]) < 1), 1, (case, f))
                        for y in (f["top"], f["profile"]):
                            joins = self._joins(f, y, login)
                            # És a sor felől a login-ág sávjába futó vonalak egy helyen végződnek
                            self.assertLessEqual(len({round(p["n"][-1]) for p in joins}), 1, (case, y, f))
                            # És az ív vége nincs a fordulója fölött (nem fordul vissza)
                            for p in joins:
                                if p["turn"] is not None:
                                    self.assertGreaterEqual(p["n"][-1], p["turn"], (case, p))
                        # És a profil-merge pontozott éle a login-merge alatt, a szár egyenes részén ér véget
                        for p in dotted:
                            if abs(p["n"][1] - f["top"]) < 1 and p["n"][-2] == login:
                                self.assertGreater(p["n"][-1], f["below"], (case, f))
                                self.assertLessEqual(p["n"][-1], f["start"] - 34 + 0.5, (case, f))
                                # a login-merge kapcsolásakor a helyén marad: a login-merge mellett
                                if toggle == MERGE:
                                    self.assertLessEqual(p["n"][-1], max(f["below"] + 34, f["top"] + 2 * 34) + 0.5, (case, f))
                    # És az utolsó képkocka csatlakozásai ott végződnek, ahol a statikus rajzéi (a mozgó
                    # vonal a merge felől indul, a statikus a legalsó commit alól is)
                    want = {round(p["n"][-1]) for key in ("top", "profile")
                            for p in self._joins(final, final[key], login) if p["op"] == 1}
                    got = [p["n"][-1] for key in ("top", "profile") for p in self._joins(frames[-1], frames[-1][key], login)]
                    for y in want:
                        self.assertTrue(any(abs(y - g) < 3 for g in got), (case, want, got))

    @staticmethod
    def _joins(frame: dict, y: float | None, lane: float) -> list[dict]:
        """A `y` magasságú sorból induló, a login-ág sávjában (`lane`), de nem az Indulásnál végződő utak."""
        if y is None:
            return []
        return [p for p in frame["paths"] if abs(p["n"][1] - y) < 1 and p["n"][-2] == lane and p["n"][0] != lane
                and abs(p["n"][-1] - frame["start"]) >= 1]

    def test_expand_fades_in_dependent_join(self) -> None:
        """A ráépülő ág lenyílásakor a legalsó commitjának nincs külön csatlakozó íve: a csatlakozást
        a merge-ből induló, a helyére csúszó egyetlen vonal rajzolja."""
        # Adott: mindkét merge összecsukva
        # Ha a User kibontja a profil-merge-et, és az animáció félúton tart
        [f] = self.frames(STACKED, [100], """() => {
          const y = mid('Profil oldal');
          return paths().filter(p => p.fold && Math.abs(p.n[1] - y) < 1); }""")
        # Akkor a Profil oldal alól nem indul külön csatlakozó ív
        self.assertEqual(f["v"], [])

    def test_join_follows_rows(self) -> None:
        """A helyére csúszó csatlakozás a ráépülő ág legalsó commitjával együtt mozog: az összecsukás
        elején nem fut előre (a legalsó commit fölé), a végén pedig befut a végső helyére — akkor is,
        ha a ráépülő ág commitjai között látható sor van (ott a csukott ág legalja is alatta marad)."""
        measure = """() => { const top = mid("Merge branch 'feat/profile'");
          return { ends: paths().filter(p => p.fold && Math.abs(p.n[1] - top) < 1).map(p => p.n.at(-1)),
                   profile: mid('Profil oldal') }; }"""
        for expanded_login in (True, False):
            if expanded_login:
                self.expand(MERGE)
            self.expand(STACKED)
            # Ha a User összecsukja a profil-merge-et: az animáció több pontján és a legvégén nézzük
            res = [f["v"] for f in self.frames(STACKED, [60, 100, 140, 170, 199.9], measure)]
            top = self.page.evaluate(ROW_MID, STACKED)
            final = next(p["n"][-1] for p in self.page.evaluate(PATHS) if p["dash"] == "2 2" and abs(p["n"][1] - top) < 1)
            for r in res:
                self.assertEqual(len(r["ends"]), 1, r)
            # Akkor közben a csatlakozás a legalsó committal együtt jár (legfeljebb 15 px-szel előtte)
            for r in res[:-1]:
                self.assertGreaterEqual(r["ends"][0], r["profile"] - 15, (expanded_login, r))
            # És a végén már a végső helyén (nem ugrik az animáció után)
            self.assertAlmostEqual(res[-1]["ends"][0], final, delta=3, msg=(expanded_login, res[-1], final))
            self.page.reload()
            self.page.wait_for_selector("#rows .row")
            self.settle()

    def test_expand_turns_solid_during_animation(self) -> None:
        """Összecsukott login-merge mellett a profil-merge kibontásakor a merge-ből induló szakasz a
        lenyílással együtt vált pontozottból folytonossá, nem csak utána."""
        # Adott: mindkét merge összecsukva
        # Ha a User kibontja a profil-merge-et, és az animáció félúton tart
        [f] = self.frames(STACKED, [100], """() => {
          const top = mid("Merge branch 'feat/profile'");
          return paths().filter(p => Math.abs(p.n[1] - top) < 1); }""")
        # Akkor a merge-ből induló szakaszon a folytonos réteg már részben látszik (sem nem hiányzik,
        # sem nem teljes): a pontozottból folytonosba váltás a lenyílással együtt halad
        solid = [p["op"] for p in f["v"] if p["dash"] is None and p["op"] < 1]
        self.assertTrue(solid and 0 < min(solid) < 1, f)

    def test_dependent_bottom_moves_with_progress(self) -> None:
        """Kibontott profil-ág mellett a login-merge kibontásakor a profil-ág alja és a login-ág közti
        ív vége a login-sorok nyílásával együtt halad a csukott helyéről a kibontottra (ugyanannyira,
        amennyire a sorok kinyíltak), nem ugrik az elején a végére."""
        self.expand(STACKED)

        def end() -> float:
            y = self.page.evaluate(ROW_MID, "Profil oldal")
            return next(p["n"][-1] for p in self.page.evaluate(PATHS) if abs(p["n"][1] - y) < 1 and p["n"][-2] != p["n"][0])
        # Adott: a csukott és a kibontott állapot íve (statikusan)
        closed = end()
        self.expand(MERGE)
        opened = end()
        self.expand(MERGE)
        # Ha a User kibontja a login-merge-et, és az animáció az elején tart
        [f] = self.frames(MERGE, [25], """() => { const y = mid('Profil oldal');
          return paths().filter(p => Math.abs(p.n[1] - y) < 1 && p.n.at(-2) !== p.n[0]).map(p => p.n.at(-1)); }""")
        # Akkor az ív vége a csukott és a kibontott hely között ott van, ahol a sorok haladása tart
        t = f["progress"]
        self.assertTrue(f["v"] and 0.05 < t < 0.95, f)
        want = closed + (opened - closed) * t
        self.assertTrue(all(abs(y - want) < 1.5 for y in f["v"]), (closed, opened, f, want))


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
