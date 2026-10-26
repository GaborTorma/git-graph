"""A markdown-diff Mermaid-blokkja diagramként: a változott régi változata piros, az új zöld
keretben, a változatlan keret nélkül; hibás diagramnál a kódnézet marad, a hibával."""
from __future__ import annotations

import unittest
from pathlib import Path

from harness import PageTestCase, commit_versions

FENCE = "```"
OLD = f"""# Ábra

{FENCE}mermaid
flowchart LR
  A[Régi] --> B[Vég]
{FENCE}

Bekezdés marad.

{FENCE}mermaid
sequenceDiagram
  Lap->>Szerver: kérés
{FENCE}

Ez a sor változik.
"""
NEW = (OLD.replace("A[Régi] --> B[Vég]", "A[Új] --> B[Vég] --> C[Plusz]")
       .replace("Ez a sor változik.", "Ez a sor megváltozott."))
OLD_ONLY = (f'{FENCE}mermaid\nflowchart TD\n  A["merge-pr"] --> P{{"tiszta munkakönyvtár,<br/>nyitott PR, zöld CI?"}}\n'
            f'  P -->|nem| X["megáll"]\n{FENCE}\n')
NEW_ONLY = OLD_ONLY.replace(", zöld CI?", "?")
OLD_LINES = f"{FENCE}mermaid\nflowchart LR\n  A[Marad] --> B[Is]\n  B --> T[Törölt]\n{FENCE}\n\nRégi mondat.\n"
NEW_LINES = OLD_LINES.replace("  B --> T[Törölt]\n", "").replace("Régi mondat.", "Új mondat.")
OLD_BAD = f"{FENCE}mermaid\nflowchart LR\n  A --> B\n{FENCE}\n"
NEW_BAD = f"{FENCE}mermaid\nflowchart LR\n  A --> \n{FENCE}\n"
# csak egy él célpontja változik (`D` → `T`): az azonosító betűje egyik feliratban sem jelölt
OLD_TARGET = (f'{FENCE}mermaid\nflowchart LR\n  H{{"HEAD egy commit?"}}\n  D["deploy"]\n  T["STOP"]\n'
              f'  H -->|igen| D\n  D --> T\n{FENCE}\n')
NEW_TARGET = OLD_TARGET.replace("H -->|igen| D", "H -->|igen| T")
# egy csomópont felirata változik, a kiemelt vessző egy korábbi csomópontban is előfordul
OLD_COMMA = (f'{FENCE}mermaid\nflowchart TD\n  S["merge-dev"] --> P{{"dev branch,<br/>tiszta munkakönyvtár?"}}\n'
             f'  P -->|igen| F{{"a main a dev őse?"}}\n'
             f'  F -->|igen| B["merge-body --commits main..dev<br/>tárgysor a commitokból"]\n{FENCE}\n')
NEW_COMMA = OLD_COMMA.replace('B["merge-body --commits main..dev<br/>tárgysor a commitokból"]',
                              'B["üzenet: tárgysor a commitokból,<br/>## Deploy, ha kell"]')
# hosszú, fentről lefelé írt lánc: széles helyen vízszintesen fér el jobban
CHAIN = f"{FENCE}mermaid\nflowchart TD\n  A[Első] --> B[Második] --> C[Harmadik] --> D[Negyedik] --> E[Ötödik]\n{FENCE}\n"
# ER-diagram elágazással (a vonalak fordulnak), feliratos és üres kapcsolatokkal
ER = (f'{FENCE}mermaid\nerDiagram\n  Szerzo ||--o{{ Konyv : iras\n  Szerzo ||--o{{ Cikk : ""\n'
      f'  Konyv ||--o{{ Fejezet : ""\n  Cikk |o..o{{ Fejezet : hivatkozas\n{FENCE}\n')

# A kirajzolt diagramok: [keret, szövegek] — a keret a diff színe (`add` / `del`), vagy üres.
FIGS = ("fs => fs.map(f => [f.className.replace(/md-mmd-(fig|)/g, '').trim(),"
        " [...f.querySelectorAll('svg .nodeLabel, svg text')].map(t => t.textContent.trim()).filter(Boolean)])")


