# Egyoldalú fájl-diff csak egymás alatti nézetben

Új vagy egészében törölt fájl lenyitásakor a diff mostantól mindig az egymás
alatti nézetben jelenik meg, széles panelen is.

Ilyen fájlnál minden sor csak `+` vagy csak `−`, így a side-by-side nézet
egyik fele üresen maradt volna, a hasznos tartalom pedig a szélesség felére
szorult.

A `diffHtml` a hunkok sortípusaiból dönt: ha csak egyféle változás van, és
nincs változatlan sor, a side-by-side változatot el sem készíti.

- [`[8b5254bf]`](https://github.com/GaborTorma/git-graph/commit/8b5254bf985bd91e0b9b0610e13d9b72250dc98e) · fix(ui): show one-sided file diffs only in the unified view
