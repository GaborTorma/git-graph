# Robusztusabb session-napló

A hook a `~/.git-graph/sessions.json`-t ideiglenes fájlon át, atomi cserével írja.
Ha az írás nem sikerül, naplóz és fut tovább. Headless sessionben nem ír bejegyzést.

A v0.6.0 élesítése után a valódi naplóban látszott, hogy az app indulásakor több
session hookja fut néhány másodpercen belül. A sima visszaírásnál egy hook félig írt
fájlt olvashatott be, amit üresnek vett. Ilyenkor felülírta a naplót, és minden
session újra megnyitotta a lapot. Írási hibánál (`OSError`) a hook elhasalt, és a
publikálást sem kérte.

Párhuzamos írásnál egy bejegyzés továbbra is elveszhet. Ez szándékosan maradt így,
mert legfeljebb egy fölösleges megnyitás a következménye. Zárolás ezért nem kellett.
Próba: 20 párhuzamos hook után ép volt a fájl és nem maradt ideiglenes fájl;
írhatatlan mappánál a hook kimenete megmaradt.

- [`[6ff5190c]`](https://github.com/GaborTorma/git-graph/commit/6ff5190c8ccce9b3fdbf0bd642f36eb8db024df0) · fix(hook): write the session log atomically and survive write errors
