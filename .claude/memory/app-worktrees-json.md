---
name: app-worktrees-json
description: A leválasztott HEAD-ű worktree ágát a git nem jegyzi, a Claude app git-worktrees.json-ja igen
metadata:
  type: reference
---

Session törlésekor a Claude app a worktree-t és az ágat megtartja, a HEAD-et leválasztja (a
reflogban egyetlen, üzenet nélküli bejegyzés). A git ezután semmivel nem köti az ágat a
worktree-hez: az ágnak nincs reflogja, a worktree configjában nincs nyoma (mérve, 2026-10-05).

Az app nyilvántartja: `~/Library/Application Support/Claude/git-worktrees.json` →
`worktrees.<név>` = `{path, branch, sourceBranch, leasedBy, …}` (`leasedBy: null`: nincs hozzá
session). A worktree admin-mappájában egy üres `claude-desktop-worktree` jelzőfájl is van.

Kód: `app_worktree_branches` (a worktree `appBranch` mezője); név szerint nem azonosítunk.
Kapcsolódik: [[app-focus-sources]], [[branch-base-origin-head]].
