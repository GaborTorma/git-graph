# Az Artifact sessionönként egyszer nyílik meg

A SessionStart hook mostantól egy sessionben csak egyszer kéri a repó (worktree)
Artifactjának megnyitását. Ha a lap új verziója jön, a publikálást továbbra is
mindig kéri.

Eddig minden SessionStartnál (`compact`, `resume`, `/clear`) és minden
worktree-váltásnál újra megnyittatta a lapot, pedig az a sessionben nyitva maradt.

A `~/.git-graph/sessions.json` sessionönként (`session_id`) rögzíti, melyik repó
lapját kérte már a hook. A kulcs a repó slugja, nem az URL: így egy friss
publikálás után sem kér külön megnyitást, egy másik worktree lapját viszont
megnyittatja. A `source`-ot nem nézi, mert a `resume` és a `/clear` sem zárja be a
sessionben megnyitott lapot. A `SessionEnd`-et elvetettük, mert app-bezáráskor is
lefut, archiválásra pedig nincs hook. A bejegyzéseket ezért 7 nap után maga a hook
törli.

Nyitva maradt: ha a `/clear` új `session_id`-t ad, a lap egyszer újra megnyílik.
Ez ártalmatlan, de nincs kimérve.

- [`[91531f69]`](https://github.com/GaborTorma/git-graph/commit/91531f69e63da7e6dca4aa93ce5c28a9a6948fa3) · feat(hook): open the artifact only once per session
