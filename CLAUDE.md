# git-graph

Git Graph-szerű commit-gráf **bármelyik repóból**: élő Artifact, amely a
Claude appban a gépen futó `gg --mcp`-ből olvas. A VS Code `mhutchie.git-graph` elrendezését követi.

Használat és felépítés: [README.md](README.md).

## Repó térkép

| Útvonal | Mi ez |
| --- | --- |
| `bin/git-graph` | a teljes eszköz egyetlen fájlban: git-adatgyűjtés + HTML/CSS/JS sablon (az Artifact vékony lapja) + MCP szerver a Claude appnak (`--mcp`, benne a leszerelés figyelése) + a publikálás lépései a sessionnek (`--publish`, `--published`) + SessionStart hook (`--session-hook`), benne a plugin gépi telepítése |
| `bin/gg` | symlink a `git-graph`-ra (rövid alias) |
| `.claude-plugin/plugin.json` | Claude Code plugin manifest — a verzió egyetlen forrása |
| `.claude-plugin/marketplace.json` | a `git-graph` marketplace: egyetlen plugin, `source: "./"` |
| `hooks/hooks.json` | a plugin hookja (`--session-hook`): SessionStart, és PostToolUse az `EnterWorktree` / `ExitWorktree` után |
| `skills/git-graph/SKILL.md` | a `/git-graph:git-graph` skill (`gg --publish`, és publikálja vagy megnyitja) |
| `skills/remove/SKILL.md` | a `/git-graph:remove` skill: Artifactok törlése + `gg --forget` az uninstall előtt |
| `docs/artifact-findings.md` | **mérési napló**: mit tud és mit nem az Artifact platform |
| `docs/desktop-live.md` | **mérési napló** (történeti): a kivezetett Browser panel-út |
| `docs/mcp-plan.md` | a korábbi terv az élő Artifacthoz (azóta a `host:` híddal megvalósult) |
| `probe/` | eldobható MCP-mérőeszköz a `host:` híd újratesztelésére |

## Parancsok

```sh
claude plugin install git-graph@git-graph   # a hook az első sessionben telepít mindent
claude --plugin-dir .                      # fejlesztés: a working tree pluginként, bump nélkül
claude plugin validate . --strict          # manifestek, skill, hook
gg --help             # a teljes súgó
gg --publish          # az Artifact vékony lapja + a publikálás lépései a sessionnek
gg --published <URL>  # a session publikálása után: URL + hash a .git/config-ba
gg --mcp              # MCP szerver stdio-n — a Claude app indítja, nem kézzel
gg --artifacts        # ismert repók Artifactjai (regiszter + a szülőmappák repói)
gg --forget           # a repó git-graph nyomai + automatikus publikálás KI
gg --forget-artifact <URL>   # egyetlen Artifact nyomai (megszűnt worktree)
python3 bin/git-graph …    # közvetlenül, a working tree-ből
```

Egy sablon (`build()`): az Artifact vékony lapja — üres váz, az adatot a
Claude app host-hídján át a `gg --mcp`-ből kéri, a `startLive` pollozójával.
A `gg` a Claude Bash eszközének parancsa (a plugin `bin/`-je), terminálos
link és pillanatkép nincs; parancs nélkül a súgót írja ki.

Nincs teszt-suite és nincs build — egyfájlos stdlib script. Változtatás után az
ellenőrzés: a `gg --mcp` `graph_data`-ja több repón (eltérő sávszámmal,
merge-ekkel), és a lap az appban. A JS-t a fájlból kivágva `node --check`-kel lehet
szintaxis-ellenőrizni. Az MCP-é: a `gg --mcp`-t stdio-n kézfogással,
`tools/list`-tel és a toolok hívásával (`/usr/bin/python3`-mal, ahogy az app
indítja). Az élő lapé: a sessionből publikálva, a Claude appban megnyitva (az
app MCP-naplója a host-híd hívásait nem mutatja — a lapot kell nézni). A hooké
és a publikálásé: `--session-hook` kamu `HOME`-mal, `CLAUDE_PLUGIN_ROOT`-tal
és `CLAUDE_CODE_ENTRYPOINT`-tal, eldobható klónon (a `--published` a
`.git/config`-ba ír); a hook kimenete a publikálás lépéseit vagy a megnyitást
kéri. A telepítésé (`ensure_installed`, `uninstall`, `watch_uninstall`): kamu
`HOME`-mal, a modult betöltve, a `launchctl`-t rögzítőre cserélve — a régi
agent labelje közös a valódival, ahhoz a próba ne nyúljon.

