# Nem stage-elt átnevezés egy fájlként

A WIP-sorban a még nem stage-elt átnevezés most egyetlen átnevezett fájlként
jelenik meg (`régi => új`), a két tartalom különbségével, és a diffje is a két
változatot veti össze.

Eddig törölt és új fájlként látszott: az új fájl követetlen, ezért a git
átnevezés-felismerése nem látja.

A párosítás a törölt és a követetlen szöveges fájlokat hasonlóság szerint veti
össze (legalább 50% közös sor, mint a git `-M` alapküszöbe). Az index
érintetlen marad, `git add -N` nincs, összhangban azzal, hogy minden git-hívás
csak olvas.

- [`[97acd16a]`](https://github.com/GaborTorma/git-graph/commit/97acd16ad0e2e75cffaef8d02e1b37bbe634b487) · fix(wip): show an unstaged rename as one renamed file
- [`[ebe6e680]`](https://github.com/GaborTorma/git-graph/commit/ebe6e680e7a0dbebcb3d585e2b5414731dabb0ee) · simplify(wip): keep the line counts of a paired rename
- [`[5c8ebd2d]`](https://github.com/GaborTorma/git-graph/commit/5c8ebd2d33f3ed199b03dc0f795070dd7cc4d5f5) · simplify(wip): reuse the rename candidate's matcher for the line counts
