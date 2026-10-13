# git-graph — felépítés és gotchák részletesen

A `.claude/CLAUDE.md` rövid szabályainak indoklása és a mért háttér. A platform
mérései: [artifact-findings.md](artifact-findings.md).

## Fejlesztés és ellenőrzés

Az Artifact csak egy betöltő (`page/loader.html`, `build()`): a lap kódját
(`page/head.html`, `page.css`, `body.html`, `js/*.js`) a `page_code` toollal, az adatot a
`graph_data`-val kéri a Claude app host-hídján át a `git-graph --mcp`-ből, a
`startLive` pollozójával. Kódváltozás így újrapublikálás nélkül él: a
`claude plugin update` után a futó szerver percen belül frissíti magát, a lap
pedig újratölt.
A `git-graph` a Claude Bash eszközének parancsa (a plugin `bin/`-je), terminálos
link és pillanatkép nincs; parancs nélkül a súgót írja ki.

Nincs build — stdlib csomag és statikus lapfájlok (a stabil másolat zipjét a
telepítés rakja össze, a lap moduljait a `page_code` köti össze). A **Check** a lap
moduljait Node-ban összeköti (`scripts/check-page.mjs`), lintel (ruff, Biome), típusellenőriz
(`tsc --checkJs`, `page/tsconfig.json`; a `graph_data` és a betöltő kontextusának alakja a
`page/js/types.d.ts`-ben, nem szigorú módban), és lefuttatja a
teszteket (`/usr/bin/python3`-mal, ahogy az app indítja): modulonként, és a
füsttesztet — az MCP-t stdio-n kézfogással, `tools/list`-tel és a toolok
hívásával, a stabil másolatból is. A hook, a publikálás és a telepítés is
tesztelt, kamu `HOME`-mal. A lintereket a `uvx` / `pnpm dlx` hozza, a repóba nem kerül
függőség. Ezen túl kézzel: a `git-graph --mcp` `graph_data`-ja több repón
(eltérő sávszámmal, merge-ekkel), és a lap az appban. Az élő lapé: `python3 bin/git-graph --dev-install`. Ez a working treet az
appban futó szerver helyére teszi `+dev` verzióval; a szerver 15 s-on belül
átvált, a lap újratölt, és az app minden git-graph lapja az új kódot mutatja.
A hook 12 óráig nem másolja vissza a telepítettet (`dev_active`).
**Forrásból futó plugin** (ezen a gépen: `~/.claude/settings.json` →
`env.CLAUDE_CODE_PLUGIN_DIRS` végén `:…/git-graph`, a `git-graph@git-graph`
disabled, de telepítve marad — a leszerelés a nyilvántartás kulcsát nézi): a
skillek és a mod a working tree-ből jönnek (skillhez `/reload-plugins`), a hook
pedig minden session indulásakor `<verzió>+dev.src.<hash>` verzióval telepít
(`source_digest`) — a szerver csak kódváltozásra indul újra, a `pull_update` nem
másol vissza. A `CLAUDE_PLUGIN_ROOT` a `~/.claude/plugins/cache` alatt =
telepített, máshol = forrás. A válaszban írd ki a verziót (`<verzió>+dev.<időbélyeg>`) — a lap láblécén ebből látszik, hogy már az
új állapot fut.
Utána a sessionből publikált lapot kell nézni a Claude appban (az app MCP-naplója a host-híd hívásait nem mutatja). A hooké
és a publikálásé: `--session-hook` kamu `HOME`-mal, `CLAUDE_PLUGIN_ROOT`-tal
és `CLAUDE_CODE_ENTRYPOINT`-tal, eldobható klónon (a `--published` a
`.git/config`-ba ír); a hook kimenete a publikálás lépéseit vagy a megnyitást
kéri. A telepítésé (`ensure_installed`, `uninstall`, `watch_plugin`): kamu
`HOME`-mal, a modult betöltve — az app configja és a `~/.git-graph` is a
`HOME` alól jön, a valódihoz így a próba nem nyúl.

