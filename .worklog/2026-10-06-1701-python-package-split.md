# A Python-oldal modulokra bontva

A 2400 soros, egyetlen fájlos `bin/git-graph` helyett a kód a `git_graph/`
csomagban él, felelősségi körönként egy modulban (git-hívások, gráf, diff,
avatarok, lap, regiszter, az app session-fókusza, a `changes` long-poll,
publikálás, MCP szerver, telepítés, hook, parancssor). A `bin/git-graph`
vékony belépő maradt, így a `git-graph` parancs, a hook és a skillek változatlanok.
A tesztek modulonként külön fájlba kerültek, és 18-ról 59-re bővültek: a hook,
a publikálás, a regiszter, a diff és a telepítés is le van fedve.

Az egy fájl a launchd-s időkből maradt, amikor a scriptnek bárhol, egymagában
kellett futnia. Pluginként a lap fájljai már úgyis mellette utaznak, a fájl
viszont nehezen volt áttekinthető és modulonként tesztelhető.

A legkényesebb rész az app által futtatott stabil másolat volt. Ez továbbra is
egyetlen fájl: a telepítés a csomagból futtatható zipet épít (stdlib, `python3
<zip>`), és atomi cserével teszi a helyére, így egy épp induló szerver sosem lát
félig új csomagot. A manifest kerül ki utolsónak, mert a zip a verzióját abból
olvassa: fordított sorrendnél egy közben induló újraindulás a régi kódot az új
verziónak hitte volna. A 0.12.x szerver frissítéskor csak a `bin/git-graph`-ot
másolja át; ilyenkor a belépő a telepített plugin mappájából tölti be a
csomagot, és a következő session hookja teszi ki a zipet. Ezt élesben is
kipróbáltuk kamu HOME-mal (12/12 kérés megválaszolva a csere körül), és a
`graph_data` / `file_diff` kimenete 5 valódi repón bájtra egyezik a régiével.

Nyitva maradt: a 0.12.x átmeneti ág a belépőben törölhető, ha már sehol nem
fut 0.12.x. A közben észrevett fókusz-hiba (menet közben `EnterWorktree`-vel
worktree-be lépő session a fő checkoutot látja sajátnak) parkolva, külön ágon jön.

- [`[55c8d4ff]`](https://github.com/GaborTorma/git-graph/commit/55c8d4ff4acc42b746a72ec75448c1ae8c7e9198) · refactor: split bin/git-graph into the git_graph package with per-module tests
- [`[bea41370]`](https://github.com/GaborTorma/git-graph/commit/bea41370a01fe4e2137ee2d94bf31febed300453) · refactor(install): place the manifest last and share the registry and manifest readers
