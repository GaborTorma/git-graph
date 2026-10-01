# git-graph

Git Graph-szerű commit-gráf **bármelyik repóból**, egyetlen önálló HTML fájlba.
A VS Code [`mhutchie.git-graph`](https://marketplace.visualstudio.com/items?itemName=mhutchie.git-graph)
elrendezését és Dark+/Light+ palettáját követi.

```sh
gg                    # az aktuális repó → ~/.git-graph/<slug>/index.html (pillanatkép)
gg --open             # …és megnyitja a böngészőben
gg ~/dev/masik-repo   # másik repó
gg --limit 200        # csak az utolsó 200 commit (alap: mind)
gg --out graf.html    # máshova (relatív út a hívás helyéhez)
gg --publish          # az Artifact élő lapjának publikálása (headless claude-dal)
gg --serve            # élő kiszolgálás: http://127.0.0.1:7788
gg --mcp              # MCP szerver a Claude appnak (az app indítja, nem kézzel)
gg --launch-config    # .claude/launch.json bejegyzés a Browser panelhez
gg --artifacts        # az ismert repók Artifactjai (<repó>\t<URL>)
gg --forget           # a repó git-graph nyomai törlése (az Artifactot nem törli)
ggl                   # ugyanaz, rövidebben
```

Három nézet, más-más célra:

| | Pillanatkép (`gg`) | Browser panel (`gg --serve`) | Artifact |
| --- | --- | --- | --- |
| Mi | önálló HTML fájl, beágyazott adattal | loopback szerver | adat nélküli lap a claude.ai-on |
| Adat | a generálás pillanatáé | élő, HTTP-n | élő, a gépen futó `gg --mcp`-ből |
| Frissülés | kézi újrafuttatás | ~2 mp-en belül | ~2 mp-en belül |
| Hol nézed | böngésző | a Claude Desktop **Browser panelje** | a **Claude appban**, a saját gépeden |

## Telepítés

Claude Code plugin, saját marketplace-szel (maga ez a repó):

```sh
claude plugin marketplace add GaborTorma/git-graph
claude plugin install git-graph@git-graph
```

A plugin hozza a `/git-graph:git-graph` skillt, a SessionStart hookot, és a Claude
Bash eszközének PATH-jára a `git-graph` / `gg` / `ggl` parancsokat. Függősége
nincs a Python 3 stdliben túl; minden git-hívás **csak olvas**.

A pluginnak nincs telepítési eseménye, ezért a gépi részt az **első session
hookja** állítja be — és minden verzióváltáskor frissíti (idempotens, csak
változáskor ír):

- `~/.git-graph/bin/git-graph` (+ `gg`, `ggl`) — a script stabil másolata. A
  plugin útvonala verziónként más, a launchd és az app ezt futtatja.
- `~/.local/bin/{git-graph,gg,ggl}` — terminálos parancsok a másolatra (ha a
  mappa létezik; valódi fájlhoz és idegen symlinkhez nem nyúl).
- `~/Library/LaunchAgents/ai.torma.git-graph.plist` — a `gg --serve`-et a
  bejelentkezés indítja és életben tartja (`/usr/bin/python3`, napló:
  `~/.git-graph/serve.log`). Új verziónál újraindul.
- `~/Library/Application Support/Claude/claude_desktop_config.json` → `git-graph`
  MCP szerver (előtte mentés). Az app csak induláskor olvassa: ilyenkor a
  session szól, hogy **egyszer újra kell indítani**.

**Eltávolítás:** két lépés.

1. `/git-graph:remove` egy sessionben — törli az Artifactokat (a `gg --artifacts`
   listája alapján, mindegyiket külön jóváhagyással), és repónként a `gg
   --forget`-tel a `git-graph.*` kulcsokat, a helyi lapokat és a
   regiszterbejegyzést. Közben kikapcsolja az automatikus publikálást, hogy a
   futó szerver ne hozzon létre újat. Kihagyható: akkor az Artifactok és a
   kulcsok maradnak, és egy újratelepítés ugyanazokat éleszti újra.
2. `claude plugin uninstall git-graph@git-graph`. A futó szerver percenként
   megnézi a Claude Code nyilvántartását (`installed_plugins.json`), és ha a
   plugin két egymást követő ellenőrzésnél hiányzik, leszereli a fentieket — az
   MCP-bejegyzést, a `~/.local/bin` linkjeit, a `~/.git-graph`-ot és végül
   saját magát. Olvashatatlan vagy ismeretlen formátumú nyilvántartásnál nem
   töröl semmit. Az appot csak utána érdemes újraindítani.

**Verziózás:** SemVer, a verzió egyetlen forrása a
`.claude-plugin/plugin.json`. Bump nélkül a `claude plugin update` nem hoz le
semmit. Kiadás: `vX.Y.Z` tag.

Fejlesztés közben, bump nélkül: `claude --plugin-dir .` (csak az adott
sessionre). Ilyenkor a hook ugyanúgy telepít, de mivel a nyilvántartásban nincs
benne, a szerver ~2 perc múlva leszerel — a következő session újra telepít.

## Élő mód a Claude Desktopban

A cél: **ne kelljen parancsot írni a chatbe**, mégis friss gráfot láss.

1. A `gg --serve` a loopbackon szolgál ki: `/` a friss HTML, `/data` a friss
   adat, `/fingerprint` egy pár száz bájtos ujjlenyomat (HEAD + refek hash-e +
   piszkos fájlok száma), `/diff` egy fájl diffje (→ Fájl-diff).
2. A lap kétmásodpercenként az **ujjlenyomatot** kéri, és csak tényleges
   változásra tölt `/data`-t — a nyitott commit-panel, a szűrők és a görgetés
   megmaradnak.
3. Melyik repót mutatja? Amit az URL mond: `http://<slug>.localhost:7788` — a
   **SessionStart hook** ezt az URL-t adja át (ugyanazt, amit a launch config
   is használ), így minden session panelje a **sajátját** mutatja akkor is, ha
   több session fut egyszerre. A szerver a `?repo=<útvonal>` alakot is érti
   (kézi használatra), paraméter és slug nélkül pedig a `~/.git-graph/current`
   a tartalék — azt szintén a hook írja.
4. A hook a session indulásakor megkéri Claude-ot, hogy nyissa meg a repó élő
   **Artifactját** (`git-graph.artifact`). Ha a repónak még nincs, a Browser
   panelt nyittatja meg ezzel az URL-lel — a szerver közben létrehozza az
   Artifactot, és a következő sessiontől az nyílik.

### `gg --launch-config` (röviden: `ggl`)

Beírja a repó `.claude/launch.json`-jába az élő preview bejegyzését, így a panel
névvel is indítható (`preview_start name="git-graph"`), URL nélkül:

```json
{ "name": "git-graph", "url": "http://git-graph-94eba9.localhost:7788", "port": 7788 }
```

A Claude Desktop localhostra **csak origint** fogad el — path és query nélkül —,
ezért a repó itt a **hostnévbe** kerül: `<mappanév>-<útvonal-hash>.localhost`.
A Chromium minden `*.localhost` nevet a loopbackra old fel, a szerver pedig a
`Host` fejlécből tudja, melyik repót kérted. A slug→útvonal párokat a
`~/.git-graph/repos.json` tartja.

A parancs a fájl **többi bejegyzését és kulcsát megtartja** (csak a saját,
`git-graph` nevű sorát cseréli), de a JSON-t újraformázza. A `git-graph` mindig
a **lista elejére** kerül — a névtelen indítás az első bejegyzést választja.

A slug abszolút útvonalból származik, más gépen értelmetlen — ezért a parancs a
`launch.json`-t felveszi a repó **lokális** ignore-listájába
(`.git/info/exclude`). Ha a repó viszont
**már követi** a fájlt (mert van benne saját dev-szerver bejegyzés), nem nyúl
hozzá, csak figyelmeztet — ott neked kell eldöntened, mi legyen a sorával.

Nincs `launch.local.json`: mérve, a `.claude/launch.d/` drop-in mappa létezik
ugyan, de csak framebuffer (VNC) forrásokra — egy oda tett preview-bejegyzést a
`preview_start` nem talál meg. A lokális kizárás tehát az egyetlen jó válasz.

> A `preview_start` **nem parancssori program**, hanem Claude eszköze — a
> terminálból nem futtatható. Vagy a session hookja kéri meg rá Claude-ot
> (ez a normál út, nem kell gépelni semmit), vagy kézzel beilleszted a fenti
> URL-t a Browser panel címsorába. Rendszer-böngészőben: `open <URL>`.

A hook némán kilép, ha a mappa nem git repó, vagy ha se Artifactja nincs, se a
szerver nem fut — az „off kapcsoló" a plugin kikapcsolása
(`claude plugin disable git-graph@git-graph`).

## Felépítés

| Útvonal | Mi |
| --- | --- |
| `bin/git-graph` | maga a script: adatgyűjtés + beágyazott HTML/CSS/JS sablon + szerverek + telepítés |
| `bin/gg` | symlink a `git-graph`-ra — rövid alias |
| `bin/ggl` | symlink a `git-graph`-ra; ezen a néven a `--launch-config` a default |
| `.claude-plugin/plugin.json` | a plugin manifestje — a verzió egyetlen forrása |
| `.claude-plugin/marketplace.json` | a `git-graph` marketplace (egyetlen plugin: ez a repó) |
| `hooks/hooks.json` | SessionStart hook: `git-graph --session-hook` (telepít + megnyittatja a gráfot) |
| `skills/git-graph/SKILL.md` | `/git-graph:git-graph`: `gg --publish`, majd megnyitja az Artifactot |
| `skills/remove/SKILL.md` | `/git-graph:remove`: az Artifactok törlése és a repók kitakarítása az eltávolítás előtt |
| `docs/artifact-findings.md` | **mit tud és mit nem az Artifact platform** — mérésekkel |
| `docs/desktop-live.md` | miért a Browser panel + lokális szerver az élő út — mérésekkel |
| `docs/mcp-plan.md` | terv az élő, magától frissülő verzióhoz (blokkolva, lásd findings) |
| `probe/` | eldobható MCP-mérőeszköz a blokkoló újratesztelésére |

## Kimenet

A repón **kívülre**, `~/.git-graph/<slug>/` alá — ugyanaz a slug, mint a
`<slug>.localhost` címben:

| Fájl | Mi |
| --- | --- |
| `index.html` | a `gg` pillanatképe, beágyazott adattal |
| `artifact.html` | az Artifact vékony lapja — adat nélkül, ezt tölti fel a `gg --publish` |

A projektmappába nem kerül semmi.

## Artifact

Az Artifact **élő**, de adatot nem tárol: a lap a Claude appban megnyitva a
gépeden futó `gg --mcp`-ből kéri, az app **host-hídján** át
(`callTool("host:git-graph", …)`). Ugyanaz a logika, mint a Browser panelen:
2 mp-enként az olcsó `fingerprint` (refek, HEAD, munkakönyvtár — ~40 ms), és
csak változáskor a teljes `graph_data` (150–300 ms). A lábléc kiírja a mért
időket. Egy lenyitott fájl diffje a `file_diff` toolból jön.

Megkötések (a platformé, mérve — [docs/artifact-findings.md](docs/artifact-findings.md)):

- csak a **Claude appban**, a saját gépeden, tulajdonosként megy — böngészőben,
  telefonon a lap annyit ír ki, hogy az appban kell megnyitni;
- a `git-graph` MCP-nek a **Claude app configjában** kell lennie (az
  plugin hookja teszi be; a `claude mcp add` nem elég), és az app csak
  induláskor olvassa be;
- az első megnyitáskor az app engedélyt kér a `git-graph` szerverhez.

**Publikálás:** a lap csak sablon, így feltölteni csak akkor kell, ha a UI-kód
vagy a repó neve változik. A `gg --publish` egy headless `claude -p`-vel tölti
fel (az Artifact API-t csak a modell éri el): meglévőt frissít, ha nincs,
létrehozza, **változatlan lapnál nem tölt fel**. A `gg --serve` indításkor és új
repó regisztrálásakor minden ismert repóra (`~/.git-graph/repos.json` + a hook
repója) megteszi — így minden repónak van Artifactja. Egy feltöltés ~6 mp.
Ha létezik a `~/.git-graph/no-auto-publish` fájl, a szerver nem publikál
(fejlesztés közben, és a `gg --forget` után: csak a kézi `gg --publish` megy).
Futás közben is kapcsolható.

A repó **lokális** git configjában (`.git/config`, sosem commitolódik):

| Kulcs | Mi |
| --- | --- |
| `git-graph.artifact` | a közzétett oldal URL-je |
| `git-graph.artifactHash` | a publikált lap hashe (változatlanra nem tölt fel) |

Kézi URL-megadás: `gg --set-artifact <url>`.

## `--open`

| Parancs | Mit nyit |
| --- | --- |
| `gg --open` / `gg --open local` | a frissen generált helyi pillanatképet |
| `gg --open artifact` | az Artifactot — böngészőben élő adat nélkül, csak a figyelmeztetéssel |

Mindegyik a **rendszer böngészőjében** nyit. A Claude Artifact-ablakát külső
folyamat nem tudja vezérelni — azt a `/git-graph` nyitja meg.

## Uncommitted Changes

Ha a munkakönyvtárban van változás, a gráf tetején — a Git Graph mintájára —
megjelenik egy **ál-sor**: `Uncommitted Changes (3 fájl)`, üres karikával,
szaggatott vonallal a HEAD-re. A zárójelben az érintett fájlok száma — így a
panel kinyitása nélkül is látszik. Rákattintva ugyanaz a részletek-panel nyílik, mint egy
commitnál: fájlonkénti `+`/`−` a HEAD-hez képest, a követetlen fájlok pedig
`új` jelöléssel (számok nélkül — a diff nem látja őket).

Nem commit, ezért a fejléc számlálójába nem számít bele, és a szűrők sem rejtik
el. Élő módban magától megjelenik és tűnik el, ahogy szerkesztesz.

## Fájl-diff

A részletek-panel fájlsorai lenyithatók (a sorra kattintva — a fájlnév maga a
GitHub-link marad): alatta a fájl diffje, a Claude app diff-nézetének mintájára —
sorszám, `+`/`−`, a cserélt soroknál a megváltozott szavak erősebb háttérrel, a
hunkok közt „N változatlan sor”. Az Uncommitted sornál a HEAD-hez képesti diff,
követetlen fájlnál a teljes tartalom hozzáadottként. Ha a diff legalább 1000 px
széles (széles Artifact-ablak, Browser panel), **side-by-side** nézetre vált:
balra a régi, jobbra az új oldal, a cserélt sorok egymás mellett — átméretezéskor
magától, újratöltés nélkül.

A diff nincs a teljes adatban: a lap lenyitáskor kéri, fájlonként (`/diff`,
illetve az Artifactban a `file_diff` tool). A commitok diffje gyorstárazva, az
Uncommitted soré élőben frissül. Csak élő nézetben megy — a statikus
pillanatkép (`gg`) ezt kiírja. Egy fájlból legfeljebb 3000 sor látszik.

## GitHub-linkek

Ha az `origin` GitHub-repó, a lap a GitHubra linkel:

- **Issue / PR**: a commit-üzenetekben (sor, panel-cím, body) a `#12` és az
  `owner/repo#12` — a `/issues/12` a PR-ra is átirányít. A `C#1`-szerű szöveg
  és az URL-fragment (`lap.html#3`) nem lesz link.
- **Commit hash**: a sorban és a panelen a commit GitHub-oldala.
- **Fájlváltozás**: a panel fájllistájában a fájl diffje a commit-oldalon.

Élő módban a link a **rendszerböngészőben** nyílik: a Browser panel a saját
fülén nyitná meg, ezért a lap a szervernek küldi (`POST /open`), az pedig
`webbrowser.open`-nel nyitja. A szerver csak GitHub-URL-t és csak a saját
lapjáról (Origin = Host) fogad el.

A hash és a fájl csak **pusholt** commitnál link (az `origin` valamelyik ága
eléri) — a helyi commit a GitHubon 404 lenne. Más hoston (GitLab, …) nincs
linkesítés: ott a `#szám` mást jelent.

A linkek valódi `<a target="_blank">` elemek — az Artifact keretéből a Claude
app csak ezt engedi át (mérve: a `window.open` el sem jutott hozzá). A
fájl-diff horgonyát (`#diff-<sha256(út)>`) a Python számolja az adatba.

## Hogyan rajzol

A git saját lane-kiosztását követi: a commit abba a sávba ül, amelyik már rá
vár (a gyereke foglalta le); az első szülő viszi tovább a sávot, a további
(merge) szülők új vagy meglévő sávot kapnak. A vonal merge-nél rögtön a merge
commit alatt hajlik, leágazásnál közvetlenül a szülő fölött. Sávonként ciklikus
Git Graph-színek.
