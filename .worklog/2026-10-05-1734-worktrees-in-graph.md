# Worktree-k a gráfban

A hozzáadott worktree-k külön sávot kapnak a gráfban, a fő checkout ágai után, halvány elválasztóval. Az elágazási pontjuk fölött hátrébb húzódnak. Halványabb mindaz, ami nem a saját worktree-é. A gazdátlan ágak (amelyekről a git nem tudja, hol jöttek létre) a fő checkouthoz számítanak.

A saját commit és WIP nélküli worktree HEAD-je (például egy trunk-commiton, vagy leválasztva) csonkot kap, így ez is látszik elágazásként. A worktree-k a létrehozásuk sorrendjében jelennek meg, nem név szerint.

A leválasztott HEAD-ű worktree ágát a git nem jegyzi fel. A Claude app `git-worktrees.json`-ja viszont igen, ezért onnan jön (`appBranch`). Név szerinti egyeztetést szándékosan nem használunk, mert az félrevitt.

- [`[7f6b62ef]`](https://github.com/GaborTorma/git-graph/commit/7f6b62ef9dc1529bb78fbc291241884d0f4cb1b2) · feat(page): tell worktree pills apart from branches and show how far ahead they are
- [`[2fb97b39]`](https://github.com/GaborTorma/git-graph/commit/2fb97b39e65e5300975dadbdd2d2eb7cfa20900d) · feat(page): show only real worktrees as pills and branch them off the main line
- [`[b3374901]`](https://github.com/GaborTorma/git-graph/commit/b3374901c5d3af81ee5b9428c5486204d8992478) · feat(page): put worktree lanes after the main checkout's branches with a faint separator
- [`[108ca888]`](https://github.com/GaborTorma/git-graph/commit/108ca888bf81d376dbf374eecaa342fc6bbcb7e1) · feat(page): dim what is not in the own worktree instead of a manual pick
- [`[97c5710b]`](https://github.com/GaborTorma/git-graph/commit/97c5710bcd8df45c527a1b023b104b95d5218372) · fix(page): move worktree lanes back only above their fork point
- [`[ed95de58]`](https://github.com/GaborTorma/git-graph/commit/ed95de58c4badf400c65dcf00c64faee451b7f32) · feat(page): treat unowned branches as the main checkout's when dimming
- [`[22d40d58]`](https://github.com/GaborTorma/git-graph/commit/22d40d58b3cd518727eec4051860a0e921f0759e) · feat(page): branch a commitless worktree HEAD off with a stub, group worktree badges
- [`[a5934f2e]`](https://github.com/GaborTorma/git-graph/commit/a5934f2e057e903d4a18428167544ef2df0ee0c1) · docs(claude): note the worktree stubs
- [`[c81375e2]`](https://github.com/GaborTorma/git-graph/commit/c81375e2352f04720a49a79142cf3ea3a6b231c9) · docs(findings): find a detached worktree's branch in the Claude app registry
- [`[68496fd9]`](https://github.com/GaborTorma/git-graph/commit/68496fd93ef04d36dd73a5901b7a2e18f4351d19) · fix(page): tie a detached worktree to its branch via the app registry, not the name
- [`[2009faf1]`](https://github.com/GaborTorma/git-graph/commit/2009faf1504875b403b42e1ae6673fbd4390e26b) · feat(server): order linked worktrees by creation time
- [`[26cbc7b9]`](https://github.com/GaborTorma/git-graph/commit/26cbc7b9fc540a4aca2c24fbfd429155d2b84657) · refactor(server): drop the unused per-worktree ahead/behind, share worktree helpers
