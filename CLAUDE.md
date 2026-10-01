# git-graph

Git Graph-szerű commit-gráf **bármelyik repóból**: önálló HTML pillanatkép, élő
Browser panel nézet, és élő Artifact, amely a Claude appban a gépen futó
`gg --mcp`-ből olvas. A VS Code `mhutchie.git-graph` elrendezését követi.

Használat és felépítés: [README.md](README.md).

## Repó térkép

| Útvonal | Mi ez |
| --- | --- |
| `bin/git-graph` | a teljes eszköz egyetlen fájlban: git-adatgyűjtés + HTML/CSS/JS sablon (3 mód: `static`, `http`, `mcp`) + élő szerver (`--serve`) + MCP szerver a Claude appnak (`--mcp`) + headless Artifact-publikálás (`--publish`) + SessionStart hook (`--session-hook`), benne a plugin gépi telepítése és leszerelése |
| `bin/gg` | symlink a `git-graph`-ra (rövid alias) |
| `bin/ggl` | ugyanaz a script; a `sys.argv[0]` neve kapcsolja a `--launch-config`-ot |
| `.claude-plugin/plugin.json` | Claude Code plugin manifest — a verzió egyetlen forrása |
| `.claude-plugin/marketplace.json` | a `git-graph` marketplace: egyetlen plugin, `source: "./"` |
| `hooks/hooks.json` | a plugin SessionStart hookja (`--session-hook`) |
| `skills/git-graph/SKILL.md` | a `/git-graph:git-graph` skill (`gg --publish`, majd megnyitja) |
| `docs/artifact-findings.md` | **mérési napló**: mit tud és mit nem az Artifact platform |
| `docs/desktop-live.md` | **mérési napló**: miért a Browser panel + lokális szerver az élő út |
| `docs/mcp-plan.md` | a korábbi terv az élő Artifacthoz (azóta a `host:` híddal megvalósult) |
| `probe/` | eldobható MCP-mérőeszköz a `host:` híd újratesztelésére |

## Parancsok

```sh
claude plugin install git-graph@git-graph   # a hook az első sessionben telepít mindent
claude --plugin-dir .                      # fejlesztés: a working tree pluginként, bump nélkül
claude plugin validate . --strict          # manifestek, skill, hook
gg --help             # a teljes súgó
gg                    # az aktuális repó → ~/.git-graph/<slug>/index.html (pillanatkép)
gg --publish          # az Artifact vékony lapja (headless claude -p)
gg --serve            # élő kiszolgálás a Browser panelnek + Artifactok karbantartása
gg --mcp              # MCP szerver stdio-n — a Claude app indítja, nem kézzel
gg --launch-config    # .claude/launch.json bejegyzés (preview_start git-graph)
ggl                   # ugyanaz — a hívás neve kapcsolja
python3 bin/git-graph …    # közvetlenül, a working tree-ből
```

Három mód, egy sablon (`build(..., mode=…)`): `static` — beágyazott
pillanatkép; `http` — a `gg --serve` élő lapja; `mcp` — az Artifact vékony lapja
(üres váz, az adatot a Claude app host-hídján át a `gg --mcp`-ből kéri). A két
élő mód ugyanazt a pollozót futtatja (`startLive`), csak a forrás más.

Nincs teszt-suite és nincs build — egyfájlos stdlib script. Változtatás után az
ellenőrzés: `gg` futtatása több repón (eltérő sávszámmal, merge-ekkel), és a
generált HTML megnyitása. A JS-t a fájlból kivágva `node --check`-kel lehet
szintaxis-ellenőrizni. Az élő mód ellenőrzése: `gg --serve`, majd a lapon
`DATA.meta.dirty` figyelése egy fájl létrehozása után (újratöltés nélkül kell
változnia), és repóváltás a `~/.git-graph/current` átírásával. Az MCP-é: a
`gg --mcp`-t stdio-n kézfogással, `tools/list`-tel és a toolok hívásával
(`/usr/bin/python3`-mal, ahogy az app indítja). Az MCP-mód lapja a Browser
panelen egy `srcdoc` iframe-ben próbálható: a szerver lapját `MODE='mcp'`-re
írva, egy ál-`window.claude`-dal, amely a `/fingerprint`-ből és a `/data`-ból
válaszol. A publikálásé: `gg --publish` kétszer (a második „naprakész”). A
launchd más környezet, mint egy Desktop session shellje — ami onnan működik,
azt launchd alatt is ki kell próbálni. A telepítésé (`ensure_installed`,
`uninstall`): kamu `HOME`-mal, a modult betöltve, a `launchctl` függvényt
rögzítőre cserélve — a valódi agenthez ne nyúljon a próba, a label közös.

