# Worktree-nként saját Artifact

Minden worktree saját Artifactot kap, a saját munkakönyvtárával és Uncommitted
sorával. A kulcsai a közös `.git/config`-ban külön szakaszba kerülnek
(`git-graph.<slug>.artifact`, `….artifactHash`); a fő checkouté marad
`git-graph.artifact`. A hook az `EnterWorktree` és az `ExitWorktree` után is
lefut (PostToolUse), így a session közben nyitott worktree is megkapja a magáét.
A megszűnt worktree-k Artifactjait a hook felismeri (nincsenek már a
`git worktree list`-ben), és megkéri a sessiont, hogy törölje őket, majd
`gg --forget-artifact <URL>`-lel takarítsa a kulcsaikat. A `gg --artifacts`, a
`gg --forget` és a `/git-graph:remove` a worktree-k Artifactjait is kezeli.

A worktree-k közös configot látnak, a slugjuk viszont az útvonalukból jön: közös
kulcson egymás lapját publikálták felül, oda-vissza. Ez a régi launchd-s
változatban csendben történt, és élesben is előjött — a még futó régi agent a
worktree lapját a fő checkout Artifactjába publikálta; kézzel helyreállítva.

A *Fejlesztő* kérése szerint a takarítás a git-graph dolga, nem a
`/worktree-close`-é. Az `extensions.worktreeConfig` bekapcsolása helyett
szakaszokat használunk, mert az a repó beállítását változtatná meg.

Nyitva maradt: ha a worktree-t nem `ExitWorktree`, hanem kézi
`git worktree remove` törli, az árva Artifact csak a következő session
indulásakor derül ki.

- [`[333c5993]`](https://github.com/GaborTorma/git-graph/commit/333c599304f05687176a0d5b083d11db4e5fba6e) · feat!: publish artifacts from the session per worktree and drop the launchd server
