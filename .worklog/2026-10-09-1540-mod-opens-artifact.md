# A lapot a plugin modja nyitja meg

A repó Git Graph lapját a session indulásakor már nem a modell nyitja meg, hanem
a plugin saját modja (`hooks/register.ts`): a `git-graph --open-url` megmondja,
kell-e (naprakész a lap, és a sessionben még nem volt nyitva), és ha igen, a mod
maga hívja az Artifact `open`-t. A modell így nem kap „nyisd meg” utasítást. A
worktree-váltás hookja kikerült: a repónak egy közös lapja van, a session elején
megnyílik.

A kiinduló kérdés az volt, hogy a lap átköltözhet-e egy mod-panelbe Artifact
nélkül. Nem: a mod-panel saját elemfából rajzol, HTML-t és scriptet nem futtat,
a lapot újra kellene írni. A modell Artifact-hívása viszont kiváltható.

Mérve: modból az `open` és a `read` auto módban megerősítés nélkül átmegy, a
`publish` nem (az osztályozó szerint nincs mögötte kérés) — ezért a publikálás a
session dolga marad, a hook továbbra is kéri. A mod a `classic.*` hook-eseményeket
nem kapja meg, ezért a döntés a Pythonban van, nem a hook szövegének elkapásában.
Friss sessionben a mod `open`-je kinyitja a panelt; egy már megnyitott lapot sem
a mod, sem a modell nem nyit ki újra.

Közben a `CLAUDE.md` a `.claude/` mappába került, hogy a `--strict` validálás
átmenjen (a `dev`-en ugyanez a mozgatás már megtörtént).

Nyitva maradt: ahol nem fut mod (régi kliens), a lap magától nem nyílik meg. A
`0.13.0` verzió a `dev` mergeletlen munkáján is szerepel.

- [`[3d4b3585]`](https://github.com/GaborTorma/git-graph/commit/3d4b3585f62328ec5aeaf9b0ea1dbc4522e1df2e) · feat(plugin): open the artifact from a plugin mod instead of the model
