---
name: stable-copy-install
description: Nincs install/update/uninstall esemény — a SessionStart hook telepít; az app a stabil zipet futtatja (nem symlinket), atomi cserével, lap → zip → manifest sorrendben
metadata:
  type: project
---

- A plugin-rendszerben nincs install/update/uninstall esemény → a gépi részt a SessionStart hook
  állítja be (`ensure_installed`), csak ha a kód gyökere (`ROOT`) a `CLAUDE_PLUGIN_ROOT`; egy kézi
  `--session-hook` nem telepít. Minden lépés idempotens, csak változáskor ír. A hook stdout-ja a
  hook-JSON-é, napló csak stderr-re (`log`).
- A `CLAUDE_PLUGIN_ROOT` verziónként más (`…/cache/git-graph/git-graph/<verzió>/`) → az app a stabil
  másolatot futtatja (`~/.git-graph/bin/git-graph`). Symlinket nem, mert a régi verzió mappája
  eltűnhet.
- A másolat a csomag egyetlen futtatható zipben (`stable_bundle`; `python3 <zip>`): egy fájl, atomi
  csere, egy épp induló szerver sosem lát félig új csomagot. Tömörítés és időbélyeg nélkül, így
  változatlan forrásból bájtra ugyanaz.
- Sorrend: a lap fájljai (`~/.git-graph/page/`) → zip → manifest
  (`~/.git-graph/.claude-plugin/plugin.json`) utolsóként. A zip a verzióját ebből olvassa; egy
  közben induló újraindulás különben a régi kódot az új verziónak hinné, és nem frissülne tovább. A
  `--dev-install` is így ír (`install_copy`).
- A lap fájljait a szerver induláskor egyszer olvassa be (`page_file`): a futó verzió a saját kódját
  adja, akkor is, ha a hook már újat másolt. A `RUNNING_VERSION` a manifestből jön, a `changes` a
  telepítettel együtt adja → a lábléc jelzi, ha még a régi kód fut.
- A `bin/` csak a Bash eszköz PATH-ja, a hooké nem: a hook a `${CLAUDE_PLUGIN_ROOT}/bin/git-graph`-ot
  hívja.
- Bump nélkül a `claude plugin update` nem hoz le semmit ([[version-bump-in-release]]).

**Why:** a kód a futó szerver alatt cserélődik; félig új állapot nem lehet.

**How to apply:** a telepítési sorrenden ne változtass; új telepített fájl a lap elé vagy a zip
mellé, a manifest mindig utolsó. Frissítés futás közben: [[server-self-update]].
