# Új tool a futó szerveren: tools/list_changed

Az önfrissítő szerver (`restart`, `os.execv`) az újraindulás után
`notifications/tools/list_changed`-et küld, a kézfogásban pedig
`listChanged: true`-t jelez. Az app erre azonnal újra lekéri a tool-listát.

A `settings` tool bevezetésekor derült ki, hogy az app a szerver tool-listáját
csak a kapcsolódáskor kéri le. A frissült szerver új toolját ezért nem ismerte, és
a lap hívása `not_in_manifest`-tel bukott el; csak az app újraindítása segített.
Mérve, a jelzés után 1 ms-mal jött az új `tools/list`. A tanulság a mérési
naplóba is bekerült.

- [`[73144d29]`](https://github.com/GaborTorma/git-graph/commit/73144d2984bd2aebaf9132356eb9e061251f8881) · fix(mcp): announce the tool list change after a self-update restart
