#!/usr/bin/env bash
# git-graph telepítő: symlinkek a PATH-ra és a Claude commands mappájába.
# Idempotens — újrafuttatható, meglévő azonos symlinket nem bánt.
#
#   ./install.sh                  symlinkek (git-graph, gg, /git-graph parancs)
#   ./install.sh --live [--port N]  + élő szerver (launchd), SessionStart hook és
#                                   a git-graph MCP a Claude app configjában
#   ./install.sh --uninstall-live   az élő rész leszerelése (symlinkek maradnak)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
CMD_DIR="$HOME/.claude/commands"
SETTINGS="$HOME/.claude/settings.json"
# A Claude app saját MCP-configja: az Artifact `host:git-graph` hívásai csak az
# innen indított szervert érik el (a `claude mcp add`-os nem számít — mérve).
APP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
LABEL="ai.torma.git-graph"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
OLD_LABEL="co.torma.gitgraph"   # korábbi név — telepítéskor/leszereléskor eltávolítjuk
# A rendszer Pythonja: a launchd minimális környezetében is biztosan megvan,
# és nem tűnik el egy homebrew-frissítéssel. A script stdlib-only, elég neki.
PY_BIN="/usr/bin/python3"
PORT=7788
MODE="links"

while [ $# -gt 0 ]; do
  case "$1" in
    --live) MODE="live" ;;
    --uninstall-live) MODE="uninstall" ;;
    --port) PORT="${2:?--port után szám kell}"; shift ;;
    *) echo "Ismeretlen kapcsoló: $1" >&2; exit 2 ;;
  esac
  shift
done

link() {
  local src="$1" dst="$2"
  [ -e "$src" ] || { echo "Kihagyva (nincs meg): $src"; return; }
  mkdir -p "$(dirname "$dst")"

  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
    echo "Naprakész: $dst"
    return
  fi
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    # Egy korábbi telepítés symlinkje: kérdés nélkül átirányítjuk.
    if [ -L "$dst" ]; then
      echo "Átirányítva: $dst  ($(readlink "$dst") → $src)"
      rm -f "$dst"
    else
      # Valódi fájl/mappa — ezt csak kézi jóváhagyással bántjuk. A `|| a=""`
      # kell, különben EOF-on (nem interaktív futás) a `set -e` némán kilép.
      local a=""
      read -r -p "Létezik VALÓDI fájl: $dst — felülírjam symlinkkel? [i/N] " a || a=""
      [[ "$a" =~ ^[iI]$ ]] || { echo "Kihagyva (nem symlink): $dst"; return; }
      rm -rf "$dst"
    fi
  fi
  ln -s "$src" "$dst"
  echo "Symlink: $dst → $src"
}

# A SessionStart hook be-/kivétele a globális Claude settingsből. Mentést készít,
# és a saját bejegyzését azonosítja — idegen hookokhoz nem nyúl.
patch_settings() {   # $1: "add" | "remove"
  "$PY_BIN" - "$1" "$SETTINGS" "$PY_BIN $REPO_DIR/git-graph --session-hook --port $PORT" <<'PY'
import json, shutil, sys, time
from pathlib import Path

action, path, command = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
data = {}
if path.exists():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        sys.exit(f"HIBA: {path} nem érvényes JSON — kézzel kell javítani.")
    shutil.copy2(path, path.with_suffix(f".json.bak-{time.strftime('%Y%m%d%H%M%S')}"))

hooks = data.setdefault("hooks", {})
groups = hooks.setdefault("SessionStart", [])
mine = "graph --session-hook"   # a régi (gitgraph) és az új (git-graph) név is
kept = [g for g in groups
        if not any(mine in h.get("command", "") for h in g.get("hooks", []))]
dropped = len(groups) - len(kept)

if action == "add":
    kept.append({"hooks": [{"type": "command", "command": command}]})
    print("Hook frissítve." if dropped else "Hook felvéve.")
else:
    print("Hook eltávolítva." if dropped else "Nem volt felvéve hook.")

if kept:
    hooks["SessionStart"] = kept
else:
    hooks.pop("SessionStart", None)
    if not hooks:
        data.pop("hooks", None)

path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

# A git-graph MCP be-/kivétele a Claude app configjából. Csak változáskor ír,
# előtte mentést készít; a többi szerver-bejegyzéshez és kulcshoz nem nyúl.
patch_app_config() {   # $1: "add" | "remove"
  "$PY_BIN" - "$1" "$APP_CONFIG" "$PY_BIN" "$REPO_DIR/git-graph" <<'PY'
import json, shutil, sys, time
from pathlib import Path

action, path, python, script = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4]
data = {}
if path.exists():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        sys.exit(f"HIBA: {path} nem érvényes JSON — kézzel kell javítani.")

servers = data.setdefault("mcpServers", {})
entry = {"command": python, "args": [script, "--mcp"]}
if action == "add":
    if servers.get("git-graph") == entry:
        print("Claude app config: a git-graph MCP naprakész.")
        sys.exit(0)
    servers["git-graph"] = entry
    done = "Claude app config: git-graph MCP felvéve — az app újraindítása után él."
else:
    if servers.pop("git-graph", None) is None:
        print("Claude app config: nem volt benne git-graph MCP.")
        sys.exit(0)
    if not servers:
        data.pop("mcpServers")
    done = "Claude app config: git-graph MCP eltávolítva (az app újraindításával szűnik meg)."

if path.exists():
    shutil.copy2(path, path.with_name(path.name + f".bak-{time.strftime('%Y%m%d%H%M%S')}"))
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(done)
PY
}

