# Egy Artifact repónként, a worktree-k közösen látják

A git-graph mostantól repónként egyetlen Artifactot tart fenn, nem worktree-nként egyet. Minden worktree-ből ugyanaz a lap nyílik, és a `graph_data` az összes worktree-t adja: a HEAD-jüket, a commitolatlan változásaikat és az ágaikat. A slug, a `git-graph.*` kulcsok és a cím a fő checkoutra képződik le.

A worktree-nkénti lapok szétaprózták a képet: egy feature-worktree-ből nem látszott, mi történik a fő checkoutban vagy a többi sessionben. A régi, `git-graph.<slug>.*` szakaszos lapokat a hook felismeri, töröltetni kéri, majd `--forget-artifact`-tal takarít.

A platform korlátait mérve rögzítettük a findingsben: egy Artifactnak az app egyetlen keretet tart, és azt mutatja minden sessionben. Ezért a lap egy új panelhez kérdés nélkül kötődik, és a kötést újratöltés és keret-újraépítés után is megtartja. A breaking change a régi lapok megszűnése.

- [`[0b04c8c0]`](https://github.com/GaborTorma/git-graph/commit/0b04c8c0114e9b487a148c9fae59bc31190c0c9c) · docs(findings): measure a shared worktree artifact
- [`[8d8cd78c]`](https://github.com/GaborTorma/git-graph/commit/8d8cd78c0a239b064c4f2c6d6cf0ff6966a23364) · feat!: share one artifact per repo across worktrees
- [`[8a7ecea1]`](https://github.com/GaborTorma/git-graph/commit/8a7ecea18fe4410558794d0dcdd9feddcd89f145) · feat(page): hide the commit count while the footer shows an error
- [`[c366c51f]`](https://github.com/GaborTorma/git-graph/commit/c366c51f517b2c3404d30ac918db8f1b106063ae) · feat: bind a new panel to its session without a prompt
- [`[0a9a5a9d]`](https://github.com/GaborTorma/git-graph/commit/0a9a5a9d90f67dd7536a595b5ba7ca8a31dac1e2) · fix: keep the panel binding across reloads and frame rebuilds