class MermaidTest(PageTestCase):
    SUBJECT = "ábra"

    @classmethod
    def prepare(cls, repo: Path) -> None:
        commit_versions(repo, {
            "abra.md": (OLD, NEW), "hibas.md": (OLD_BAD, NEW_BAD), "szoveg.md": ("Régi szöveg.\n", "Új szöveg.\n"),
            "torles.md": (OLD_ONLY, NEW_ONLY), "sorok.md": (OLD_LINES, NEW_LINES), "lanc.md": (None, CHAIN), "er.md": (None, ER),
            "cel.md": (OLD_TARGET, NEW_TARGET), "vesszo.md": (OLD_COMMA, NEW_COMMA),
        }, cls.SUBJECT)

    def figs(self, scope: str) -> list:
        self.page.wait_for_selector(f"{scope} .md-mmd-on")
        return self.page.locator(f"{scope} .md-mmd-fig").evaluate_all(FIGS)

    def test_changed_and_unchanged(self) -> None:
        """Keskenyen egymás alatt: a változott diagram régi (piros) és új (zöld) változata, a változatlan
        keret nélkül; a kódnézet rejtve."""
        self.open_file("abra.md")
        figs = self.figs(".diff-uni")
        self.assertEqual([f[0] for f in figs], ["del", "add", ""])
        self.assertEqual(figs[0][1], ["Régi", "Vég"])
        self.assertEqual(figs[1][1], ["Új", "Vég", "Plusz"])
        self.assertIn("kérés", figs[2][1])
        # csak a változott elem színes: a régiben az átírt csomópont, az újban az is, az új
        # csomópont és az új él (felirat nélkül); a változatlan „Vég” egyikben sem
        marked = self.page.locator(".diff-uni .md-mmd-fig").evaluate_all(
            "fs => fs.map(f => [...f.querySelectorAll('.md-mmd-ch')].map(e => e.tagName + ':' + e.textContent.trim()))")
        self.assertEqual(marked[0], ["g:Régi"])
        self.assertEqual(sorted(marked[1]), ["g:Plusz", "g:Új", "path:"])
        self.assertEqual(marked[2], [])
        # a két kis diagram elfér egymás mellett: egy sorban
        tops = self.page.locator(".diff-uni .md-mmd-fig").evaluate_all("fs => fs.map(f => f.offsetTop)")
        self.assertEqual(tops[0], tops[1])
        hidden = self.page.locator(".diff-uni .md-mmd .md-code").evaluate_all(
            "cs => cs.map(c => getComputedStyle(c).display)")
        self.assertEqual(hidden, ["none", "none"])

    def test_split(self) -> None:
        """Széles nézetben egymás mellett: balra a régi, jobbra az új változat."""
        self.resize(1400)
        self.open_file("abra.md")
        figs = self.figs(".diff-split")
        self.assertEqual([f[0] for f in figs], ["del", "add", ""])   # a változatlan is egyszer
        # a diagram előtti változatlan címsor is egyszer, a teljes szélességen
        self.assertEqual(self.page.locator(".diff-split .md-mmd-row .md-h").all_text_contents(), ["Ábra"])
        self.assertEqual(self.page.locator(".diff-split .md-row .md-h").count(), 0)
        # a teljes szélességen: a régi jobbra, az új balra igazítva, a középvonalon találkoznak
        edges = self.page.locator(".diff-split .md-mmd-view").first.evaluate(
            "v => { const r = v.getBoundingClientRect(), [a, b] = [...v.querySelectorAll('.md-mmd-fig')]"
            ".map(f => f.getBoundingClientRect()); return [r.left + r.width / 2 - a.right, b.left - (r.left + r.width / 2)]; }")
        self.assertTrue(all(0 <= e <= 4 for e in edges), edges)
        # csík csak az egészében új / törölt diagramon
        borders = self.page.locator(".diff-split .md-mmd-fig").evaluate_all(
            "fs => fs.map(f => getComputedStyle(f).borderLeftWidth)")
        self.assertEqual(borders, ["1px", "1px", "1px"])

    def test_only_deleted_text(self) -> None:
        """Ha a diagramból csak szöveg tűnt el, egy diagram elég: a régi, benne a változott csomópont
        színes, a törölt szöveg kiemelve."""
        self.open_file("torles.md")
        figs = self.figs(".md-doc")
        self.assertEqual([f[0] for f in figs], ["del"])
        marked = self.page.locator(".md-mmd-fig").evaluate(
            "f => [[...f.querySelectorAll('.md-mmd-hl')].map(e => e.textContent),"
            " [...f.querySelectorAll('.md-mmd-ch')].map(e => e.textContent.trim())]")
        self.assertEqual(marked, [[", zöld CI"], ["tiszta munkakönyvtár,nyitott PR, zöld CI?"]])
        # egy változat: balra igazítva
        gap = self.page.locator(".md-mmd-view").first.evaluate(
            "v => v.querySelector('.md-mmd-fig').getBoundingClientRect().left - v.getBoundingClientRect().left")
        self.assertEqual(gap, 0)

    def test_only_deleted_lines_split(self) -> None:
        """Side-by-side-ban is egy diagram, ha csak törlés van (egész sorok is), a teljes szélességen."""
        self.resize(1400)
        self.open_file("sorok.md")
        figs = self.figs(".diff-split")
        self.assertEqual([f[0] for f in figs], ["del"])
        self.assertEqual(self.page.locator(".diff-split .md-mmd-row .md-mmd").count(), 1)
        self.assertEqual(self.page.locator(".diff-split .md-row .md-mmd").count(), 0)
        marked = self.page.locator(".diff-split .md-mmd-fig").evaluate(
            "f => [...f.querySelectorAll('.md-mmd-ch')].map(e => e.tagName + ':' + e.textContent.trim())")
        self.assertEqual(sorted(marked), ["g:Törölt", "path:"])

    def test_broken_keeps_code(self) -> None:
        """Ha a diagram hibás, a kódnézet látszik, alatta a Mermaid hibája."""
        self.open_file("hibas.md")
        err = self.page.wait_for_selector(".md-mmd-err")
        self.assertIn("A diagram nem rajzolható ki", err.text_content())
        self.assertIn("Parse error", err.text_content())
        shown = self.page.locator(".md-mmd .md-code").evaluate("c => getComputedStyle(c).display")
        self.assertEqual(shown, "block")

    def test_new_edge_target(self) -> None:
        """Ha csak egy él célpontja változik, az él színes, de a csomópontok nem: az azonosító
        (`D`, `T`) betűje nem emelődik ki a `HEAD` / `STOP` feliratban."""
        self.open_file("cel.md")
        self.figs(".diff-uni")
        marked = self.page.locator(".diff-uni .md-mmd-fig").evaluate_all(
            "fs => fs.map(f => [[...f.querySelectorAll('.md-mmd-hl')].length,"
            " [...f.querySelectorAll('.md-mmd-ch')].map(e => e.tagName).sort()])")
        self.assertEqual([m[0] for m in marked], [0, 0])
        self.assertTrue(all(m[1] and set(m[1]) <= {"path"} for m in marked), marked)

    def test_mark_in_its_own_node(self) -> None:
        """A kiemelt szöveg a saját csomópontjában: az új felirat vesszője nem színezi a korábbi
        „dev branch,” csomópontot."""
        self.open_file("vesszo.md")
        self.figs(".diff-uni")
        marked = self.page.locator(".diff-uni .md-mmd-fig").evaluate_all(
            "fs => fs.map(f => [...f.querySelectorAll('g.node.md-mmd-ch')].map(e => e.textContent.trim()))")
        self.assertTrue(all(not any("dev branch" in t for t in m) for m in marked), marked)
        self.assertTrue(any(any("üzenet" in t for t in m) for m in marked), marked)

    def test_direction_fits_the_room(self) -> None:
        """A flowchart iránya a helyhez igazodik: széles nézetben a fentről lefelé írt lánc
        vízszintes, keskenyre váltva — újrarajzolás nélkül — visszafordul függőlegesre."""
        aspect = "f => { const s = f.querySelector('svg').viewBox.baseVal; return s.width / s.height; }"
        self.resize(1400)
        self.open_file("lanc.md")
        fig = self.page.locator(".md-mmd-on .md-mmd-fig:visible")
        fig.wait_for()
        self.assertGreater(fig.evaluate(aspect), 1)
        self.resize(700)
        self.assertLess(fig.evaluate(aspect), 1)

    def test_er_marker_before_bend(self) -> None:
        """Az ER-diagram vonala az entitás mellett egyenesen fut, és csak a jelölő (kör, villa)
        után fordul: a jelölő nem a fordulón ül."""
        self.open_file("er.md")
        self.page.wait_for_selector(".md-doc .md-mmd-on")
        # a vonal két végén az egyenes szakasz hossza (a rajz egységeiben)
        stubs = self.page.locator(".md-mmd-fig svg").first.evaluate("""svg => {
          const straight = (p, from, dir) => {
            const L = p.getTotalLength(), a = p.getPointAtLength(from);
            let k = 0;
            while (k < 100 && Math.abs(p.getPointAtLength(Math.min(L, Math.max(0, from + dir * (k + 1)))).x - a.x) < 0.5) k++;
            return k;
          };
          return [...svg.querySelectorAll('path[marker-start], path[marker-end]')]
            .flatMap(p => [straight(p, 0, 1), straight(p, p.getTotalLength(), -1)]);
        }""")
        self.assertEqual(len(stubs), 8)
        self.assertTrue(all(s >= 40 for s in stubs), stubs)   # a Mermaid ELK-ja magától 16-ot hagy

    def test_lazy_load_and_theme(self) -> None:
        """A Mermaid csak az első diagramnál töltődik be; témaváltáskor a diagram újrarajzolódik."""
        self.open_file("szoveg.md")
        self.page.wait_for_selector(".md-doc")
        self.settle()
        self.assertFalse(self.page.evaluate("'mermaid' in globalThis"))
        self.page.locator("#rows .details .file", has_text="abra.md").click()
        self.figs(".diff-uni")
        # a rajz `neo` stílusú, a lap palettáján (`base` téma)
        self.assertIn("neo", self.page.evaluate("document.querySelector('.diff-uni .md-mmd-fig svg').outerHTML"))
        # a diagram stílusa a saját azonosítója nélkül (az minden rajzolásnál új)
        style = ("() => document.querySelector('.diff-uni .md-mmd-fig svg style').textContent"
                 ".replace(/#gg-mmd-\\d+/g, '')")
        light = self.page.evaluate(style)
        self.page.evaluate("document.documentElement.setAttribute('data-theme', 'dark')")
        self.page.wait_for_function(f"({style})() !== {light!r}")


if __name__ == "__main__":
    unittest.main()