- **Check**: `syntax=/usr/bin/python3 -m py_compile bin/git-graph && claude plugin validate . --strict` · `js=sed -n '/^<script>$/,/^<\/script>$/{//!p;}' bin/git-graph | node --check -`

## Konvenciók

- **Nyelv**: magyar — kommentek, doksi, commit-body, a generált UI feliratai.
  A táblázat-fejlécek (`Description / Date / Author / Commit`) viszont
  **angolul** maradnak: az a Git Graph felismerhető arca. A Graph oszlop
  fejléce ikon (a felirat feleslegesen szélesre nyomta az oszlopot).
- **Függőség**: kizárólag Python 3 stdlib. Ez szándékos — az eszköznek bárhol
  futnia kell, `pip install` nélkül. Ne hozz be libet.
- **Minden git-hívás olvas.** A script sosem módosít repót. Kivétel a
  `.git/config` `git-graph.*` kulcsai — lokális, sosem commitolódik.
- **Verziókezelés**: SemVer, a verzió egyetlen forrása a
  `.claude-plugin/plugin.json` (a `marketplace.json` nem ismétli); kézi
  `vX.Y.Z` tag, Conventional Commits. A bump a feature-commitban történik,
  a `/release` a `plugin.json` verzióját tageli (a `git cliff` számítását nem).
- **Deploy**: a marketplace forrása a repó `main`-je, tehát a merge már
  élesít; a `/release` deploy-lépése a helyi frissítés:
  `claude plugin marketplace update git-graph && claude plugin update git-graph@git-graph`.
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
  `auto-bpm` → `WristBPM`). Ez adja az Artifact címét is; worktree-ben a
  mappa neve is mellé kerül (`Git Graph (git-graph · <mappa>)`). A cím a
  publikált `<title>`-ből jön, a lap JS-e nem írja felül.
- **A beágyazott JSON lezárhatja a script blokkot**: egy commit-üzenetben tényleg
  előfordult `</script>` (varazskez repó) → a lap fele nyers JSON-ként ömlött ki.
  A `build()` ezért az `embed()`-en át ágyaz (`</` → `<\/`, U+2028/29 escape).
  Bármi, ami a lapra kerül, ezen menjen át.
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
- **A `REPO` modulszintű globális**, a `gg --mcp` viszont hívásonként más repót
  szolgálhat ki (a lap slugja szerint): a `_REMOTES` cache-t minden váltásnál
  nullázni kell. A stdio-kiszolgálás soros, lock nem kell.
- **Az app a `gg --mcp`-t `/usr/bin/python3`-mal indítja** (a homebrew-s
  Python eltűnhet egy frissítéssel) — a script maradjon 3.9-kompatibilis.
- **A hook publikáltat vagy megnyittat.** Ha a repónak nincs Artifactja, vagy a
  lap hashe eltér a `git-graph.artifactHash`-től, a publikálás lépéseit adja a
  sessionnek (`publish_steps`); különben a meglévőt nyittatja meg. Headless
  (`CLAUDE_CODE_ENTRYPOINT=sdk-*`) sessionben és `no-auto-publish` mellett nem
  kér publikálást. Némán kilép, ha a mappa nem repó: egy SessionStart hook
  minden sessionben lefut, zajt nem csinálhat. A repót mindig regisztrálja — a
  `gg --mcp` a lap slugjából a `repos.json`-ból találja meg.
- **Worktree-nként saját Artifact, közös `.git/config`-ban**: a fő checkout
  kulcsai `git-graph.*`, egy worktree-é `git-graph.<slug>.*` (`config_section`)
  — közös kulcson a worktree-k egymás lapját publikálnák felül, oda-vissza.
  `extensions.worktreeConfig`-ot szándékosan nem kapcsolunk be (a repó
  beállítása lenne). A megszűnt worktree szakaszát a hook ismeri fel
  (`orphan_artifacts`: nincs a `git worktree list`-ben), és törölteti az
  Artifactot, majd `--forget-artifact` — a `/worktree-close` erről nem tud.
  Az `EnterWorktree` session közben történik, ezért a hook PostToolUse-ként
  is fut: a `cwd` ilyenkor már az új munkakönyvtár (docs).
