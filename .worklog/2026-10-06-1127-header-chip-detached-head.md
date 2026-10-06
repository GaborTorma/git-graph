# Fejléc-chip és leválasztott HEAD

A fejléc chipje ugyanúgy épül, mint a saját HEAD commit-chipje: ugyanaz az ikon, ugyanazok a remote-szakaszok és távolságok, teli háttérrel. A chip gomb: rákattintva a lista a saját HEAD-hez ugrik. Ha az ágválasztó elrejti a HEAD-et, a chip halványabb, és kattintásra előbb minden ágra áll vissza.

Leválasztott HEAD-nél lánc ikon áll az ág-ikon helyén, a chipen „HEAD” vagy a hash, worktree-nél előtte a worktree jele és neve. Mellette a HEAD-commit távolsága az alapágtól, ezt a szerver számolja (`worktree_meta`). Egy HEAD git szerint vagy ágon, vagy közvetlenül egy commiton áll; ha nincs ág, ezt a jelölésnek el kell mondania, mert a régi Git Graph nem különböztette meg.

A végén egy `/simplify`-kör közös helperekbe vonta a fejléc- és a commit-chip közös részeit. A szerveren az előny/lemaradás számolása egyetlen függvény lett.

Nyitva maradt: halványítson-e és álljon-e vissza a keresés és a „Csak ref-es commitok” is a chipre kattintva.

- [`[4e240548]`](https://github.com/GaborTorma/git-graph/commit/4e240548beda212d6c27fec6fb6b1b9be8b3f1b5) · feat(page): label a detached worktree HEAD and show its distance from the base branch
- [`[97b59f99]`](https://github.com/GaborTorma/git-graph/commit/97b59f99c8c72f4e124b7621958b39efc8a9e4c1) · fix(page): keep the remote switch redrawing when remotes are turned off
- [`[e4896eca]`](https://github.com/GaborTorma/git-graph/commit/e4896ecaf01b32c600ea58ba408f28317d422f1b) · feat(page): jump to the own HEAD commit when the header chip is clicked
- [`[ffadf8d3]`](https://github.com/GaborTorma/git-graph/commit/ffadf8d3d6493a4fa9f004f039d404597c2b454a) · fix(page): make the header chip a real button so the a11y lint passes
- [`[9b36f794]`](https://github.com/GaborTorma/git-graph/commit/9b36f794a7214e132f98280cf4236173d8a6ed37) · feat(page): dim the header chip when the branch filter hides HEAD, reset the filter on click
- [`[87fdcaa4]`](https://github.com/GaborTorma/git-graph/commit/87fdcaa43ac8e41ed17f8ad592010e78f0ad31b8) · refactor: share chip helpers between the header and commit badges, one ahead-behind helper
