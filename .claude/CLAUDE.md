# git-graph

Git Graph-szerű commit-gráf **bármelyik repóból**: élő Artifact, amely a
Claude appban a gépen futó `git-graph --mcp`-ből olvas. A VS Code `mhutchie.git-graph` elrendezését követi.

Használat és felépítés: [README.md](../README.md).

## Repó térkép

| Útvonal | Mi ez |
| --- | --- |
| `bin/git-graph` | a `git-graph` parancs: a `git_graph` csomag vékony belépője (a hook és a Bash eszköz ezt futtatja) |
| `git_graph/` | a Python-oldal: `gitio` (git-hívások, `REPO`), `graph` (a `graph_data` csomagja: commitok, refek, összerakás), `stats` (fájlstatisztika), `worktrees` (worktree-k, WIP-sor), `branches` (ágak, távolságok), `lanes` (sávkiosztás), `diff`, `avatars`, `page` (betöltő, `page_code`, ikonok), `registry` (slug, `repos.json`, sessionök), `claude_app` (az app session-fókusza), `watch` (a `changes` long-pollja), `publish`, `mcp` (`--mcp`), `install` (stabil másolat, frissítés, leszerelés), `hook` (`--session-hook`), `cli`, `state` (`~/.git-graph`, atomi írás) |
| `page/` | a lap: `loader.html` (az Artifact betöltője, `build()`), `head.html`, `page.css`, `body.html`, `js/` (a lap ES-moduljai, belépő: `main.js`; a `page_code` köti össze), `file-icons.json` (fájltípus-ikonok, generált), `vendor/` (a Mermaid 12.2.0 karcsú egyfájlos buildje + licencek, `scripts/mermaid.sh`; lustán, `page_code` `part: "mermaid"`) |
| `page/js/` | `state` (közös állapot + setterek), `dom`, `util`, `dates`, `icons`, `model` (saját worktree, színek, elérhetőség), `avatars`, `graph` (SVG), `anim`, `layout`, `scroll`, `panel`, `syntax`, `diff-html`, `md-diff`, `mermaid` (diagramok a markdown-diffben), `diff` (fájl-diff), `refs` (chipek), `details` (commit-panel), `rows` (`render`), `hydrate`, `menu`, `branches` (ágválasztó), `filters`, `keyboard`, `theme`, `settings`, `mcp`, `live` (`startLive`), `tip`, `main` |
| `scripts/check-page.mjs` | a lap moduljainak szintaxisa és összekötése (import ↔ export) Node-ban, futtatás nélkül — a Check része |
| `page/js/types.d.ts`, `page/tsconfig.json` | a lap típusai (`graph_data`, `GIT_GRAPH`) a `tsc --checkJs`-hez — a lapra nem kerül |
| `scripts/mermaid.sh` | a `page/vendor/mermaid.min.js` karcsú buildje (esbuild, a nehéz diagramtípusok helyén csonk, ELK-kal) és a licencek — kézzel, frissítéskor; a host-híd határa alatt kell maradnia |
| `scripts/file-icons.py` | a `page/file-icons.json` előállítása a Catppuccin VS Code ikonjaiból (MIT, verzióra rögzítve) — kézzel, frissítéskor |
| `tests/` | modulonként egy `test_<modul>.py`, kamu `HOME`-mal (`helpers.py`: a csomag friss betöltése, eldobható repók, MCP-kliens); `test_mcp.py` a füstteszt: `git-graph --mcp` stdio-n a working tree-ből, és a stabil másolatból; `tests/page/`: a lap viselkedése headless Chromiumban (Playwright, `harness.py`: valódi betöltő + `git-graph --mcp`, fixture-repó) |
| `ruff.toml`, `biome.json` | lint: Python (3.9-célverzióval) és a `page/` JS / CSS / HTML-je |
| `.claude-plugin/plugin.json` | Claude Code plugin manifest — a verzió egyetlen forrása |
| `.claude-plugin/marketplace.json` | a `git-graph` marketplace: egyetlen plugin, `source: "./"` |
| `hooks/hooks.json` | a plugin SessionStart hookja (`--session-hook`) és a mod (`modules`) |
| `hooks/register.ts` | a plugin modja: a repó Artifactját a modell nélkül nyitja meg (`git-graph --open-url`, `Artifact open`); teszt: `register.test.ts` |
| `skills/artifact-publish/SKILL.md` | a `/git-graph:artifact-publish` skill (`git-graph --publish`, publikálja, ha kell, és megnyitja) |
| `skills/artifact-open/SKILL.md` | a `/git-graph:artifact-open` skill (`git-graph --open-url`, és megnyitja az Artifactot; elavultat előbb frissít, újat nem hoz létre) |
| `skills/artifact-forget/SKILL.md` | a `/git-graph:artifact-forget` skill: az aktuális vagy az összes repó Artifactjának törlése + `git-graph --forget` (választás; uninstall előtt: mind) |
| `docs/README.md`, `docs/<funkció>.md` | a funkcióoldalak listája és oldalai (pl. `file-diff.md`): működés, `R-N` követelmények, használat |
| `docs/artifact-findings.md` | **mérési napló**: mit tud és mit nem az Artifact platform |
| `docs/architecture.md` | a lenti szabályok indoklása, a mért háttér, a kézi ellenőrzés menete — **módosítás előtt az érintett részt olvasd el** |

