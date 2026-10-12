# A plugin futtatása forrásból

Ha a git-graph a working tree-ből töltődik be (`CLAUDE_CODE_PLUGIN_DIRS`,
`--plugin-dir`), a hook fejlesztői példányt telepít `<verzió>+dev.src.<hash>`
verzióval. A futó szerver csak kódváltozásra indul újra, és nem írja vissza a
telepített verziót. Ezen a gépen a git-graph így fut: a `CLAUDE_CODE_PLUGIN_DIRS`
végén a repó, a telepített `git-graph@git-graph` disabled.

Eddig a forrásból futó hook a sima verzióval másolt a stabil helyre, a szerver
`pull_update`-je pedig visszaírta a telepítettet — oda-vissza. A cél az volt, hogy
a skillek, a mod és a szerver bump és `claude plugin update` nélkül kövessék a
forrást, mint a torma-ai pluginoknál.

Telepített vagy forrás: a `CLAUDE_PLUGIN_ROOT` a `~/.claude/plugins/cache` alatt
telepített, máshol forrás. A verziót ezentúl a `/workflow:release` emeli, nem a
feature-commit.

- [`[6c9b3dac]`](https://github.com/GaborTorma/git-graph/commit/6c9b3dac4f49748e2806b5dd2c2921d92eab8bd8) · feat(install): treat a plugin loaded from source as a dev instance
- [`[25a568cd]`](https://github.com/GaborTorma/git-graph/commit/25a568cdb5998a80fec1315c8ef8f01d545a849d) · docs(claude-md): drop the version bump rule from the feature commit
