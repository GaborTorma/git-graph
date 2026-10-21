- [Mélyebb utánajárás korlát előtt](dig-before-declaring-limits.md) — „nem lehet” előtt kísérlet és bizonyíték
- [Max 20x — kvóta nem szempont](max20-quota-irrelevant.md) — döntésnél sebesség/egyszerűség számít, nem a tokenköltség
- [GitLens nem dizájnminta](no-gitlens-design.md) — precedensnek jó, kinézetet ne vegyünk át tőle
- [Ág ellenőrzése commit előtt](check-branch-before-commit.md) — a Fejlesztő menet közben ágat válthat a worktree-ben
- [Commit-ikon tilos](no-commit-icon.md) — a h-alakú VS Code Git Graph-os commit ikont sehol ne használd
- [Ne ismételj ikont](no-redundant-icons.md) — chipen csak olyan ikon, ami nem derül ki a chipből (branch-chip távolsága ikon nélkül)
- [A verziót a release emeli](version-bump-in-release.md) — plugin.json bump csak a /workflow:release-ben

## Lap

- [CSS-osztály ütközés](css-class-collision.md) — osztálynév névtérrel (`ref-*`), rövid, generikus nem: egy stíluslap van
- [embed() és charset](page-embed-escaping.md) — ami a lapra kerül, `embed()`-en át (`</` → `<\/`, U+2028/29); `<meta charset="utf-8">` az első sor
- [Gráf a sorok mögött](graph-rows-layout.md) — `drawGraph()` minden DOM-változás után; sor-kiemelés csak a `.row-in`-re
- [Modulok blob-URL-en](page-modules-blob-linking.md) — nincs körkörös, dinamikus import; sor eleji `import … from './x.js'`; export csak olvasható, setterrel; `LOADER_API`; a betöltő a `body`-t nem írja felül
- [Az Artifact nem tárol adatot](artifact-holds-no-data.md) — adatot, kódot ne tegyél vissza a lapba: csak a betöltő
- [Sticky és overflow](sticky-header-overflow.md) — köztes `overflow` elrontja a ragadós fejlécet; egy görgető régió
- [Görgetés commitonként](scroll-step-rows.md) — scroll-snap és animáció elvetve; a `coasting` a lendületre
- [A lap nyelve](page-language-os-locale.md) — `navigator.language` = OS; az app nyelve a `config.json`-ból, a szerveren
- [Mermaid-build](mermaid-build.md) — blobból fut a CSP alatt; karcsú build csonkokkal, ELK-kal, a hídhatár alatt

## Git és Python

- [--no-optional-locks](git-no-optional-locks.md) — minden git-hívás olvas és `--no-optional-locks`; `core.fsmonitor` nem használható
- [Git-pollozás költsége](git-poll-cost.md) — a git a `git_bin`-nel fut, nem a `/usr/bin/git` shimmel; worktree-nkénti WIP mérve
- [Python-futtatás korlátai](python-runtime-constraints.md) — 3.9 (`/usr/bin/python3`); függvényen belüli import nem; `set_repo` / `gitio.REPO`
- [Repónév a remote-ból](repo-name-from-remote.md) — repónév az `origin`-ből, nem a mappanévből; minden út a fő checkoutra (`main_checkout`)
- [WIP-sorok a lane-ek előtt](wip-rows-before-lanes.md) — `*uncommitted:` / `*staged:` a lane-kiosztás ELŐTT; a `meta` a valódi commitokból
- [Stash egy sor](stash-single-row.md) — `log --all` helyett `ALL_BUT_STASH`; stash a `git stash list`-ből, egy szülővel (`^1`)
- [file_diff bemenete](file-diff-input-safety.md) — a `sha` csak hex; fájlt közvetlenül csak követetlen esetben olvasunk
- [Ág-távolság origin/HEAD-hez](branch-base-origin-head.md) — a reflog forrás-ága szándékosan nem; gazda a HEAD-reflogból

## MCP és host-híd

- [MCP stdout](mcp-stdout-protocol.md) — stdout-on csak ASCII JSON-RPC, napló stderr-re
- [Host-híd korlátai](host-bridge-limits.md) — csak a `claude_desktop_config.json` szervere, beírás után app-újraindítás; minden tool `readOnlyHint: true`; csak az appban
- [Új tool: tools/list_changed](tools-list-changed.md) — új tool → `PUBLISH_CAPS` + új betöltő; `restart` után `notifications/tools/list_changed`
- [Nyitott hívás a hídon](host-bridge-long-poll.md) — a `changes` long-poll: sűrű kérdezés tilos (~20 gyors hívás után visszafog); a `signal` nem jut át
- [Saját worktree: fókusz](focused-worktree-design.md) — az előtérben lévő sessioné (`focused_worktree`), kézzel nem választható
- [Rejtett keret](host-bridge-hidden-frame.md) — rejtve `server_unavailable`, az időzítők állnak; megjelenéskor újrapróba
- [Host-híd válaszmérete](host-bridge-response-size.md) — a határ ~4 000 000 karakter; képlimit ezért ~2,95 MB oldalanként
- [Egy Artifact = egy keret](artifact-single-frame.md) — minden sessionben ugyanaz; `#horgony`, `?query` eldobva; republish újratölt
- [Előtérben lévő session forrásai](app-focus-sources.md) — session-JSON `lastFocusedAt`, `main.log` `setFocusedSession`; nincs hook
- [git-worktrees.json](app-worktrees-json.md) — a leválasztott HEAD-ű worktree ága az app nyilvántartásában
- [MCP-alakok a lapon](mcp-wire-format.md) — `listTools()` `{servers}`-t ad, az eredmény a `payload`; GUI-ból minimális PATH
- [Artifact CSP](artifact-csp.md) — külső fetch tilos; eval, blob-script, `import(blob:)`, CDN-script fut; `data:` nem
- [Artifact capability-k](artifact-capabilities.md) — mi él a fiókon; „AI-powered artifacts” kapcsoló; a `sample` nem a session
- [sendToClaude a lapról](comments-send-to-claude.md) — a lapot mutató sessionnek megy; egyszeri hozzájárulás

## Plugin, telepítés, publikálás

- [Stabil másolat, telepítés](stable-copy-install.md) — nincs install-esemény, a SessionStart hook telepít; stabil zip; csere: lap → zip → manifest; bump nélkül a `plugin update` nem hoz le semmit
- [Önfrissítő szerver](server-self-update.md) — a futó szerver frissít és szerel le (`watch_plugin`); puffereletlen stdin
- [A hook publikáltat, a mod nyit](hook-publishes-mod-opens.md) — `publish_steps` a hookból, `--open-url` a modból; modból `publish` nem megy
- [Publikálás a sessionből](publish-from-session.md) — meglévőre csak `Artifact read` után; a lépésekben `git-graph`, nem abszolút út
- [Mod korlátai](mod-limits.md) — modból `open`, `read` megy, `publish` nem (auto mód); `classic.*` nem jön; panel nem DOM
- [Artifact megnyitása](artifact-open-paths.md) — nyitott lapra az `open` csak kártya; `show_pane` nyit; külső folyamat nem
- [Headless publikálás (kivezetve)](headless-publish-retired.md) — `claude -p` buktatói és idői, ha mégis kellene
- [Fejlesztés forrásból](dev-from-source.md) — `--dev-install`, `CLAUDE_CODE_PLUGIN_DIRS`, kézi próba kamu `HOME`-mal
