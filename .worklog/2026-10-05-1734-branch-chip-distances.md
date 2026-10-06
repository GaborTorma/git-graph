# Ág-chipek: remote-ok és távolságok

Az ág-chipek többet mondanak. Ha a helyi ág egy helyen áll a remote párjával, egyetlen felhő-és-ág ikon jelzi, és az alapágé teli. Az `origin/HEAD` beolvad a céljába, a remote-only ágak szürke chipet kapnak `origin/` előtag nélkül. Több remote-nál a chip remote-onként egy-egy szakaszt kap a remote nevével. A chipek a commit sávjának színét viselik.

Minden ág chipjén látszik a távolsága az alapágtól (az `origin/HEAD` céljától), és ha eltér, az upstreamjétől is. A remote-only chipen a helyi párjától mért távolság áll utolsóként. Egyetlen `for-each-ref` adja mindezt (`%(ahead-behind:…)`). A forrás-ágat szándékosan nem használjuk: az ágak alja mindig az `origin/main`.

Ha a helyi `main` előrébb jár a remote-jánál, az anomália, ezért figyelmeztető színt és magyarázatot kap. Kikapcsolt remote ágaknál a remote-hoz mért szakaszok és a felhők is eltűnnek.

- [`[81cd693c]`](https://github.com/GaborTorma/git-graph/commit/81cd693c7050c493d14af713b22a2fde412dec5b) · feat(page): fold origin/HEAD into its target and drop the origin/ prefix on remote chips
- [`[35cbe466]`](https://github.com/GaborTorma/git-graph/commit/35cbe466b42a8815f3dec033162c2af30c524a43) · feat(page): name the remotes on synced branch badges when a repo has several
- [`[221a2aaa]`](https://github.com/GaborTorma/git-graph/commit/221a2aaafee56f3d1245abb9a693ff5144a83809) · feat(page): color branch, HEAD and tag badges by their commit's lane
- [`[9ea3ba52]`](https://github.com/GaborTorma/git-graph/commit/9ea3ba522cd6efca75988d5f93a5f0cca159edde) · feat(page): show each branch's distance from the base branch and its upstream on its chip
- [`[f8d29ede]`](https://github.com/GaborTorma/git-graph/commit/f8d29ede2ab49025506ee14a5a3a43c71f00b87c) · feat(page): show a remote branch's distance from its local branch last on its chip
- [`[38a4cbc9]`](https://github.com/GaborTorma/git-graph/commit/38a4cbc982eff9a182efe9932e3aafabf363af24) · feat(page): flag unpushed commits on the base branch's local copy
- [`[826dd61f]`](https://github.com/GaborTorma/git-graph/commit/826dd61fbf4492794312c87f6d7f6c7d563999bf) · test: cover branch distances from the base branch, upstream and local pair
- [`[921e05e2]`](https://github.com/GaborTorma/git-graph/commit/921e05e2bdae8d3ff96521060e4483fd93a7d340) · docs: describe branch distance segments and uncommitted row placement
- [`[2695c117]`](https://github.com/GaborTorma/git-graph/commit/2695c117edb51971905ecac7935bd33a74fd9748) · feat(page): branch distances on the base branch's remote, uncommitted badges and tooltips
- [`[a6c4cc50]`](https://github.com/GaborTorma/git-graph/commit/a6c4cc505d693e70ab217e6a88151ede9a79895a) · fix(page): hide only remote-only history and remote badges when remote branches are off
- [`[a0f8ec99]`](https://github.com/GaborTorma/git-graph/commit/a0f8ec997677cd84fcb52ce443714ef24fc00ce9) · feat(page): mark a branch synced with its upstream by one cloud-and-branch icon, one icon column
- [`[3f5a1dd7]`](https://github.com/GaborTorma/git-graph/commit/3f5a1dd7b80187f0b3eebaccd09491e32f6e70fe) · refactor(page): index commits once per data load, one remote-switch reader, opt-in checkmarks
