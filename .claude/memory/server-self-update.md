---
name: server-self-update
description: A futó git-graph --mcp frissíti magát (watch_plugin → pull_update → os.execv ugyanazokon a stdio-csöveken), és leszerel, ha a plugin eltűnt az installed_plugins.json-ból
metadata:
  type: project
---

- Ha a nyilvántartás más verziót mond, mint ami fut, a szerver a plugin `installPath`-jából átmásolja
  a csomagot, a lap fájljait és a manifestet (vagy a hook már lecserélte), majd két kérés között
  `os.execv`-vel újraindul ugyanazokon a stdio-csöveken.
- Ezért puffereletlen a stdin-olvasás (`select` + `os.read`, saját sorpuffer): csak üres pufferrel
  indul újra, a csőben maradt kérést az új folyamat olvassa. A szerver a kézfogás után nem tart
  állapotot. Mérve kamu `HOME`-mal: 12/12 kérés megválaszolva a csere körül.
- A lap a `changes` verzióváltásán újratölt (`location.reload`) → az új `page_code` is megjön. Új
  tool esetén: [[tools-list-changed]].
- Leszerelés ugyanebben a szálban: az `installed_plugins.json`-ban (Claude Code belső fájl,
  `version: 2`) keresi a `git-graph@…` kulcsot. Ismeretlen formátumnál nem dönt, és csak két egymást
  követő hiány után szerel le (frissítés közbeni pillanat). Csak a stabil példányban fut
  (`sys.argv[0]` a `STABLE`); a working tree-ből indított nem szerel le. Több példány fut (az app és
  minden Code-session indít egyet), a leszerelés idempotens; ha az app nem fut, a következő indulásáig
  vár.

**Why:** nincs update/uninstall esemény ([[stable-copy-install]]), a `claude plugin update` után
mégis percen belül az új kódnak kell futnia.

**How to apply:** a stdin-olvasást ne cseréld pufferelt olvasóra; a kézfogás után ne tárolj
állapotot.