## Gotchák

- **Osztálynév-ütközés a lap egyetlen stíluslapján**: a `.head` (az egykori
  táblázat-fejléc) egyszer már ráült a `badge head` elemre. A badge-variánsok
  azóta `ref-*` névtérben vannak. Rövid, generikus osztálynevet ne vezess be.
- **`<meta charset="utf-8">` a generált fájl legelső sora** — enélkül
  `file://`-ról latin-1-ként olvasódik.
- **Repónév az `origin` remote-ból**, nem a mappanévből (a mappa eltérhet:
  `auto-bpm` → `WristBPM`). Ez adja az Artifact címét is (`Git Graph (<repó>)`).
  A cím a publikált `<title>`-ből jön, a lap JS-e nem írja felül.
- **A beágyazott JSON lezárhatja a script blokkot**: egy commit-üzenetben tényleg
  előfordult `</script>` (varazskez repó) → a lap fele nyers JSON-ként ömlött ki.
  A `build()` ezért az `embed()`-en át ágyaz (`</` → `<\/`, U+2028/29 escape).
  Bármi, ami a lapra kerül, ezen menjen át.
- **A `drawGraph()` a DOM-ból olvassa a sorok Y-pozícióját** (`offsetTop`), nem
  sorszám × magasságból: a napok fejléce (`.day`) és a kinyitott commit-panel
  az alattuk lévő sorokat lejjebb tolja. A pötty a sor közepére kerül
  (`offsetTop + offsetHeight / 2`): a sor `ROW_H` magas, a kétsoros 52, a tördelt badge-es (`.three`) legalább 71 px, a badge-ek számától függően magasabb. A sor
  elrendezése fix határokkal a szövegoszlop szélességétől függ (`fitRows`:
  480 alatt kétsoros `.two`, a sorban hash nincs, a lista nem szűkül 320
  alá); csak a badge-es sort méri (`.tight`), mert a badge-ek hossza soronként más. Ezért minden DOM-változás után újra kell hívni (nyitás,
  zárás, Escape, `render`). A panel `margin-left: var(--graph-w)` — a gráf-oszlop
  szabadon marad, a vonal mellette fut végig.
- **A sor-kiemelés nem mehet a gráf-oszlopra**: a pöttyöket az `#lanes` SVG
  rajzolja a sorok MÖGÉ, az átlátszatlan `:hover` / kiválasztott háttér pedig
  eltakarta őket. Ezért a sor bal paddingje a gráf szélessége, és a háttér a
  belső sávra (`.row-in`) megy. Az SVG-t a sorok fölé emelni nem megoldás: a `.rows`
  (`z-index: 2`) saját rétegkontextust nyit, így a benne lévő `.details` sosem
  kerülhet a testvér `#lanes` fölé — a kinyitott panelen átlógnának a vonalak.
- **A „Nem commitolt változások” ál-sorok a `commits` lista elején** (worktree-nként
  egy, `sha`: `*uncommitted:<worktree-slug>` — ebből tudja a `file_diff`, melyik
  mappát diffelje; a slugnak élő worktree-é kell lennie), a szülőjük a worktree
  HEAD-je. Az `assign_lanes` magától kezeli, de az `edges` **sorindexeket**
  használ — ezért az ál-sorokat a lane-kiosztás ELŐTT kell beszúrni, a `meta`
  viszont még a valódi commitokból készül (különben a „N commit látszik"
  hazudna). A szerzőjük a worktree `user.name`-je, az idejük a fájlok `mtime`-ja.
  A lapon a saját worktree-é a fix `#pending` sávban ül (a pontja Y-ja a sáv mért
  soraiból jön, `drawPending`, negatív a lista tetejéhez képest); a többié a
  listában, az ideje szerint a commitok közé sorolva, sosem a HEAD-je alá.
