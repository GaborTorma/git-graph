# A parkoló lista ignorálva

A `.parked.md` (a `/park` lokális teendőlistája) bekerült a `.gitignore`-ba,
hogy ne jelenjen meg követetlen fájlként, és véletlenül se commitolódjon.

A tétel a worktree-ben jött létre: a worktree-izolált session nem írhat a fő
checkoutba, így a parkoló sem mehetett oda — ezt a tanulságot a
`claude-settings` inboxa rögzíti.

- [`[38ed479c]`](https://github.com/GaborTorma/git-graph/commit/38ed479caa84cfd67fab387bb88f68f5d86faa7d) · chore: ignore the parked list
