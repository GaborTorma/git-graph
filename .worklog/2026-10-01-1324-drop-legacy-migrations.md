# A régi átvezetések kivéve

Kikerült a scriptből minden kód, ami a plugin előtti állapotból vezetett át:
a régi `install.sh`-s telepítés takarítása (globális hook, `~/.claude/commands`
symlink, régi `~/.local/bin` linkek átirányítása, a `co.torma.gitgraph` agent),
a régi `gitgraph.*` és `artifactHead` kulcsok kezelése, és a repón belüli
`.git-graph/` kimenet törlése.

Ezek minden session elején lefutottak, de már semmit nem találtak: az eszköz
egyetlen gépen van, ott az első pluginos hook mindent átvezetett. Előtte az
utolsó maradványt (`MicrOasis2026`: régi kulcs és kimeneti mappa) még a régi
kóddal vittük át, és minden repót átnéztünk, hogy nincs több.

A `~/.local/bin` linkeknél a hook mostantól csak a hiányzót hozza létre; ami a
néven már ott van, ahhoz nem nyúl.

- [`[edb37fd3]`](https://github.com/GaborTorma/git-graph/commit/edb37fd359603b2805cc8ec14bdc3ac1417136c8) · refactor: drop migrations from the pre-plugin install and old output
