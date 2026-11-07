# Funkcióoldalak

A git-graph funkciói, funkciónként egy oldal: mit tud most, és hogyan működik.

| Oldal | Mire való |
| --- | --- |
| [Fejléc](header.md) | az ágválasztó (a kijelölés a gombon, remote-onkénti kapcsolók), a lenyíló keresés a ref-szűrővel, ghost gombok |
| [Fájl-diff](file-diff.md) | a commit fájljainak diffje: szöveg, renderelt markdown, képek |
| [Kóddiff és szerkesztés](code-diff.md) | a CodeMirror-kóddiff, a szerkesztés és mentés, a HEAD-commit WIP-rétege |
| [Fájlfa és teljes nézet](full-view.md) | a fájlfa sidebarban és teljes képernyőn, diff-szűrő, kereső, commitlista |
| [Merge-ek összecsukása](merge-collapse.md) | gyűrűs merge-pont, a beolvasztott commitok a merge alatt, kibontás a gráfoszlopra kattintva, animálva; repónkénti kapcsoló |
| [Subtree-remote](subtree-remote.md) | a `git subtree split` / `push` remote-ja: független történet a chipen, tükör-commitok, remote szerinti szűrő |

Fejlesztői háttér (a szabályok indoklása, mérések, döntések): a memória,
[`.claude/memory/`](../.claude/memory/MEMORY.md).
