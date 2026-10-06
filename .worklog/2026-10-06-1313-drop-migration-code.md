# Kikerült a régi telepítések átmeneti kódja

Kikerült a 0.12 előtti, worktree-nkénti lapok takarítása (a hook kérése és a `--forget-artifact` parancs), az elavult lap külön hibaüzenete, a 0.10.x szerver lapfájl-pótlása, és a betöltő „régebbi szerver” ága. A kód így csak azt írja le, ahogy ténylegesen működni akarunk.

A törlés előtt a Fejlesztő gépén minden ismert repóban kitakarítottuk a régi `git-graph.<slug>.*` szakaszokat; a két hozzájuk tartozó Artifact már nem létezett. A `not_in_manifest` a betöltőben most csak az elutasított engedélyt jelenti, a lapon pedig az engedélyt vagy az elavult lapot, amelyet a hook újrapublikáltat. A `remove` skill repónként egy lappal számol.

A betöltő változott, ezért minden repó lapját a hook egyszer újrapublikáltatja.

- [`[e02476ae]`](https://github.com/GaborTorma/git-graph/commit/e02476aef54dd45450d22f3b16e28f8fe1e9ad1c) · refactor: drop the migration code for pre-0.12 per-worktree pages and the 0.10.x server