- **Check**: `syntax=/usr/bin/python3 -m py_compile bin/git-graph && claude plugin validate . --strict` · `js=sed -n '/^<script>$/,/^<\/script>$/{//!p;}' bin/git-graph | node --check -`

## Konvenciók

- **Nyelv**: magyar — kommentek, doksi, commit-body, a generált UI feliratai.
  A táblázat-fejlécek (`Description / Date / Author / Commit`) viszont
  **angolul** maradnak: az a Git Graph felismerhető arca. A Graph oszlop
  fejléce ikon (a felirat feleslegesen szélesre nyomta az oszlopot).
- **Függőség**: kizárólag Python 3 stdlib. Ez szándékos — az eszköznek bárhol
  futnia kell, `pip install` nélkül. Ne hozz be libet. A publikáláshoz a
  `claude` CLI kell (külső program, `claude_bin()` keresi a launchd PATH-ján
  kívül is); nélküle minden más működik.
- **Minden git-hívás olvas.** A script sosem módosít repót. Kivétel a
  `.git/info/exclude` és a `.git/config` `git-graph.*` kulcsai — mindkettő lokális,
  sosem commitolódik —, valamint a `--launch-config`, ami
  `.claude/launch.json`-t ír: az **commitolható** fájl, ezért csak kifejezett
  kérésre fut, sosem mellékhatásként.
- **Verziókezelés**: SemVer, a verzió egyetlen forrása a
  `.claude-plugin/plugin.json` (a `marketplace.json` nem ismétli); kézi
  `vX.Y.Z` tag, Conventional Commits.
- **Env**: a toolnak nincs env-függősége, ezért nincs `.env.example`. Ha a
  tunneles MCP-irány megvalósul (`docs/mcp-plan.md` B változat), a bearer token
  `.env`-be megy.

## Gotchák

- **Osztálynév-ütközés az egyfájlos oldalon**: a `.head` (táblázat-fejléc) egyszer
  már ráült a `badge head` elemre. A badge-variánsok azóta `ref-*` névtérben, a
  fejléc `.thead`. Rövid, generikus osztálynevet ne vezess be.
- **`<meta charset="utf-8">` a generált fájl legelső sora** — enélkül
  `file://`-ról latin-1-ként olvasódik.
- **Repónév az `origin` remote-ból**, nem a mappanévből (a mappa eltérhet:
  `auto-bpm` → `WristBPM`). Ez adja az Artifact címét is.
- **A `file://` megnyitás a Browser panelen `data:` originné válik** — beágyazott
  pillanatkép, magától nem tölt újra, és nem `fetch`-el. Az élő mód ezért
  loopback HTTP, nem fájl.
- **A beágyazott JSON lezárhatja a script blokkot**: egy commit-üzenetben tényleg
  előfordult `</script>` (varazskez repó) → a lap fele nyers JSON-ként ömlött ki.
  A `build()` ezért az `embed()`-en át ágyaz (`</` → `<\/`, U+2028/29 escape).
  Bármi, ami a lapra kerül, ezen menjen át.
- **Nincs `launch.local.json`.** A `.claude/launch.d/` drop-in mappa csak
  framebuffer (VNC) forrásokra megy — mérve: az oda tett preview-bejegyzést a
  `preview_start` nem találja, a `launch.json`-ra esik vissza. Gépfüggő
  bejegyzést ezért `.git/info/exclude`-dal tartunk lokálisan.