- **Minden git-hívás `--no-optional-locks`**: a `git status` egyébként frissíti
  az indexet, ahhoz `index.lock`-ot vesz, és a gyakori állapotlekérés így a Fejlesztő
  saját git-parancsait akasztja meg (egy commit tényleg elhasalt rajta). Ezért
  nem használható a git `core.fsmonitor`-ja sem: csak az indexbe írva gyorsít (mérve, #29).
- **A git a valódi binárisával fut** (`git_bin`, a `git --exec-path` mellől): az
  app szűk PATH-tal indítja a szervert, a macOS `/usr/bin/git` pedig `xcrun`-shim,
  hívásonként ~6 ms-mal lassabb.
- **A `REPO` a `gitio` modulszintű globálisa**, a `git-graph --mcp` viszont hívásonként más repót
  szolgálhat ki (a lap slugja szerint): váltani csak `set_repo`-val (az a `_REMOTES`
  cache-t is nullázza), olvasni `gitio.REPO`-ként — egy `from .gitio import REPO`
  a betöltéskori értéket tartaná meg. A stdio-kiszolgálás soros, lock nem kell.
- **Az app a `git-graph --mcp`-t `/usr/bin/python3`-mal indítja** (a homebrew-s
  Python eltűnhet egy frissítéssel) — a kód maradjon 3.9-kompatibilis.
- **A csomag minden modulja induláskor betöltődik** (a `cli` mindet importálja):
  a stabil zip a futó szerver alatt cserélődhet, egy későbbi import már az új
  zipből olvasna. Függvényen belüli import a csomagból nem lehet.
- **A hook publikáltat, a mod nyit meg.** Ha a repónak nincs Artifactja, vagy a
  lap hashe eltér a `git-graph.artifactHash`-től, a hook a publikálás lépéseit adja a
  sessionnek (`publish_steps`). A meglévőt a plugin modja (`hooks/register.ts`)
  nyitja meg a modell nélkül, a session indulásakor: a `git-graph --open-url` dönt (`open_url`), a mod
  `$.tool.call`-lal hívja az `Artifact` `open`-t — sessionönként
  egyszer: a `~/.git-graph/sessions.json` (`session_id → slug`, 7 nap után
  törlődik) szerint, a `source`-tól függetlenül (`resume`, `/clear`, `compact`
  nem zárja be a lapot; archiválásra nincs hook, a `SessionEnd` app-bezáráskor
  is fut). Publikáláskor a hook jegyzi be a sessiont: utána a modell nyit.
  Modból a `publish` nem megy (az auto mód elutasítja, nincs mögötte kérés), az
  `open` / `read` igen; a mod a `classic.*` eseményeket nem kapja meg
  (mérve, docs/artifact-findings.md). Ahol nem fut mod (régi kliens), a lap
  magától nem nyílik meg. Headless
  (`CLAUDE_CODE_ENTRYPOINT=sdk-*`) sessionben nem kér publikálást. A lap
  fogaskerék-menüje (`settings` tool, `publish.settings`) két kapcsolót ad: az
  **automatikus megnyitás** repónként (`git-graph.autoOpen`; ki: a hook nem
  frissít, a mod nem nyit — a `--forget` is ezt írja, az új Artifact
  `--published`-je törli; a 0.13 előtti `autoPublish=false` is kikapcsoltnak
  számít), az **automatikus publikálás** a gépen (`~/.git-graph/settings.json`;
  ki: Artifact nélküli repóban nem kér publikálást). A `--open-url` session
  nélkül (a `/git-graph:artifact-open`-é) a beállítástól függetlenül az URL-t,
  elavult lapnál a frissítés lépéseit adja. Némán kilép, ha a mappa nem repó: egy SessionStart hook
  minden sessionben lefut, zajt nem csinálhat. A repót mindig regisztrálja — a
  `git-graph --mcp` a lap slugjából a `repos.json`-ból találja meg.
- **Repónként egy Artifact, a worktree-k közösen látják** (0.12 óta): minden
  út a fő checkoutra képződik le (`main_checkout`) — slug, `git-graph.*`
  kulcsok, cím. A `graph_data` minden worktree-t ad (`meta.worktrees`, HEAD-badge
  `worktree` mezővel, worktree-nkénti ál-sor), az állapotukat párhuzamosan gyűjti
  (`collect_worktrees`). A hozzáadott worktree-k a létrehozásuk sorrendjében
  (`worktree_created`: az admin-mappa születési ideje; a git a név szerinti ábécét adná). A saját commit és WIP nélküli worktree HEAD-je (pl. egy trunk-
  commiton, vagy a session törlésekor leválasztva) csonkot kap (`worktree_stubs`:
  a commit `stubs` listája, commitonként a sávok utáni első szabad oszloptól; a lap
  legyezőszerűen rajzolja), így az is elágazik. A saját worktree WIP-je a fix
  sávban, a többié a listában, a fájlok `mtime`-ja szerint (`last_change`; az
  ujjlenyomatban is). Az ágak távolságát (`branch_tracks`, a `meta.tracks`) egyetlen
  `for-each-ref` adja: `base` az `origin/HEAD` céljához (`%(ahead-behind:…)`, git
  2.41+, régebbin ágankénti `rev-list`), `up` az upstreamhez, a remote-only ágnak
  `local` a helyi párjához; a forrás-ágat (reflog) szándékosan nem használjuk — az
  ágak alja mindig az `origin/main`-en van. Az ágválasztó viszont a worktree-k
  HEAD-reflogjából (`logs/HEAD`, `checkout: moving … to <ág>`) csoportosít: az ág
  azé a worktree-é, ahol utoljára ki volt véve (`branch_owners`, a `branches`
  `owner` mezője; csak fájlt olvas). Törölt worktree reflogja vele megy: az ága
  gazdátlan. A `branches` a csak remote ágakat is adja (`remote: true`). A leválasztott
  HEAD-ű worktree ágát a git nem jegyzi — a Claude app `git-worktrees.json`-ja
  igen (`app_worktree_branches`, a worktree `appBranch` mezője); név szerint
  nem azonosítunk. Worktree-váltásra nincs hook: a lap ugyanaz, a session
  indulásakor megnyílt (0.13 előtt `PostToolUse` futott az `Enter`/`ExitWorktree` után).
- **A „saját” worktree az előtérben lévő sessioné** — mérve,
  docs/artifact-findings.md: az app egy Artifactnak **egyetlen keretet** tart,
  és azt mutatja minden sessionben; a link `#horgony`-a nem jut át, a host-híd
  hívásából a session nem derül ki, session-váltásra nincs hook. A Claude app
  viszont sessionönként JSON-t tart (`~/Library/Application Support/Claude/
  claude-code-sessions/*/*/local_*.json`: `cwd` / `worktreePath`,
  `lastFocusedAt`, `isArchived`): a repóban dolgozó, nem archivált sessionök
  közül a legutóbb fókuszált van előtérben (`focused_worktree`, a
  `changes` `focus` mezője). A `lastFocusedAt` 1–3 s késéssel íródik, ezért
  a fókusz ideje az app naplójából jön (`~/Library/Logs/Claude/main.log`,
  `setFocusedSession`, ~20 ms-mal a váltás után; `app_log_focus`, csak az új
  sorokat olvassa, a forgatást kezeli). A lap erről nem kap eseményt (a keret
  rejtés nélkül költözik, egyforma panelméretnél `resize` sincs). Ezért a lap
  mindig egy `changes`-hívást tart nyitva (long-poll, `since` + `wait`,
  `wait_changes`): a szerver külön szálon akkor válaszol, ha az app naplójában
  session-váltás jelenik meg (`log_advance`, ~50 ms), vagy a repó állapota
  (`repo_state`) eltér a `since` tokenben lévőtől — git-műveletnél egy
  `stat`-előszűrő (`stamp_paths`) miatt ~50 ms-on belül, fájlszerkesztésnél a
  2 s-onkénti teljes számításra —, legkésőbb 50 s után üresen. A `since`
  (állapot-hash + naplókurzor + fókusz) miatt a két hívás között jött változás sem vész
  el. A fókuszt a 2 s-os kör is újraszámolja: új sessionre váltáskor a napló
  sora előbb jön, mint a session-fájl, a váltáskor kiadott fókusz még a régi
  (mérve: enélkül 50 s-ig). A szál explicit repóval dolgozik, a `REPO` globálist nem érinti. A `send`
  ezért zárolt, a fókusz-gyorstárak `FOCUS_LOCK` alatt; a `restart` előbb a
  várakozókat válaszoltatja (`WAKE`). A host a lap megszakítását (`signal`) nem
  adja át a szervernek: az árva várakozót a határidő zárja, és `WAITERS_MAX`
  fölött nem várunk. Rejtett keretben a hívás azonnal elbukik, és a lap
  időzítői sem futnak: a lap a megjelenéskor (`wake`) hív újra. Sűrű kérdezés
  tilos: a host ~20 gyors hívás után visszafogja a hívásokat. Belső fájlok, ismeretlen formánál nem
  dönt; a több száz, nagy session-fájlt `stat`-tal figyeli, csak a
  megváltozottat olvassa újra (`app_sessions`). Kézzel nem választható. Halványabb (`.foreign`), ami nem a
  sajáté: worktree-ből nézve ami a HEAD-jéből nem érhető el; a fő checkoutból
  nézve csak a worktree-k saját commitjai és WIP-je — a gazdátlan ágak a fő
  checkouté (a git nem jegyzi fel, hol jöttek létre).
- **A kimenet a repón KÍVÜL, `~/.git-graph/<slug>/`**: `artifact.html` az
  Artifact betöltője — innen publikál a session. Ne tedd konfigurálhatóvá. A projektmappába nem írunk.
- **Az Artifact nem tárol adatot** — ez a lényeg, nem optimalizálás. Egy
  beágyazott adatú lap frissítése nagy repón ~50 s volt (a feltöltő modell az
  élő és a helyi példányt is végigolvassa); a betöltőt csak a saját, a repónév
  vagy a capability-lista változásakor kell feltölteni. Adatot és kódot ne tegyél
  vissza a lapba.
- **A lap kódja élőben jön** (`page_code`, mérve: az Artifact CSP-je engedi az
  `import(blob:)`-ot, docs/artifact-findings.md). A `page/js/` valódi ES-modulok
  (strict mode), a kontextust (`slug`, `repo`, MCP kliens) a betöltő adja a
  `globalThis.GIT_GRAPH`-ban (`state.js`).
- **A lap moduljait a `page_code` köti össze** (`page_modules`, `PAGE_BOOT`): a
  blob-URL-hez relatív út nem oldható fel, ezért a modulok a függőségeik után kapnak
  blob-URL-t, és az importjuk útja a függőségük URL-jére cserélődik. Ezért:
  **körkörös import nem lehet** (az alsóbb modul felfelé callbackkel szól, pl.
  `computeFresh(render)`), importálni csak a sor eleji `import … from './x.js'`
  alakban lehet (dinamikus `import()` nem), és a lapra csak a `main.js`-ből elérhető
  modul kerül — új modul felvétele lista nélkül, az importjával megy. A modul
  exportja kívülről csak olvasható: a közös állapotot a gazdája setterrel írja
  (`setData`, `setExpanded`, `setVisible`, …). A modul ott veszi fel az
  eseménykezelőit, ahol a kódja van; a sorrend a betöltésé (pl. a `details`
  Escape-je a `keyboard`-é előtt). A Check a `scripts/check-page.mjs`-sel köti össze
  őket (hiányzó export, szintaxis); a Biome a fölösleges és a felülírt importot jelzi, a
  `tsc` a típusokat (`types.d.ts`: a lap lekérdezései HTMLElement-et adnak; ahol más
  elem vagy esemény jön, JSDoc-cast).
  A telepítés a `page/js/` minden modulját másolja, a forrásból eltűntet törli
  (`page_files`). A 0.14-es szerver a `page/page.js` hiányában magától nem frissít,
  a következő session hookja telepíti az újat. A betöltő és a `page_code` szerződése a
  `LOADER_API`: csak akkor lép, ha a kettő közti megállapodás változik — eltérésnél
  a `page_code` hibával adja vissza a teendőt, a betöltő kiírja. A betöltő nem
  írhatja felül a `body`-t: a platform a `<title>`-t is oda teszi.
- **Host-híd (`host:git-graph`)** — mérve, docs/artifact-findings.md:
  - Csak a Claude app configjában (`claude_desktop_config.json`) felvett szerver
    érhető el; a `claude mcp add`-os nem. Az app csak induláskor olvassa, és
    **futás közben felülírja** a memóriabeli változattal (beállítás-mentéskor —
    mérve: a bejegyzés eltűnt). Ezért a beírás után azonnal újraindítás.
  - A lapnak deklarálnia kell a `mcp` capability-t (`PUBLISH_CAPS`) — enélkül a
    `use("mcp")` `null`, és a lap azt hiszi, nem az appban fut. A deklaráció
    a session szervere nélkül is átmegy (csak figyelmeztet), és a hash része.
  - A `git-graph --mcp` stdout-ján csak JSON-RPC mehet, ASCII-ban (a locale-tól
    függetlenül); napló, ha kell, stderr-re.
  - A toolok `readOnlyHint: true`-k — a `settings` is, pedig a git-graph saját
    beállítását írja (kapcsolónként ne kérdezzen) —, enélkül az app hívásonként megerősítést
    kérhet. A `watchTool` pollozása ≥ ~30 s, ezért a lap `callTool`-lal hív
    (nyitva tartott `changes`, változáskor `graph_data`).
  - Csak az appban megy (böngészőben `server_not_connected`), csak a
    tulajdonosnak. A lap nem `retryable` hibánál leáll, és kiírja a teendőt.
  - Új tool → a `PUBLISH_CAPS` tool-listájába is (különben `not_in_manifest`),
    és az új betöltő publikálása (a capability-lista a hash része). Az app a
    szerver tool-listáját csak a kapcsolódáskor kéri le: a `restart` utáni
    folyamat ezért `notifications/tools/list_changed`-et küld (`RESTARTED_ENV`,
    a kézfogásban `listChanged: true`), amire az app azonnal újra lekéri (mérve).
    Enélkül az új tool app-újraindításig `not_in_manifest` („does not offer a tool”).
- **A `file_diff` bemenete a lapról jön**: a `sha` csak hex lehet
  (különben `--output=…`-szerű opcióként menne a gitnek), fájlt közvetlenül
  csak akkor olvasunk, ha a git követetlennek mondja — a lapon át ne legyen
  kiolvasható tetszőleges fájl.
- **Publikálás a sessionből** — mérve, docs/artifact-findings.md:
  - Az Artifact API-t csak a modell éri el, ezért a session publikál, a hook
    (`publish_steps`) vagy a `git-graph --publish` lépései szerint; a hook az
    eredményt nem látja, ezért a `git-graph --published <URL>` írja vissza az URL-t és
    a hasht (az `artifact.html`-ből számolva).
  - Friss sessionből meglévő Artifactra a publish csak `Artifact read` után megy
    át (az elutasítás maga is olvasásnak számít).
  - A lépésekben `git-graph` áll, nem abszolút út: a plugin `bin/`-je a Bash
    PATH-ján van, és egy `Bash(git-graph:*)` engedély lefedi.
- **Plugin: nincs install/update/uninstall esemény** (docs). Ezért:
  - A gépi részt a SessionStart hook állítja be (`ensure_installed`), csak ha a
    kód gyökere (`ROOT`) a `CLAUDE_PLUGIN_ROOT` — egy kézi `--session-hook` nem
    telepít. Minden lépés idempotens, csak változáskor ír; a hook stdout-ja a
    hook-JSON-é, napló csak stderr-re (`log`).
  - A `CLAUDE_PLUGIN_ROOT` verziónként más (`…/cache/git-graph/git-graph/<verzió>/`),
    ezért az app a **stabil másolatot** futtatja
    (`~/.git-graph/bin/git-graph`) — symlinket nem, mert a régi verzió mappája
    eltűnhet. A másolat a `git_graph` csomag egyetlen futtatható zipben
    (`stable_bundle`; `python3 <zip>` stdlibből fut): egy fájl, így atomi
    cserével kerül a helyére, egy épp induló szerver sosem lát félig új
    csomagot. Tömörítés és időbélyeg nélkül, hogy változatlan forrásból
    bájtra ugyanaz legyen. A `ROOT` a zipből a `~/.git-graph`.
    A másolat mellé a lap fájljai (`~/.git-graph/page/`) és a manifest is kerül
    (`~/.git-graph/.claude-plugin/plugin.json`) — előbb a lap, aztán a zip, a
    manifest utolsóként: a zip a verzióját ebből olvassa, egy közben induló
    újraindulás különben a régi kódot az új verziónak hinné, és nem frissülne
    tovább. A `--dev-install` is így ír (`install_copy` a `+dev` manifesttel). A lap fájljait a szerver induláskor egyszer olvassa be
    (`page_file`), így a futó verzió a saját kódját adja akkor is, ha a hook már
    újat másolt. A manifestből olvassa a futó szerver induláskor a verzióját (`RUNNING_VERSION`), a
    `changes` pedig a telepítettel együtt adja — a lábléc így jelzi, ha az
    app még a régi kódot futtatja.
  - **A futó szerver frissíti magát** (`watch_plugin` → `pull_update` →
    `restart`): ha a nyilvántartás más verziót mond, mint ami fut, a plugin
    `installPath`-jából átmásolja a csomagot, a lap fájljait és a manifestet (vagy a hook már
    lecserélte), majd két kérés között `os.execv`-vel újraindul ugyanazokon a
    stdio-csöveken. Ezért puffereletlen a stdin-olvasás (`select` + `os.read`,
    saját sorpuffer): csak üres pufferrel indul újra, a csőben maradt kérést az
    új folyamat olvassa. A szerver nem tart állapotot a kézfogás után, a
    `respond` így az újraindult folyamatban is válaszol. A lap a `changes`
    verzióváltásán újratölt (`location.reload`), így az új `page_code` is megjön.
    Mérve kamu `HOME`-mal: 12/12 kérés megválaszolva a csere körül.
  - A leszerelést is ez a szál végzi (`watch_plugin`): az
    `installed_plugins.json`-ban (Claude Code belső fájl, `version: 2`) keresi a
    `git-graph@…` kulcsot. Ismeretlen formátumnál nem dönt, és csak két
    egymást követő hiány után szerel le (frissítés közbeni pillanat). Csak a
    stabil példányban fut (`sys.argv[0]` a `STABLE`) — a working tree-ből indított
    `git-graph --mcp` nem szerel le. Több példány fut (az app és minden Code-session indít egyet), a
    leszerelés idempotens. Ha az app nem fut, a következő indulásáig vár.
  - A `bin/` csak a Claude **Bash eszközének** PATH-ja, a hooké nem: a hook a
    `${CLAUDE_PLUGIN_ROOT}/bin/git-graph`-ot hívja. Terminálos parancs nincs.
  - Bump nélkül a `claude plugin update` nem hoz le semmit (a `plugin.json`
    `version`-je dönt).
