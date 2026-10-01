# Kiadás: verzió és deploy

A CLAUDE.md rögzíti, hogyan megy a kiadás: a verziót a feature-commit emeli a
`plugin.json`-ban, és a `/release` ezt tageli, nem a `git cliff` számítását; a
deploy a helyi plugin-frissítés
(`claude plugin marketplace update git-graph && claude plugin update git-graph@git-graph`).

Az első kiadásnál (v0.3.0) derült ki: a `git cliff` tag híján `v0.1.0`-t
számolt, a projektnek pedig nem volt deploy-módja. A marketplace forrása a repó
`main`-je, tehát a merge már élesít — a deploy-lépésben csak a saját gép
frissítése marad.

- [`[ed4be6c4]`](https://github.com/GaborTorma/git-graph/commit/ed4be6c4f4a7bcd06e9de4ecdc95cdcfa094d148) · docs(claude): record release versioning and deploy mode
