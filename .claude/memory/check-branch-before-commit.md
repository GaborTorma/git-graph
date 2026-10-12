---
name: check-branch-before-commit
description: Commit előtt ellenőrizd a kivett ágat — a Fejlesztő menet közben ágat válthat a worktree-ben (tesztág)
metadata:
  node_type: memory
  type: feedback
  originSessionId: cf7247b5-7763-471b-afd3-48522b80fcc1
  modified: 2026-10-04T08:39:13.897Z
---

Commit előtt mindig `git branch --show-current` — ne a session elején megjegyzett ágra hagyatkozz.

**Why:** 2026-10-04-én a Fejlesztő a git-graph feature-worktree-jében tesztághoz (`workree-test`) váltott, miközben dolgoztam; a következő commitom a tesztágra került, amit kért, hogy ne bántsak. Vissza kellett állítani (`git switch` + `git branch -f`).

**How to apply:** minden commit (és push) előtt nézd meg az ágat; ha nem a várt feature-ág, állj meg és kérdezz, ne commitolj. Kapcsolódik: [[dig-before-declaring-limits]]
