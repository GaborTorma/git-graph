---
name: author-date-order
description: A lista az --author-date-order szerint rendez (nem a VS Code Git Graph alapértelmezett --date-order-je), hogy a sorrend egyezzen a szerzői időt mutató napfejlécekkel
metadata:
  type: project
---

Döntés (a Fejlesztőé, 2026-11-10): a `graph.collect_commits` és a `stats.collect_stats`
`--author-date-order`-rel kér; a stash-ek helye is a szerzői időből (`authored_at`). A friss
commit jelölése (`computeFresh`, `committed`) marad a committer-dátumé.

**Why:** a napfejléc és a sor ideje a szerzői idő (`%aI`), a `--date-order` viszont a
committer-dátum szerint rendez. Cherry-pick és rebase (pl. a témánkénti merge) után a kettő
szétvált: a napok ugráltak, a párhuzamos ágak commitjai a pick sorrendjében keveredtek. A VS Code
Git Graph alapja a `date` (committer), az `author-date` ott választható; a `topic-merge.md`
cherry-pickjeit a szerzői idővel futtatni elvetve — a git-graph minden repón javít.

**How to apply:** új `git log`-hívás a lap sorrendjéhez `--author-date-order`-rel; ne térj
vissza a `--date-order`-re. Kapcsolódik: [[unrelated-history-detection]].