# A régi néven futó agent: különben a régi plist a következő bejelentkezéskor
# újraindulna, és a két szerver ugyanazért a portért versenyezne.
remove_old_agent() {
  launchctl bootout "gui/$UID/$OLD_LABEL" 2>/dev/null || true
  rm -f "$HOME/Library/LaunchAgents/$OLD_LABEL.plist"
}

install_agent() {
  mkdir -p "$(dirname "$PLIST")" "$HOME/.git-graph"
  cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY_BIN</string>
    <string>$REPO_DIR/git-graph</string>
    <string>--serve</string>
    <string>--port</string>
    <string>$PORT</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$HOME/.git-graph/serve.log</string>
  <key>StandardErrorPath</key><string>$HOME/.git-graph/serve.log</string>
</dict>
</plist>
PLIST_EOF
  remove_old_agent
  launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
  # A bootout aszinkron: amíg a régi példány le nem állt, a bootstrap
  # „5: Input/output error"-ral elbukik (mérve). Az utolsó próba hibája látszik.
  local tries=0
  until launchctl bootstrap "gui/$UID" "$PLIST" 2>/dev/null; do
    tries=$((tries + 1))
    [ "$tries" -lt 10 ] || { launchctl bootstrap "gui/$UID" "$PLIST"; break; }
    sleep 0.5
  done
  echo "launchd agent: $LABEL (port $PORT)"
}

link "$REPO_DIR/git-graph"            "$BIN_DIR/git-graph"
link "$REPO_DIR/git-graph"            "$BIN_DIR/gg"
link "$REPO_DIR/git-graph"            "$BIN_DIR/ggl"   # = gg --launch-config
link "$REPO_DIR/commands/git-graph.md" "$CMD_DIR/git-graph.md"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo; echo "FIGYELEM: $BIN_DIR nincs a PATH-on — add hozzá a shell rc-dhez." ;;
esac

case "$MODE" in
  live)
    echo
    install_agent
    patch_settings add
    patch_app_config add
    sleep 1
    if curl -fsS -o /dev/null "http://127.0.0.1:$PORT/fingerprint"; then
      echo "Szerver válaszol: http://127.0.0.1:$PORT"
    else
      echo "FIGYELEM: a szerver nem válaszol — napló: ~/.git-graph/serve.log"
    fi
    echo
    echo "Kész. A következő session indulásakor a Browser panelen magától megjelenik a gráf."
    echo "Az Artifactok élő adatához a Claude appot egyszer újra kell indítani (az app csak"
    echo "induláskor olvassa a configját, onnan indítja a git-graph MCP-t)."
    ;;
  uninstall)
    echo
    launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    remove_old_agent
    echo "launchd agent eltávolítva."
    patch_settings remove
    patch_app_config remove
    ;;
  links)
    echo
    echo "Kész. Próbáld:  gg --help"
    echo "Élő mód (Browser panel, magától frissülő gráf):  ./install.sh --live"
    ;;
esac
