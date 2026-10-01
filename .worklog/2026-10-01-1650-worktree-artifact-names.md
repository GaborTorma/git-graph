# Worktree-Artifactok a mappájuk nevével

Worktree-ben az Artifact neve a mappa nevét is tartalmazza:
`Git Graph (git-graph · drop-static-snapshot)`; a fő checkouté marad
`Git Graph (git-graph)`.

Worktree-nként külön Artifact van, de a választóban eddig mind azonos néven
állt. A név a publikált `<title>`-ből jön; a lap JS-e betöltéskor eddig
visszaírta a repó nevére, ezért ez a sor kikerült. A meglévő Artifact neve
újrapublikáláskor frissül — élesben kipróbálva.

- [`[af986a21]`](https://github.com/GaborTorma/git-graph/commit/af986a21aedb4cd00d7cf03a9e3ec3a1433facfe) · feat: name worktree artifacts after their folder