- **A launch.json localhostra csak origint fogad el** (mérve: *„a localhost
  address with a path or query"*), ezért a `--launch-config` a repót a
  hostnévbe teszi: `<slug>.localhost`. A Chromium minden `*.localhost` nevet a
  loopbackra old fel; a szerver a `Host` fejlécből és a
  `~/.git-graph/repos.json` regiszterből azonosítja a repót.
- **A repó a kérés URL-jében van** (`/?repo=…`), nem globális állapotban: több
  session panelje egyszerre kérdezi ugyanazt a szervert, és egy közös „aktuális
  repó" véletlenszerűen váltogatna. A `~/.git-graph/current` csak tartalék.
- **A `drawGraph()` a DOM-ból olvassa a sorok Y-pozícióját** (`offsetTop`), nem
  sorszám × magasságból: kinyitott commit-panelnél az alatta lévő sorok
  lejjebb csúsznak. Ezért minden DOM-változás után újra kell hívni (nyitás,
  zárás, Escape, `render`). A panel `margin-left: var(--graph-w)` — a gráf-oszlop
  szabadon marad, a vonal mellette fut végig.
- **A sor-kiemelés nem mehet a gráf-oszlopra**: a pöttyöket az `#lanes` SVG
  rajzolja a sorok MÖGÉ, az átlátszatlan `:hover` / kiválasztott háttér pedig
  eltakarta őket. Ezért a háttér a cellákra megy, az elsőt kihagyva
  (`.cell ~ .cell`). Az SVG-t a sorok fölé emelni nem megoldás: a `.rows`
  (`z-index: 2`) saját rétegkontextust nyit, így a benne lévő `.details` sosem
  kerülhet a testvér `#lanes` fölé — a kinyitott panelen átlógnának a vonalak.
- **Az `Uncommitted Changes` ál-sor a `commits` lista 0. eleme** (`sha`:
  `*uncommitted`), a szülője a HEAD. Az `assign_lanes` magától kezeli, de az
  `edges` **sorindexeket** használ — ezért az ál-sort a lane-kiosztás ELŐTT kell
  beszúrni, a `meta` viszont még a valódi commitokból készül (különben a
  „N commit látszik" hazudna).
- **Minden git-hívás `--no-optional-locks`**: a `git status` egyébként frissíti
  az indexet, ahhoz `index.lock`-ot vesz, és a 2 mp-es pollozás így a Fejlesztő
  saját git-parancsait akasztja meg (egy commit tényleg elhasalt rajta).
- **A `REPO` modulszintű globális**, a szerver viszont kérésenként más repót
  szolgálhat ki: a kiszolgálás ezért **sorosított** (lock), és a `_REMOTES`
  cache-t minden váltásnál nullázni kell.
- **A launchd agent `/usr/bin/python3`-mal fut** (minimális PATH, a homebrew-s
  Python eltűnhet egy frissítéssel) — a script maradjon 3.9-kompatibilis.
- **A hook az Artifactot nyittatja meg** (`git-graph.artifact`), ha van; ha
  nincs, a Browser panelt (dev szerver). Némán kilép, ha a mappa nem repó, vagy
  se Artifact, se futó szerver: egy SessionStart hook minden sessionben lefut,
  zajt nem csinálhat.
- **A kimenet a repón KÍVÜL, `~/.git-graph/<slug>/`**: `index.html` a `gg`
  pillanatképe, `artifact.html` az Artifact vékony lapja — a headless claude ezt
  a mappát kapja munkakönyvtárnak (az Artifact csak onnan olvas). Ne tedd
  konfigurálhatóvá. A projektmappába nem írunk.
- **Az Artifact nem tárol adatot** — ez a lényeg, nem optimalizálás. Egy
  beágyazott adatú lap frissítése nagy repón ~50 s volt (a feltöltő modell az
  élő és a helyi példányt is végigolvassa); a vékony lapot csak sablon- vagy
  repónév-változáskor kell feltölteni (~6 s). Adatot ne tegyél vissza a lapba.
- **Host-híd (`host:git-graph`)** — mérve, docs/artifact-findings.md:
  - Csak a Claude app configjában (`claude_desktop_config.json`) felvett szerver
    érhető el; a `claude mcp add`-os nem. Az app csak induláskor olvassa, és
    **futás közben felülírja** a memóriabeli változattal (beállítás-mentéskor —
    mérve: a bejegyzés eltűnt). Ezért a beírás után azonnal újraindítás.
  - A lapnak deklarálnia kell a `mcp` capability-t (`PUBLISH_CAPS`) — enélkül a
    `use("mcp")` `null`, és a lap azt hiszi, nem az appban fut. A headless
    publikáló csak akkor deklarálhatja a `host:git-graph`-ot, ha maga is látja a
    szervert: ezért kapja `--mcp-config`-gal. A deklaráció a hash része.
  - A `gg --mcp` stdout-ján csak JSON-RPC mehet, ASCII-ban (a locale-tól
    függetlenül); napló, ha kell, stderr-re.
  - A toolok `readOnlyHint: true`-k — enélkül az app hívásonként megerősítést
    kérhet. A `watchTool` pollozása ≥ ~30 s, ezért a lap `callTool`-lal kérdez
    2 s-onként (olcsó `fingerprint`, változáskor `graph_data`).
  - Csak az appban megy (böngészőben `server_not_connected`), csak a
    tulajdonosnak. A lap nem `retryable` hibánál leáll, és kiírja a teendőt.
  - Új tool → a `PUBLISH_CAPS` tool-listájába is (különben `not_in_manifest`),
    és az app újraindítása: az app által indított `gg --mcp` a régi kódot futtatja.
- **A `file_diff` / `/diff` bemenete a lapról jön**: a `sha` csak hex lehet
  (különben `--output=…`-szerű opcióként menne a gitnek), fájlt közvetlenül
  csak akkor olvasunk, ha a git követetlennek mondja — a loopback szerveren át
  ne legyen kiolvasható tetszőleges fájl.
- **Headless Artifact (`publish_page`)** — mind mérve, docs/artifact-findings.md:
  - `-p` módban az Artifact tool alapból KI (`sdk_default_off`); az opt-in a
    `CLAUDE_CODE_ARTIFACT=1`. Desktop sessionből indítva nélküle is ment (a
    `CLAUDE_CODE_ENTRYPOINT=claude-desktop` öröklődik) — launchd alatt nem.
  - Az Artifact egy org-policy lekérdezés után kapcsol be, gyakran az első
    init UTÁN. Ezért `--input-format stream-json`: hiányzó toolnál interrupt +
    újrakérdezés UGYANABBAN a folyamatban (új folyamat újra zárt kapuval indul).
  - Friss sessionből a publish csak `Artifact read` után megy át.
  - Karcsú indulás: `--strict-mcp-config` + `ENABLE_CLAUDEAI_MCP_SERVERS=false`
    + `--setting-sources project` (a `--tools` szűkítés MCP-vel együtt rossz:
    `ToolSearch` nélkül minden MCP-séma betöltődik).
- **A publikálás a lock NÉLKÜL fut**: a `REPO`-váltás és a git-hívások lockban,
  a claude-folyamat kívül — különben addig a lap sem szolgálna ki.
- **A `launchctl bootout` aszinkron** — a közvetlenül utána jövő
  `bootstrap` „5: Input/output error”-ral bukott, ezért próbálkozik újra.
- **Plugin: nincs install/update/uninstall esemény** (docs). Ezért:
  - A gépi részt a SessionStart hook állítja be (`ensure_installed`), csak ha a
    script a `CLAUDE_PLUGIN_ROOT` alatt fut — egy kézi `--session-hook` nem
    telepít. Minden lépés idempotens, csak változáskor ír; a hook stdout-ja a
    hook-JSON-é, napló csak stderr-re (`log`).
  - A `CLAUDE_PLUGIN_ROOT` verziónként más (`…/cache/git-graph/git-graph/<verzió>/`),
    ezért a launchd és az app a **stabil másolatot** futtatja
    (`~/.git-graph/bin/git-graph`) — symlinket nem, mert a régi verzió mappája
    eltűnhet. Változott másolatnál az agent `kickstart -k`-val újraindul.
  - A leszerelést a `--serve` szála végzi (`watch_uninstall`): az
    `installed_plugins.json`-ban (Claude Code belső fájl, `version: 2`) keresi a
    `git-graph@…` kulcsot. Ismeretlen formátumnál nem dönt, és csak két
    egymást követő hiány után szerel le (frissítés közbeni pillanat). Csak a
    stabil példányban fut — a fejlesztői `gg --serve` nem szerel le.
  - A `bin/` csak a Claude **Bash eszközének** PATH-ja, a hooké és a terminálé
    nem: a hook a `${CLAUDE_PLUGIN_ROOT}/bin/git-graph`-ot hívja, a terminál a
    `~/.local/bin` linkjeit használja.
  - Bump nélkül a `claude plugin update` nem hoz le semmit (a `plugin.json`
    `version`-je dönt).

Részletes platform-tanulságok (CSP, capabilities, MCP): `docs/artifact-findings.md`.
