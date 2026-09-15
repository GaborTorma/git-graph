#!/usr/bin/env bash
# git-graph telepítő: symlinkek a PATH-ra és a Claude commands mappájába.
# Idempotens — újrafuttatható, meglévő azonos symlinket nem bánt.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
CMD_DIR="$HOME/.claude/commands"

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

link "$REPO_DIR/gitgraph"            "$BIN_DIR/gitgraph"
link "$REPO_DIR/gitgraph"            "$BIN_DIR/gg"
link "$REPO_DIR/commands/git-graph.md" "$CMD_DIR/git-graph.md"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo; echo "FIGYELEM: $BIN_DIR nincs a PATH-on — add hozzá a shell rc-dhez." ;;
esac

echo
echo "Kész. Próbáld:  gg --help"
