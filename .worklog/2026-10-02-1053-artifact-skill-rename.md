# A skill neve: /git-graph:artifact

A repó Artifactját publikáló és megnyitó skill új neve `/git-graph:artifact`
(eddig `/git-graph:git-graph`). A mappa `skills/artifact/` lett, a README, a
CLAUDE.md és a `bin/git-graph` súgója az új nevet mondja. A verzió 0.5.0.

A régi név csak a plugin nevét ismételte, és nem derült ki belőle, mit csinál a
skill: létrehozza vagy frissíti, majd megnyitja az Artifactot.

Breaking change: aki a régi paranccsal hívta, annak az újat kell használnia. A
`docs/` mérési naplóiban és a régebbi worklogokban a régi név maradt, mert ezek
történeti bejegyzések.

- [`[3c80d9fd]`](https://github.com/GaborTorma/git-graph/commit/3c80d9fda971687ead048c5dbd4f1f2f33384c5f) · refactor!: rename the git-graph skill to artifact