## Parancsok

```sh
claude plugin install git-graph@git-graph   # a hook az első sessionben telepít mindent
claude --plugin-dir .                      # fejlesztés: a working tree pluginként, bump nélkül
claude plugin validate . --strict          # manifestek, skill, hook
git-graph --help             # a teljes súgó
git-graph --publish          # az Artifact vékony lapja + a publikálás lépései a sessionnek
git-graph --published <URL>  # a session publikálása után: URL + hash a .git/config-ba
git-graph --mcp              # MCP szerver stdio-n — a Claude app indítja, nem kézzel
git-graph --artifacts        # ismert repók Artifactjai (regiszter + a szülőmappák repói)
git-graph --forget           # a repó git-graph nyomai + automatikus megnyitás KI
git-graph --open-url --session <ID>   # a mod kérdése: az URL, ha most meg kell nyitni
claude plugin test .         # a mod tesztjei (hooks/*.test.ts)
uv run --no-project --with playwright==1.63.0 python -m unittest discover -s tests/page   # a lap böngészőben
python3 bin/git-graph …    # közvetlenül, a working tree-ből
python3 bin/git-graph --dev-install   # a working tree az appban futó git-graph helyére (+dev), a lap élőben
```

Az Artifact csak egy betöltő (`page/loader.html`, `build()`): a lap kódját
(`page/head.html`, `page.css`, `body.html`, `js/*.js`) a `page_code` toollal, az adatot a
`graph_data`-val kéri a Claude app host-hídján át a `git-graph --mcp`-ből, a
`startLive` pollozójával. Kódváltozás így újrapublikálás nélkül él: a
`claude plugin update` után a futó szerver percen belül frissíti magát, a lap
pedig újratölt.
A `git-graph` a Claude Bash eszközének parancsa (a plugin `bin/`-je), terminálos
link és pillanatkép nincs; parancs nélkül a súgót írja ki.

