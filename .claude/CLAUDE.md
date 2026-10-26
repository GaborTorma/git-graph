# git-graph

Git Graph-szerű commit-gráf **bármelyik repóból**: élő Artifact, amely a
Claude appban a gépen futó `git-graph --mcp`-ből olvas. A VS Code `mhutchie.git-graph` elrendezését követi.

Használat és felépítés: [README.md](../README.md).

## Repó térkép

| Útvonal | Mi ez |
| --- | --- |
| `bin/git-graph` | a `git-graph` parancs: a `git_graph` csomag vékony belépője (a hook és a Bash eszköz ezt futtatja) |
| `git_graph/` | a Python-oldal: `gitio` (git-hívások, `REPO`), `graph` (a `graph_data` csomagja: commitok, refek, összerakás), `stats` (fájlstatisztika), `worktrees` (worktree-k, WIP-sor), `branches` (ágak, távolságok), `lanes` (sávkiosztás), `diff`, `avatars`, `page` (betöltő, `page_code`, ikonok), `registry` (slug, `repos.json`, sessionök), `claude_app` (az app session-fókusza), `watch` (a `changes` long-pollja), `publish`, `mcp` (`--mcp`), `install` (stabil másolat, frissítés, leszerelés), `hook` (`--session-hook`), `cli`, `state` (`~/.git-graph`, atomi írás) |
| `page/` | a lap: `loader.html` (az Artifact betöltője, `build()`), `head.html`, `page.css`, `body.html`, `js/` (a lap ES-moduljai, belépő: `main.js`; a `page_code` köti össze), `file-icons.json` (fájltípus-ikonok, generált), `vendor/` (a Mermaid 12.2.0 karcsú egyfájlos buildje + licencek, `scripts/mermaid.sh`; lustán, `page_code` `part: "mermaid"`; az Anthropic Sans és Mono `anthropic-sans.woff2`, `anthropic-mono.woff2`, a Claude app betűi, `part: "font"`, `"font-mono"`) |
| `page/js/` | `state` (közös állapot + setterek), `dom`, `util`, `dates`, `icons`, `model` (saját worktree, színek, elérhetőség), `avatars`, `graph` (SVG), `anim`, `layout`, `scroll`, `panel`, `syntax`, `diff-html`, `md-diff`, `mermaid` (diagramok a markdown-diffben), `diff` (fájl-diff), `refs` (chipek), `details` (commit-panel), `rows` (`render`), `hydrate`, `menu`, `branches` (ágválasztó), `filters`, `keyboard`, `theme`, `settings`, `mcp`, `live` (`startLive`), `tip`, `font` (az Anthropic Sans és Mono regisztrálása), `main` |
| `scripts/check-page.mjs` | a lap moduljainak szintaxisa és összekötése (import ↔ export) Node-ban, futtatás nélkül — a Check része |
| `page/js/types.d.ts`, `page/tsconfig.json` | a lap típusai (`graph_data`, `GIT_GRAPH`) a `tsc --checkJs`-hez — a lapra nem kerül |
| `scripts/mermaid.sh` | a `page/vendor/mermaid.min.js` karcsú buildje (esbuild, a nehéz diagramtípusok helyén csonk, ELK-kal) és a licencek — kézzel, frissítéskor; a host-híd határa alatt kell maradnia |
| `scripts/screenshots.py` | a funkcióoldalak képei (`docs/img/<funkció>/`) a `tests/page` fixture-repóiból — kézzel, UI-változáskor (`/workflow:docs`) |
| `scripts/anthropicons.py` | a `design/icons/anthropicons.json` előállítása az app ikonfontjából és a CDS-bundle névtáblájából (a gyorsítótárból kibontva) — kézzel, frissítéskor |
| `scripts/file-icons.py` | a `page/file-icons.json` előállítása a Catppuccin VS Code ikonjaiból (MIT, verzióra rögzítve) — kézzel, frissítéskor |
| `design/icons/` | ikonforrások, a lapra nem kerülnek: a Fejlesztő rajzai (CorelDRAW, pl. `cloud-branch-icon.cdr` → a `branchCloud` SVG-je) és az app teljes Anthropicons-készlete SVG-útként (`anthropicons.json`, innen kerül a lapra, ami kell) |
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
uv run --no-project --with playwright==1.63.0 --with pytest==9.0.3 --with pytest-xdist==3.8.0 python -m pytest tests/page -n auto --dist loadscope -q -p no:cacheprovider   # a lap böngészőben
uv run --no-project --with playwright==1.63.0 python scripts/screenshots.py   # a funkcióoldalak képei
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

A Checken túl kézzel: a lap az appban, `python3 bin/git-graph --dev-install` után. A
válaszban írd ki a verziót (`<verzió>+dev.<időbélyeg>`) — a lap láblécén ebből
látszik, hogy már az új állapot fut. Forrásból futó plugin, a hook és a
telepítés kézi próbája: [dev-from-source](memory/dev-from-source.md).

## Konvenciók

