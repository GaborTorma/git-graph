# Egy felejtő parancs: artifact-forget

A `/git-graph:forget-all-artifacts` megszűnt; az `/git-graph:artifact-forget`
kérdezi meg, hogy csak az aktuális repó Artifactja törlődjön, vagy mind (a plugin
eltávolítása előtt ez kell). Csak egyértelmű választásra töröl.

Két parancs ugyanarra a műveletre csak más hatókörrel fölösleges volt. Közben
kipróbált változat volt a `--all` argumentum, de a választás a kérdésben
egyszerűbb.

- [`[f0910d00]`](https://github.com/GaborTorma/git-graph/commit/f0910d000ede474fd18330eb10829c2821a86ac6) · feat(skills): merge the forget commands into artifact-forget with a scope choice
