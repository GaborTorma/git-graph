#!/usr/bin/env bash
# git-graph telepítő: symlinkek a PATH-ra és a Claude commands mappájába.
# Idempotens — újrafuttatható, meglévő azonos symlinket nem bánt.
#
#   ./install.sh                  symlinkek (gitgraph, gg, /git-graph parancs)
#   ./install.sh --live [--port N]  + élő szerver (launchd) és SessionStart hook
#   ./install.sh --uninstall-live   az élő rész leszerelése (symlinkek maradnak)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
CMD_DIR="$HOME/.claude/commands"
SETTINGS="$HOME/.claude/settings.json"
LABEL="co.torma.gitgraph"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
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
  "$PY_BIN" - "$1" "$SETTINGS" "$PY_BIN $REPO_DIR/gitgraph --session-hook --port $PORT" <<'PY'
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
mine = "gitgraph --session-hook"
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
    <string>$REPO_DIR/gitgraph</string>
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
  launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$UID" "$PLIST"
  echo "launchd agent: $LABEL (port $PORT)"
}

link "$REPO_DIR/gitgraph"            "$BIN_DIR/gitgraph"
link "$REPO_DIR/gitgraph"            "$BIN_DIR/gg"
link "$REPO_DIR/gitgraph"            "$BIN_DIR/ggl"   # = gg --launch-config
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
    sleep 1
    if curl -fsS -o /dev/null "http://127.0.0.1:$PORT/fingerprint"; then
      echo "Szerver válaszol: http://127.0.0.1:$PORT"
    else
      echo "FIGYELEM: a szerver nem válaszol — napló: ~/.git-graph/serve.log"
    fi
    echo
    echo "Kész. A következő session indulásakor a Browser panelen magától megjelenik a gráf."
    ;;
  uninstall)
    echo
    launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "launchd agent eltávolítva."
    patch_settings remove
    ;;
  links)
    echo
    echo "Kész. Próbáld:  gg --help"
    echo "Élő mód (Browser panel, magától frissülő gráf):  ./install.sh --live"
    ;;
esac
