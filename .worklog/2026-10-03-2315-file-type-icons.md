# Fájltípus-ikonok

A kinyitott commit fájljai előtt a típusuk ikonja áll, a Catppuccin VS Code
készletéből (MIT), a lap saját színeire kötve, világos és sötét témában is.

A hozzárendelést (fájlnév, leghosszabb kiterjesztés) a szerver végzi, és a
`graph_data` csak a használt ikonok SVG-jét küldi: a teljes, kb. 270 KB-os
készlet nem utazik minden betöltéskor. A készletet a
`scripts/file-icons.py` állítja elő, verzióra rögzítve. A fájlsor változás-
csíkja halványabb lett, hogy ne ez legyen a sor legerősebb eleme.

- [`[e584d82a]`](https://github.com/GaborTorma/git-graph/commit/e584d82ac6deb01f1050e3a0b86a9c1dcfa15498) · feat(page): show file type icons from catppuccin in the file list
- [`[c672ae5c]`](https://github.com/GaborTorma/git-graph/commit/c672ae5cc168f6d6997e8afe9cf6213ed4235b19) · style(page): soften the file change bars
