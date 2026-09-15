# git-graph

Git Graph-szerű commit-gráf generátor: **bármelyik repóból** egyetlen önálló
HTML fájl, amit a Claude `/git-graph` parancsa Artifactként publikál. A VS Code
`mhutchie.git-graph` elrendezését követi.

Használat és felépítés: [README.md](README.md).

## Repó térkép

| Útvonal | Mi ez |
| --- | --- |
| `gitgraph` | a teljes eszköz egyetlen fájlban: git-adatgyűjtés + beágyazott HTML/CSS/JS sablon + élő szerver (`--serve`) + SessionStart hook (`--session-hook`) |
| `gg` | symlink a `gitgraph`-ra (rövid alias) |
| `install.sh` | symlinkek; `--live`: launchd agent + SessionStart hook a globális settingsbe |
| `commands/git-graph.md` | a `/git-graph` slash command (publikálás/frissítés) |
| `docs/artifact-findings.md` | **mérési napló**: mit tud és mit nem az Artifact platform |
| `docs/desktop-live.md` | **mérési napló**: miért a Browser panel + lokális szerver az élő út |
| `docs/mcp-plan.md` | terv az élő verzióhoz — jelenleg blokkolva |
| `probe/` | eldobható MCP-mérőeszköz a blokkoló újratesztelésére |

## Parancsok

```sh
./install.sh          # symlinkek felrakása (idempotens)
./install.sh --live   # + launchd agent (gg --serve) és SessionStart hook
gg --help             # a teljes súgó
gg                    # az aktuális repó → <repó>/.git-graph/index.html
gg --serve            # élő kiszolgálás a Claude Desktop Browser paneljének
gg --launch-config    # .claude/launch.json bejegyzés (preview_start git-graph)
python3 gitgraph …    # symlink nélkül, közvetlenül
```

Két üzemmód: a **statikus** fájl (megosztás, Artifact) és az **élő** szerver
(napi munka, a Browser panelen magától frissül). A sablon mindkettőt ugyanabból
a kódból adja — a `build(..., live=True)` kapcsolja be a pollozást.

Nincs teszt-suite és nincs build — egyfájlos stdlib script. Változtatás után az
ellenőrzés: `gg` futtatása több repón (eltérő sávszámmal, merge-ekkel), és a
generált HTML megnyitása. A JS-t a fájlból kivágva `node --check`-kel lehet
szintaxis-ellenőrizni. Az élő mód ellenőrzése: `gg --serve`, majd a lapon
`DATA.meta.dirty` figyelése egy fájl létrehozása után (újratöltés nélkül kell
változnia), és repóváltás a `~/.git-graph/current` átírásával.

## Konvenciók

- **Nyelv**: magyar — kommentek, doksi, commit-body, a generált UI feliratai.
  A táblázat-fejlécek (`Description / Date / Author / Commit`) viszont
  **angolul** maradnak: az a Git Graph felismerhető arca. A Graph oszlop
  fejléce ikon (a felirat feleslegesen szélesre nyomta az oszlopot).
- **Függőség**: kizárólag Python 3 stdlib. Ez szándékos — az eszköznek bárhol
  futnia kell, `pip install` nélkül. Ne hozz be libet.
- **Minden git-hívás olvas.** A script sosem módosít repót. Kivétel a
  `.git/info/exclude` és a `.git/config` `gitgraph.*` kulcsai — mindkettő
  lokális, sosem commitolódik —, valamint a `--launch-config`, ami
  `.claude/launch.json`-t ír: az **commitolható** fájl, ezért csak kifejezett
  kérésre fut, sosem mellékhatásként.
- **Verziókezelés**: SemVer, kézi `vX.Y.Z` tag, Conventional Commits.
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
- **A hook némán kilép**, ha a mappa nem repó vagy nem fut a szerver: egy
  SessionStart hook minden sessionben lefut, zajt nem csinálhat.
- **A kimenet mindig `<repó>/.git-graph/index.html`** — ez stabil szerződés az
  Artifact-frissítéssel. Ne tedd konfigurálhatóvá a default helyet.

Részletes platform-tanulságok (CSP, capabilities, MCP): `docs/artifact-findings.md`.