A **Check** (`.claude/check.toml`): a lap moduljainak összekötése Node-ban, ruff +
Biome, `tsc --checkJs` a `page/js`-re, a tesztek `/usr/bin/python3`-mal (ahogy az app
indítja), a mod tesztjei és a lap viselkedése headless Chromiumban (`tests/page/`).
Ezen túl kézzel: a lap az appban, `python3 bin/git-graph --dev-install` után. A
válaszban írd ki a verziót (`<verzió>+dev.<időbélyeg>`) — a lap láblécén ebből
látszik, hogy már az új állapot fut. Forrásból futó plugin, a hook és a
telepítés kézi próbája: [architecture.md](../docs/architecture.md#fejlesztés-és-ellenőrzés).

## Konvenciók

- **Nyelv**: magyar — kommentek, doksi, commit-body, a generált UI feliratai.
- **Megjelenés**: a Claude app nyelvét követi (a Git Graph-ból a gráf marad).
  Meleg palettát használ, és a Claude Light / Dark kódszíneket. Betűk:
  Anthropic Sans / Mono, ahol nincs, a rendszeré; webfont nincs. A
  kontrollok az app mintájára épülnek: kapcsoló (szűkös helyen ikonnal),
  lenyíló menü (`makeMenu`: ágválasztó és téma, natív `<select>` nincs),
  ikonok inline stroke-SVG-ként (`ICONS`). A fájltípus-ikonok a Catppuccin
  készletéből jönnek, a lap `--ic-*` színeire kötve: a szerver rendeli a
  fájlhoz (`file_icon`), és csak a használtak SVG-jét adja a
  `graph_data`-ban (`fileIcons`). A lista egysoros, napokra bontott
  (`.day-group`, ragadós fejléccel), táblázatfej nélküli. Görgetni
  commitonként lehet (`stepRows`: egy kattanás egy commit, animáció nélkül,
  a sor a napfejléc alá igazodik). A CSS scroll-snap ezt nem tartotta, egy
  kattanással több sort ugrott; az animáció darabosnak tűnt. A simító
  egérszoftverek (BetterMouse) régi irányú lendületét a `coasting` szűri,
  különben fordulásnál ide-oda ugrál. A dátum `Europe/Budapest` szerint,
  magyar formában jelenik meg.
- **Függőség**: kizárólag Python 3 stdlib. Ez szándékos — az eszköznek bárhol
  futnia kell, `pip install` nélkül. Ne hozz be libet. A lap egyetlen külső
  JS-e a vendorolt Mermaid (`page/vendor/`, verzióra rögzítve). A lintek (ruff, Biome),
  a `tsc` és a Playwright csak fejlesztői eszközök, `uvx` / `uv run --with` / `pnpm dlx`
  futtatja őket, verzióra rögzítve.
- **Minden git-hívás olvas.** A script sosem módosít repót. Kivétel a
  `.git/config` `git-graph.*` kulcsai — lokális, sosem commitolódik.
- **Hálózat csak az avatarért.** GitHub-os repónál a szerzők képét a Python
  tölti le háttérszálon (`avatars_for`). Noreply címnél közvetlenül, különben az
  API-ból, egy pusholt commitjukon át. A kép data URI-ként kerül a
  `graph_data`-ba (az Artifact CSP-je külső képet nem enged), gyorstárazva
  (`~/.git-graph/avatars.json`). Ami nem jött, 6 óra múlva újrapróbálódik. Az
  ujjlenyomatban az `avatars` szám jelzi a lapnak, hogy új kép érkezett.
- **Verziókezelés**: SemVer, a verzió egyetlen forrása a
  `.claude-plugin/plugin.json` (a `marketplace.json` nem ismétli); kézi
  `vX.Y.Z` tag, Conventional Commits.
- **Commit**: bár ez plugin-repó (`.claude-plugin/` a gyökérben), az auto-commit
  (`RULE:git`) itt is megy — a kész, ellenőrzött munka kérdés nélkül commitolódik; a
  plugin-repó kivétel itt nem érvényes.
- **Deploy**: a marketplace forrása a repó `main`-je, tehát a merge már
  élesít; a `/release` deploy-lépése a helyi frissítés:
  `claude plugin marketplace update git-graph && claude plugin update git-graph@git-graph`.
- **Env**: a toolnak nincs env-függősége, ezért nincs `.env.example`.
- **Funkcióoldal**: bár ez plugin, a funkcióoldalak a `docs/<funkció>.md`-ben élnek, a lista a
  `docs/README.md`; a README csak belépő, funkciónként egy rövid bekezdéssel és linkkel —
  a `RULE:docs` plugin-kivétele (a komponens README-je) itt nem érvényes.

## Gotchák

Egy sor szabály; a miért és a mérés: [architecture.md](../docs/architecture.md#gotchák).

- **Lap**
  - Osztálynév névtérrel (`ref-*`), rövid, generikus osztálynév nem lehet — egyetlen stíluslap van.
  - Ami a lapra kerül, az `embed()`-en megy át (`</` → `<\/`, U+2028/29); `<meta charset="utf-8">` az első sor.
  - A `drawGraph()` a DOM-ból méri a sorok Y-ját: minden DOM-változás után újra kell hívni.
  - Sor-kiemelés csak a `.row-in`-re, a gráf-oszlopra nem (az `#lanes` SVG a sorok mögött van).
  - ES-modulok, a `page_code` köti össze: körkörös és dinamikus import nincs, az import a sor eleji `import … from './x.js'`; az export csak olvasható, a közös állapotot a gazdája setterrel írja.
  - A betöltő ↔ `page_code` szerződés a `LOADER_API`; a betöltő a `body`-t nem írhatja felül.
  - Az Artifact nem tárol adatot és kódot — csak a betöltő; ne tedd vissza a lapba.
- **Git és Python**
  - Minden git-hívás olvas és `--no-optional-locks`; `core.fsmonitor` nem használható.
  - A git a valódi binárisával fut (`git_bin`), nem a `/usr/bin/git` shimmel.
  - A `REPO` a `gitio` globálisa: váltás `set_repo`-val, olvasás `gitio.REPO`-ként (nem `from .gitio import REPO`).
  - Python 3.9-kompatibilis (`/usr/bin/python3`); függvényen belüli import a csomagból nem lehet (a zip a futó szerver alatt cserélődhet).
  - Repónév az `origin` remote-ból, nem a mappanévből; minden út a fő checkoutra képződik le (`main_checkout`).
  - A WIP ál-sorok (`*uncommitted:<slug>`, alatta `*staged:<slug>`) a lane-kiosztás ELŐTT kerülnek be, a `meta` a valódi commitokból készül.
  - A `log --all` helyett `ALL_BUT_STASH` (a `refs/stash` nélkül); a stash-ek a `git stash list`-ből, egyetlen szülővel (`^1`).
  - A `file_diff` bemenete a lapról jön: `sha` csak hex, fájlt csak követetlen esetben olvasunk közvetlenül.
  - A kimenet a repón kívül, `~/.git-graph/<slug>/`; a projektmappába nem írunk.
- **MCP és host-híd**
  - stdout-on csak ASCII JSON-RPC, napló stderr-re; minden tool `readOnlyHint: true`.
  - Új tool → `PUBLISH_CAPS` + új betöltő publikálása; `restart` után `notifications/tools/list_changed`.
  - A host-hídon csak a `claude_desktop_config.json` szervere érhető el; a beírás után app-újraindítás.
  - A `changes` long-poll: sűrű kérdezés tilos (a host ~20 gyors hívás után visszafog).
  - A „saját” worktree az előtérben lévő sessioné, az app session-fájljaiból és naplójából (`focused_worktree`) — kézzel nem választható.
- **Plugin és telepítés**
  - Nincs install/update/uninstall esemény: a SessionStart hook telepít (`ensure_installed`), a futó szerver frissít és szerel le (`watch_plugin`).
  - Az app a stabil zipet futtatja (`~/.git-graph/bin/git-graph`); csere sorrendje: lap → zip → manifest.
  - A hook publikáltat (`publish_steps`), a mod nyit meg (`--open-url`); modból `publish` nem megy.
  - Meglévő Artifactra a publish csak `Artifact read` után megy át; a lépésekben `git-graph` áll, nem abszolút út.
  - Bump nélkül a `claude plugin update` nem hoz le semmit.
