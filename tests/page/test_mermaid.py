"""A markdown-diff Mermaid-blokkja diagramként: a változott régi változata piros, az új zöld
keretben, a változatlan keret nélkül; hibás diagramnál a kódnézet marad, a hibával."""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from harness import PageTestCase

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
OLD_BAD = f"{FENCE}mermaid\nflowchart LR\n  A --> B\n{FENCE}\n"
NEW_BAD = f"{FENCE}mermaid\nflowchart LR\n  A --> \n{FENCE}\n"

# A kirajzolt diagramok: [keret, szövegek] — a keret a diff színe (`add` / `del`), vagy üres.
FIGS = ("fs => fs.map(f => [f.className.replace('md-mmd-fig', '').trim(),"
        " [...f.querySelectorAll('svg .nodeLabel, svg text')].map(t => t.textContent.trim()).filter(Boolean)])")


class MermaidTest(PageTestCase):
    @classmethod
    def prepare(cls, repo: Path) -> None:
        def git(*args: str) -> None:
            subprocess.run(["git", "-c", "user.name=Teszt Elek", "-c", "user.email=teszt@x.hu",
                            "-C", str(repo), *args], check=True, capture_output=True)
        (repo / "abra.md").write_text(OLD, encoding="utf-8")
        (repo / "hibas.md").write_text(OLD_BAD, encoding="utf-8")
        (repo / "szoveg.md").write_text("Régi szöveg.\n", encoding="utf-8")
        git("add", ".")
        git("commit", "-qm", "ábra")
        (repo / "abra.md").write_text(NEW, encoding="utf-8")
        (repo / "hibas.md").write_text(NEW_BAD, encoding="utf-8")
        (repo / "szoveg.md").write_text("Új szöveg.\n", encoding="utf-8")
        git("commit", "-qam", "ábra: módosítva")

    def open_file(self, name: str) -> None:
        self.page.locator("#rows .row", has_text="ábra: módosítva").click()
        self.settle()
        self.page.locator("#rows .details .file", has_text=name).click()

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
        hidden = self.page.locator(".diff-uni .md-mmd .md-code").evaluate_all(
            "cs => cs.map(c => getComputedStyle(c).display)")
        self.assertEqual(hidden, ["none", "none"])

    def test_split(self) -> None:
        """Széles nézetben egymás mellett: balra a régi, jobbra az új változat."""
        self.resize(1400)
        self.open_file("abra.md")
        self.figs(".diff-split")
        rows = self.page.locator(".diff-split .md-row:has(.md-mmd)").evaluate_all(
            "rs => rs.map(r => [...r.children].map(c => [...c.querySelectorAll('.md-mmd-fig')]"
            ".map(f => f.className.replace('md-mmd-fig', '').trim() || '-')))")
        self.assertEqual(rows, [[["del"], ["add"]], [["-"], ["-"]]])

    def test_broken_keeps_code(self) -> None:
        """Ha a diagram hibás, a kódnézet látszik, alatta a Mermaid hibája."""
        self.open_file("hibas.md")
        err = self.page.wait_for_selector(".md-mmd-err")
        self.assertIn("A diagram nem rajzolható ki", err.text_content())
        self.assertIn("Parse error", err.text_content())
        shown = self.page.locator(".md-mmd .md-code").evaluate("c => getComputedStyle(c).display")
        self.assertEqual(shown, "block")

    def test_lazy_load_and_theme(self) -> None:
        """A Mermaid csak az első diagramnál töltődik be; témaváltáskor a diagram újrarajzolódik."""
        self.open_file("szoveg.md")
        self.page.wait_for_selector(".md-doc")
        self.settle()
        self.assertFalse(self.page.evaluate("'mermaid' in globalThis"))
        self.page.locator("#rows .details .file", has_text="abra.md").click()
        self.figs(".diff-uni")
        # a diagram stílusa a saját azonosítója nélkül (az minden rajzolásnál új)
        style = ("() => document.querySelector('.diff-uni .md-mmd-fig svg style').textContent"
                 ".replace(/#gg-mmd-\\d+/g, '')")
        light = self.page.evaluate(style)
        self.page.evaluate("document.documentElement.setAttribute('data-theme', 'dark')")
        self.page.wait_for_function(f"({style})() !== {light!r}")


if __name__ == "__main__":
    unittest.main()
