# Minden worktree commitolatlan változása a listában

Minden worktree kap „Nem commitolt változások” sort, idővel, szerzővel és diffel. A saját worktree-é a lista fölötti fix sávban marad. A többié a listában ül, a fájlok `mtime`-ja szerint a commitok közé sorolva, és a worktree jelét viseli: a fő checkouté üres mappát, a többié a worktree nevét és az ágát.

Eddig csak a saját worktree változása látszott, így a párhuzamos sessionök félkész munkája rejtve maradt. Az `mtime` az ujjlenyomatba is bekerült, így egy fájlmentés is frissíti a lapot. A rögzített sor a napot is kiírja, ha nem mai. A napfejléc mutatja, hány sora van a napnak fölötte és alatta.

Ágszűrésnél a WIP-sor akkor marad, ha a worktree-je a kijelölt ágon áll. Leválasztott worktree-nél ez az app szerinti ága. Az ágválasztás utáni ugrás a kijelölés legfelső sorára visz, ami lehet ez a WIP-sor is.

- [`[ce0395cf]`](https://github.com/GaborTorma/git-graph/commit/ce0395cf2040c798b29f4615f875ca5e827e5b3d) · feat(server): time uncommitted rows by file mtime, start stub lanes afresh per commit
- [`[e8b64c69]`](https://github.com/GaborTorma/git-graph/commit/e8b64c69d12234b6880025b98329e31c40e3874b) · feat(page): other worktrees' WIP rows in the list with chips, fan-out stubs, new worktree icon
- [`[3270fb86]`](https://github.com/GaborTorma/git-graph/commit/3270fb86249319347d98d033eb7b532fd5439069) · fix(page): open an uncommitted row's panel under its own row in the pinned band
- [`[18aff3df]`](https://github.com/GaborTorma/git-graph/commit/18aff3dfe2db8c4d4a01c06c9a01c233bd399a49) · feat(page): show uncommitted rows as "Nem commitolt változások" with time, author and diff, placed by mtime
- [`[e0b170ce]`](https://github.com/GaborTorma/git-graph/commit/e0b170ce4abb1721f95e56b77b0682a3834a9a87) · feat(page): show how many of the day's rows are above and below its header
- [`[b6e06f26]`](https://github.com/GaborTorma/git-graph/commit/b6e06f26c8f8bc3693cb313dad5887b9d301b506) · fix(server): include the uncommitted files' mtime in the change fingerprint
- [`[41977053]`](https://github.com/GaborTorma/git-graph/commit/41977053e105cceecb990b89527ed6298aa58b2c) · feat(page): show the day on the pinned uncommitted row when it is not from today
- [`[646df870]`](https://github.com/GaborTorma/git-graph/commit/646df870468fb253ee50951c84d923e9c0e5d1f5) · fix(page): show only the uncommitted row of the worktree that has the filtered branch checked out
- [`[4fb45bd5]`](https://github.com/GaborTorma/git-graph/commit/4fb45bd57478798673a56f27983280f88508ea65) · fix(page): keep a detached worktree's WIP row under the branch filter and jump to it
