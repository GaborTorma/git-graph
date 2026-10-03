# Merge-fájlok és fejlesztői telepítés

A merge commitok fájllistája üres volt; most az első szülőhöz képest látszik,
amit a merge a fő ágra hozott (fájllista, diff).

A `--dev-install` a working treet az appban futó git-graph helyére teszi
`+dev` verzióval, és a plugin hookja 12 óráig nem írja vissza a
telepítettel — korábban egy másik session indulása perceken belül
visszaállította a régi kódot.

- [`[9e88882b]`](https://github.com/GaborTorma/git-graph/commit/9e88882b378c32ccb7645564dc330e7a6fc8c249) · fix(data): show the files of merge commits against the first parent
- [`[38bc257f]`](https://github.com/GaborTorma/git-graph/commit/38bc257f47ee35384ef4e404776b030a29303230) · fix(hook): leave a fresh --dev-install in place for twelve hours
