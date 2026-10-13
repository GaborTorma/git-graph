# Session-váltás: a lap fókusza nem késik 50 s-ot

Új sessionre váltva a lap most kb. 1 s alatt átáll az új session worktree-jére.
Eddig előfordult, hogy a régin maradt, és csak a long-poll határidejénél (50 s)
váltott.

Az ok egy versenyhelyzet az appban: a váltás sora előbb jelenik meg a
naplóban, mint az új session fájlja. A váltáskor kiadott fókusz így még a régi
volt, a következő `changes`-hívás pedig csak a repó állapotát figyelte, a
fókuszt nem.

A fókusz bekerült a `since` tokenbe, és a várakozó kör 2 s-onként a repó
állapotával együtt újraszámolja. A késés így legfeljebb a session-fájl
megjelenése + 2 s.

- [`[38eb8219]`](https://github.com/GaborTorma/git-graph/commit/38eb8219885ae5a0e03fbea15c97dc9730d4fb9f) · fix(watch): carry focus in the since token and recheck it while waiting
