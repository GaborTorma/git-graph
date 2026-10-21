---
name: mcp-stdout-protocol
description: A git-graph --mcp stdout-ja a JSON-RPC csatorna — csak protokoll mehet rá, ASCII-ban; napló stderr-re
metadata:
  type: project
---

- A szerver stdout-ja a JSON-RPC 2.0 csatorna, soronként egy üzenet: minden más kiírt sor elrontja a
  kapcsolatot az appal.
- A `json.dumps` alapértelmezett ASCII-kimenete megy ki (`ensure_ascii`): a bájtok így nem függnek az
  indító környezet locale-jától (az app minimális környezettel indít, [[mcp-wire-format]]).
- Napló, ha kell, stderr-re (`log`); a hook stdout-ja ugyanígy a hook-JSON-é ([[stable-copy-install]]).

**Why:** a stdio-szervert az app indítja, a stdout-ot ő olvassa protokollként.

**How to apply:** `print()` a szerver útján tilos; új kimenet a `send`-en át, diagnosztika a `log`-gal.
