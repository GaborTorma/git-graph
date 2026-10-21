---
name: focused-worktree-design
description: A „saját” worktree az előtérben lévő sessioné — a lap egy nyitott changes long-pollt tart, a szerver session-váltásra vagy állapotváltozásra válaszol; a fókuszt a 2 s-os kör is újraszámolja
metadata:
  type: project
---

A lap nem tudhatja, melyik sessionben látszik ([[artifact-single-frame]]), és erről eseményt sem
kap. Ezért:

- A szerver dönt: a repóban dolgozó, nem archivált sessionök közül a legutóbb fókuszált
  (`focused_worktree`, források: [[app-focus-sources]]). Kézzel nem választható.
- A lap mindig egy `changes`-hívást tart nyitva (`since` + `wait`, `wait_changes`). A szerver külön
  szálon válaszol, ha az app naplójában session-váltás jelenik meg (`log_advance`, ~50 ms), vagy a
  `repo_state` eltér a `since`-tól — git-műveletnél a `stat`-előszűrő (`stamp_paths`) miatt ~50 ms,
  fájlszerkesztésnél a 2 s-os teljes számításra —, legkésőbb 50 s után üresen
  ([[host-bridge-long-poll]]).
- A `since` (állapot-hash + naplókurzor + fókusz) miatt a két hívás között jött változás sem vész el.
- Gotcha: új sessionre váltáskor a napló sora előbb jön, mint a session-fájl, így a váltáskor kiadott
  fókusz még a régi. Ezért a 2 s-os kör is újraszámolja a fókuszt — enélkül 50 s-ig a régi maradt
  (mérve).
- A `send` zárolt, a fókusz-gyorstárak `FOCUS_LOCK` alatt; a `restart` előbb a várakozókat
  válaszoltatja (`WAKE`); `WAITERS_MAX` fölött nem várunk.
- Halványabb (`.foreign`), ami nem a sajáté: worktree-ből nézve, ami a HEAD-jéből nem érhető el; a fő
  checkoutból csak a worktree-k saját commitjai és WIP-je. A gazdátlan ágak a fő checkouté (a git nem
  jegyzi, hol jöttek létre).
- Elvetve (2026-10-04): a link `#horgony`-a (nem jut át) és a panelszélesség alapú tipp (rossz
  worktree-re is átváltott, mielőtt a session-fájl kijavította).

**Why:** repónként egy Artifact van, a worktree-k közösen látják (0.12 óta).

**How to apply:** fókusz-logika változásánál a `claude_app.py` és a `watch.py` együtt; a lapról ne
kérdezz sűrűn.
