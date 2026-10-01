# Önállóan települő Claude Code plugin

A git-graph mostantól Claude Code plugin, saját marketplace-szel: maga a repó a
`git-graph` marketplace, benne egyetlen plugin (`git-graph@git-graph`). A
pluginnal jön a `/git-graph:git-graph` skill, a SessionStart hook, és a Claude
Bash eszközének PATH-jára a `git-graph` / `gg` / `ggl`. A script a `bin/` alá
költözött, az `install.sh` megszűnt.

Eddig kézi telepítés volt (`install.sh --live`), verzió nélkül, a fő checkoutra
mutató symlinkekkel és launchd-vel — egy `dev`-frissítés vagy mappaátnevezés
alatta eltörte. A cél egy verziózható, magától települő és magától leszerelődő
csomag volt.

A `torma-ai` név nem volt újrahasznosítható: egy gépen egy marketplace-név csak
egyszer regisztrálható, a második felülírná a `claude-plugins` repóét. A
`torma-ai` felvehette volna külső forrásként, de a *Fejlesztő* a saját,
független marketplace-t választotta.

A pluginnak nincs install/update/uninstall eseménye, ezért a gépi részt a
SessionStart hook állítja be, első futáskor és minden verzióváltáskor,
idempotensen: stabil másolat a `~/.git-graph/bin`-be (a plugin útvonala
verziónként más, a régi mappa el is tűnhet), `~/.local/bin` linkek, launchd
agent (új kódnál újraindul), és a `git-graph` MCP a Claude app configjában —
ha ez változott, a session szól, hogy az appot újra kell indítani. A régi
telepítés maradványait (globális hook, `~/.claude/commands` symlink) eltakarítja.
A leszerelést a futó `gg --serve` végzi: percenként nézi az
`installed_plugins.json`-t, és ha a plugin két egymást követő ellenőrzésnél
hiányzik, mindent leszed, végül saját magát. Ismeretlen formátumnál nem dönt —
ez a Claude Code belső fájlja.

Kipróbálva: a telepítés és a leszerelés kamu `HOME`-ban, rögzítőre cserélt
`launchctl`-lel; élesben a worktree-ből felvett helyi marketplace-szel — az
átállás után az app újraindítva a stabil példányból indítja a `gg --mcp`-t, a
Claude-ból hívott `fingerprint` válaszol.

Nyitva maradt: az élő leszerelési próba (törölné a `~/.git-graph/repos.json`-t),
és merge után a marketplace átállítása a helyi worktree-ről a GitHubra
(`claude plugin marketplace add GaborTorma/git-graph`). A fő checkoutban egy
commitolatlan `git-graph`-módosítás vár döntésre — a feature-ágon ez a fájl
`bin/git-graph`.

- [`[70aa8154]`](https://github.com/GaborTorma/git-graph/commit/70aa815432d8b283cc6d99aa8334bfe14858209f) · feat!: ship as a self-installing claude code plugin