- **Nyelv**: magyar — a kommentek és a generált UI feliratai.
- **Megjelenés**: a Claude app nyelvét követi (a Git Graph-ból a gráf marad).
  Az app design-systemjét (CDS, „comfortable” sűrűség, a jelenlegi „fizzy-lake”
  színtémával) használja: semleges szürkék, kék akcentus, git- és állapot-színek,
  14 px-es alapszöveg, 32 px-es kontrollok — az értékek a `page.css` tokenjeiben,
  témánként (az app CSS-ét nem importáljuk). A chip az app Badge-e (20 px, tint
  háttér, 1,5 px-es keret, a sarok a magasság negyede, 16 px-es ikon a széltől
  4 px-re). A sávszín a `chart-categorical` 1–8 (`--lane-<n>`, a chiphez
  tint-hármassal: `lcStyle`); CSS-változó, így témaváltáskor a gráf magától
  átszíneződik. Az ikonok az app Anthropicons-glifái, ahol van pár (`ic-ag`; a
  teljes készlet `design/icons/anthropicons.json`), a többi saját, 1,2 egységes
  vonalú rajz. A méretük az app skálája: 16 px (gomb, chip, panel), 12 px (nyilak), a menükben
  20 px (comfortable `md`, `ICONS_MD`; a pipa `bold`, akcentus színű). A kód színei a Claude Light /
  Dark kódszínek. Súgó csak a saját buborék (`data-tip`, `tip.js`; natív
  `title` nincs). Betű: az Anthropic Sans, a kódé az Anthropic Mono (a keretben nincsenek meg,
  külső fontot a CSP nem enged): a vendorolt woff2-ket a `page_code` adja base64-ben (`part:
  "font"`, `"font-mono"`), a lap `FontFace`-ként regisztrálja (`font.js`); addig és hiba esetén a
  rendszerfont. A vastagság az app tengelyértékei (`--w-*`: törzs 360 … bold 560). A
  kontrollok az app komponenseinek méreteit és tokenjeit követik (Select: a lenyíló és a fogaskerék mező-gombja, TextInput,
  Switch, Menu, SegmentedControl, TextLink, Shortcut, Spinner): kapcsoló (szűkös helyen ikonnal),
  lenyíló menü (`makeMenu`: ágválasztó és téma, natív `<select>` nincs),
  ikonok inline stroke-SVG-ként (`ICONS`). A fájltípus-ikonok a Catppuccin
  készletéből jönnek, a lap `--ic-*` színeire kötve: a szerver rendeli a
  fájlhoz (`file_icon`), és csak a használtak SVG-jét adja a
  `graph_data`-ban (`fileIcons`). A lista egysoros, napokra bontott
  (`.day-group`, ragadós fejléccel), táblázatfej nélküli. Görgetni
  commitonként lehet (`stepRows`: egy kattanás egy commit, animáció nélkül,
  a sor a napfejléc alá igazodik; a simító egérszoftverek régi irányú
  lendületét a `coasting` szűri — miért: [scroll-step-rows](memory/scroll-step-rows.md)).
- **Függőség**: kizárólag Python 3 stdlib. Ez szándékos — az eszköznek bárhol
  futnia kell, `pip install` nélkül. Ne hozz be libet. A lap egyetlen külső
  JS-e a vendorolt Mermaid (`page/vendor/`, verzióra rögzítve), fontjai a vendorolt
  Anthropic Sans és Mono. A lintek (ruff, Biome),
  a `tsc` és a Playwright csak fejlesztői eszközök, `uvx` / `uv run --with` / `pnpm dlx`
  futtatja őket, verzióra rögzítve.
- **Minden git-hívás olvas.** A script sosem módosít repót. Kivétel a
  `.git/config` `git-graph.*` kulcsai — lokális, sosem commitolódik. A kimenet a
  repón kívül, `~/.git-graph/<slug>/`; a projektmappába nem írunk.
- **Hálózat csak az avatarért.** GitHub-os repónál a szerzők képét a Python
  tölti le háttérszálon (`avatars_for`). Noreply címnél közvetlenül, különben az
  API-ból, egy pusholt commitjukon át. A kép data URI-ként kerül a
  `graph_data`-ba (az Artifact CSP-je külső képet nem enged), gyorstárazva
  (`~/.git-graph/avatars.json`). Ami nem jött, 6 óra múlva újrapróbálódik. Az
  ujjlenyomatban az `avatars` szám jelzi a lapnak, hogy új kép érkezett.
- **Verziókezelés**: a verzió egyetlen forrása a `.claude-plugin/plugin.json` (a
  `marketplace.json` nem ismétli).
- **Deploy**: a marketplace forrása a repó `main`-je, tehát a merge már
  élesít; a `/release` deploy-lépése a helyi frissítés:
  `claude plugin marketplace update git-graph && claude plugin update git-graph@git-graph`.
- **Env**: a toolnak nincs env-függősége, ezért nincs `.env.example`.
- **Funkcióoldal**: bár ez plugin, a funkcióoldalak a `docs/<funkció>.md`-ben élnek, a lista a
  `docs/README.md`; a README csak belépő, funkciónként egy rövid bekezdéssel és linkkel —
  a `RULE:docs` plugin-kivétele (a komponens README-je) itt nem érvényes.
