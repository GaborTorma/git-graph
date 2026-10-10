# Külön parancs a publikálásra, a megnyitásra és a felejtésre

A `/git-graph:artifact` helyett négy parancs van. Az `artifact-publish` feltölti
a repó Artifactját, ha még nincs vagy elavult, és megnyitja. Az `artifact-open`
csak megnyitja: elavult vagy hiányzó lapnál nem publikál, hanem az
`artifact-publish`-ra küld. Az `artifact-forget` az aktuális repó Artifactját
törli megerősítés után, és lefuttatja a `git-graph --forget`-et. A korábbi
`/git-graph:remove` (az összes repó Artifactja, eltávolítás előtt) neve
`forget-all-artifacts` lett.

Az egy parancs két dolgot csinált, és egyetlen repó Artifactját nem lehetett
eltakarítani, csak az összeset.

A `--forget` eddig a `~/.git-graph/no-auto-publish` fájllal az egész gépen
kikapcsolta az automatikus publikálást — egy repó elfelejtése így mindegyikét
leállította volna. Most a repó `.git/config`-jában a `git-graph.autoPublish=false`
jelzi, a többi `git-graph.*` kulcs mellett; a hook csak ott hallgat, és a kézi
publikálás (`--published`) visszakapcsolja. A régi globális fájlt a kód már nem
nézi.

Nyitva maradt: az új parancsok élő sessionbeli kipróbálása (`claude --plugin-dir .`).

- [`[182654cc]`](https://github.com/GaborTorma/git-graph/commit/182654cc8aa1dcd7fd64bb8dd40be2cb39c5462a) · feat(skills): split artifact commands into publish, open, forget and forget-all
