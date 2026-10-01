# Pillanatkép és terminálos parancsok nélkül

Kikerült a statikus HTML-pillanatkép: a parancs nélküli `gg` (most a súgót írja
ki), a `--out`, a `--title`, az `--open`, a `~/.git-graph/<slug>/index.html` és a
sablon `static` módja. A hook már nem hoz létre `~/.local/bin` linkeket és
`~/.git-graph/bin/gg` aliast, és kikerült a 0.2-es maradékokat (launchd agent,
`ggl`, szervernapló) takarító `drop_legacy()` is. Verzió: 0.4.0.

Az élő nézet az Artifact, a *Fejlesztő* statikus fájlt már nem generál. A `gg`
csak a Claude Bash eszközének kell — a skillek és a hook hívják —, az pedig a
plugin saját `bin/`-jéből jön, nem a terminálból.

Ezen a gépen a meglévő linkeket, az aliast és a git-graph config-mentéseit
(`claude_desktop_config.json.bak-*`) kézzel töröltük, hogy ne kelljen hozzájuk
takarító kód. A `write_json` továbbra is minden config-íráskor új mentést
készít — a *Fejlesztő* döntése szerint így marad.

- [`[42c9669e]`](https://github.com/GaborTorma/git-graph/commit/42c9669e854f078cd70749af309024968dc36318) · feat!: drop the static snapshot, terminal commands and legacy cleanup
