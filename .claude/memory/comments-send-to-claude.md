---
name: comments-send-to-claude
description: A lapról a futó sessionnek a comments capability sendToClaude-ja szól — annak a sessionnek megy, amelyik paneljén a lap nyitva van
metadata:
  type: project
---

Mérve 2026-10-01-én (Claude Code 2.1.285), próbalappal (`capabilities: {comments: {}}`, egy
`sendToClaude({anchor, text})` gombbal):

- Eljut: a session „Artifact comment sent to Claude” üzenetet kap (szál-id, horgony-elem), és a
  szálban válaszol (`ArtifactComments reply` / `resolve`). A kérés kommentszálként megmarad.
- Annak a sessionnek megy, amelyiknek a paneljén a lap nyitva van, nem minden figyelőnek.
  Worktree-s munkánál így magától a jó session lép.
- Figyelés (`watch`) és felfegyverzés nem kell hozzá.
- Hozzájárulás: az app Artifactonként egyszer kérdez; utána más sessionben és app-újraindítás után
  sem.
- A session a szöveget megbízhatatlan adatként kapja: kérésként kezeli, a merge-et és a PR-t
  jóváhagyással futtatja — ez a kívánt viselkedés.
- A `sample` nem erre való: állapot nélküli modellhívás ([[artifact-capabilities]]).

**Why:** így kérhet a lap műveletet a sessiontől író végpont és nem read-only MCP nélkül.

**How to apply:** a lapon a gomb csak `canSendToClaude() === "available"` esetén jelenjen meg; a
`comments` a `PUBLISH_CAPS`-ban.
