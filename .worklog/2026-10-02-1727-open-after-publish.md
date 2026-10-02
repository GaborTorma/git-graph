# Megnyitás publikálás után

A hook és a `/git-graph:artifact` publikálási lépései most a lap megnyitásával
zárulnak: a session a `--published` után `Artifact open`-t is hív.

Eddig a platform útmutatása alapján a frissen publikált lapot nem nyittattuk meg
külön, a gyakorlatban viszont csak a kártya jelent meg (worktree-be lépés után
mérve). A hook ugyanebben a sessionben később sem kéri a megnyitást, így a lap
rejtve maradt.

- [`[52e0d938]`](https://github.com/GaborTorma/git-graph/commit/52e0d9385752fff9169ad966c839a940065cf255) · fix(hook): open the artifact after publishing it
