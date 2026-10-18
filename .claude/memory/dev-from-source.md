---
name: dev-from-source
description: Fejlesztés élő lappal és forrásból futó pluginnal ezen a gépen — --dev-install (+dev, 12 óra), CLAUDE_CODE_PLUGIN_DIRS, a hook, a publikálás és a telepítés kézi próbája kamu HOME-mal
metadata:
  type: project
---

- `python3 bin/git-graph --dev-install`: a working tree az appban futó szerver helyére, `+dev`
  verzióval (`install_copy`). A szerver 15 s-on belül átvált, a lap újratölt, és az app minden
  git-graph lapja az új kódot mutatja. A hook 12 óráig nem másolja vissza a telepítettet
  (`dev_active`).
- Forrásból futó plugin ezen a gépen: `~/.claude/settings.json` → `env.CLAUDE_CODE_PLUGIN_DIRS` végén
  `:…/git-graph`; a `git-graph@git-graph` disabled, de telepítve marad (a leszerelés a nyilvántartás
  kulcsát nézi). A skillek és a mod a working tree-ből jönnek (skillhez `/reload-plugins`), a hook
  minden session indulásakor `<verzió>+dev.src.<hash>` verzióval telepít (`source_digest`). A szerver
  csak kódváltozásra indul újra, a `pull_update` nem másol vissza. A `CLAUDE_PLUGIN_ROOT` a
  `~/.claude/plugins/cache` alatt = telepített, máshol = forrás.
- A lapot a sessionből publikált Artifacton, a Claude appban kell nézni (az app MCP-naplója a
  host-híd hívásait nem mutatja — [[host-bridge-limits]]).
- Hook és publikálás kézi próbája: `--session-hook` kamu `HOME`-mal, `CLAUDE_PLUGIN_ROOT`-tal és
  `CLAUDE_CODE_ENTRYPOINT`-tal, eldobható klónon (a `--published` a `.git/config`-ba ír). A kimenet a
  publikálás lépéseit vagy a megnyitást kéri.
- Telepítés (`ensure_installed`, `uninstall`, `watch_plugin`): kamu `HOME`-mal, a modult betöltve — az
  app configja és a `~/.git-graph` is a `HOME` alól jön, a valódihoz a próba nem nyúl.
- Kézzel még: a `graph_data` több repón (eltérő sávszámmal, merge-ekkel).

**Why:** a Check ezt nem fedi le: a valódi app, a host-híd és a plugin-gyorstár csak kézzel
próbálható.

**How to apply:** a válaszban írd ki a futó verziót (`<verzió>+dev.<időbélyeg>`) — a lap láblécén
ebből látszik az új állapot. Telepítés: [[stable-copy-install]].
