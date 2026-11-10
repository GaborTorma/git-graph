---
name: artifact-contract
description: A lapok runtime-contractja rögzített (PUBLISH_CONTRACT, 0.2.96), minden repóban ugyanaz; újabbra csak egyeztetés után
metadata:
  type: project
---

A runtime-contract a lapon futó `window.claude` API verziója (capability-k, hívásalakok,
hibakódok). Az Artifact az első publikáláskor rögzül egy verzióhoz; a publish `contract`
paramétere emeli (`"latest"` vagy pontos szám), nélküle a régi marad. 2026-11-10-én a git-graph
lapja 0.2.66-on, a Lesowné 0.2.74-en futott, a legújabb 0.2.96 volt.

Döntés (a Fejlesztőé, 2026-11-10): minden lap a `publish.PUBLISH_CONTRACT`-tal publikálódik,
rögzítve, mindenhol ugyanazzal. A contract része a lap hashének (`page_digest`, `git-graph.artifactHash`),
így váltáskor minden repó következő sessionje újrapublikálja a lapját. A 0.2.96 a git-graph
lapján mérve működik (betöltés, `file_tree`), 2026-11-10.

**Why:** egyforma, ismert API minden lapon; a frissítés ne magától, ne lapról lapra történjen.

**How to apply:** ha az `Artifact` publish eredménye újabb contractot jelez („newest …”), szólj a
Fejlesztőnek; csak az ő jóváhagyása után emeld a `PUBLISH_CONTRACT`-ot (előtte nézd át az új
verzió típusait: az artifact-capabilities skill `<verzió>/*.d.ts`), és futtasd a lap tesztjeit.