- **A kimenet a repón KÍVÜL, `~/.git-graph/<slug>/`**: `artifact.html` az
  Artifact vékony lapja — innen publikál a session. Ne tedd konfigurálhatóvá. A projektmappába nem írunk.
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
    `use("mcp")` `null`, és a lap azt hiszi, nem az appban fut. A deklaráció
    a session szervere nélkül is átmegy (csak figyelmeztet), és a hash része.
  - A `gg --mcp` stdout-ján csak JSON-RPC mehet, ASCII-ban (a locale-tól
    függetlenül); napló, ha kell, stderr-re.
  - A toolok `readOnlyHint: true`-k — enélkül az app hívásonként megerősítést
    kérhet. A `watchTool` pollozása ≥ ~30 s, ezért a lap `callTool`-lal kérdez
    2 s-onként (olcsó `fingerprint`, változáskor `graph_data`).
  - Csak az appban megy (böngészőben `server_not_connected`), csak a
    tulajdonosnak. A lap nem `retryable` hibánál leáll, és kiírja a teendőt.
  - Új tool → a `PUBLISH_CAPS` tool-listájába is (különben `not_in_manifest`),
    és az app újraindítása: az app által indított `gg --mcp` a régi kódot futtatja.
- **A `file_diff` bemenete a lapról jön**: a `sha` csak hex lehet
  (különben `--output=…`-szerű opcióként menne a gitnek), fájlt közvetlenül
  csak akkor olvasunk, ha a git követetlennek mondja — a lapon át ne legyen
  kiolvasható tetszőleges fájl.
- **Publikálás a sessionből** — mérve, docs/artifact-findings.md:
  - Az Artifact API-t csak a modell éri el, ezért a session publikál, a hook
    (`publish_steps`) vagy a `gg --publish` lépései szerint; a hook az
    eredményt nem látja, ezért a `gg --published <URL>` írja vissza az URL-t és
    a hasht (az `artifact.html`-ből számolva).
  - Friss sessionből meglévő Artifactra a publish csak `Artifact read` után megy
    át (az elutasítás maga is olvasásnak számít).
  - A lépésekben `gg` áll, nem abszolút út: a plugin `bin/`-je a Bash PATH-ján
    van, és egy `Bash(gg:*)` engedély lefedi.
- **Plugin: nincs install/update/uninstall esemény** (docs). Ezért:
  - A gépi részt a SessionStart hook állítja be (`ensure_installed`), csak ha a
    script a `CLAUDE_PLUGIN_ROOT` alatt fut — egy kézi `--session-hook` nem
    telepít. Minden lépés idempotens, csak változáskor ír; a hook stdout-ja a
    hook-JSON-é, napló csak stderr-re (`log`).
  - A `CLAUDE_PLUGIN_ROOT` verziónként más (`…/cache/git-graph/git-graph/<verzió>/`),
    ezért az app a **stabil másolatot** futtatja
    (`~/.git-graph/bin/git-graph`) — symlinket nem, mert a régi verzió mappája
    eltűnhet. Új kód az app újraindításával él (a futó `gg --mcp` a régit futtatja).
  - A leszerelést a `gg --mcp` szála végzi (`watch_uninstall`): az
    `installed_plugins.json`-ban (Claude Code belső fájl, `version: 2`) keresi a
    `git-graph@…` kulcsot. Ismeretlen formátumnál nem dönt, és csak két
    egymást követő hiány után szerel le (frissítés közbeni pillanat). Csak a
    stabil példányban fut — a working tree-ből indított `gg --mcp` nem szerel
    le. Több példány fut (az app és minden Code-session indít egyet), a
    leszerelés idempotens. Ha az app nem fut, a következő indulásáig vár.
  - A `bin/` csak a Claude **Bash eszközének** PATH-ja, a hooké nem: a hook a
    `${CLAUDE_PLUGIN_ROOT}/bin/git-graph`-ot hívja. Terminálos parancs nincs.
  - Bump nélkül a `claude plugin update` nem hoz le semmit (a `plugin.json`
    `version`-je dönt).

Részletes platform-tanulságok (CSP, capabilities, MCP): `docs/artifact-findings.md`.
