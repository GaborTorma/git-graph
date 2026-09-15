# git-graph

Git Graph-szerű commit-gráf **bármelyik repóból**, egyetlen önálló HTML fájlba.
A VS Code [`mhutchie.git-graph`](https://marketplace.visualstudio.com/items?itemName=mhutchie.git-graph)
elrendezését és Dark+/Light+ palettáját követi.

```sh
gg                    # az aktuális repó → <repó>/.git-graph/index.html
gg --open             # …és megnyitja (Artifactot, ha az aktuális; különben a helyi fájlt)
gg ~/dev/masik-repo   # másik repó
gg --limit 200        # csak az utolsó 200 commit (alap: mind)
gg --out graf.html    # máshova (relatív út a hívás helyéhez)
gg --serve            # élő kiszolgálás: http://127.0.0.1:7788
gg --launch-config    # .claude/launch.json bejegyzés a Browser panelhez
ggl                   # ugyanaz, rövidebben
```

Két üzemmód van, és más-más célra:

| | Statikus (`gg`) | Élő (`gg --serve`) |
| --- | --- | --- |
| Mi | egy önálló HTML fájl | loopback szerver, kérésenként újragenerál |
| Frissülés | kézi újrafuttatás | magától, ~2 mp-en belül |
| Hol nézed | böngésző / Artifact | a Claude Desktop **Browser panelje** |
| Mire jó | megosztás, archiválás | napi munka közben |

## Telepítés

```sh
./install.sh          # symlinkek
./install.sh --live   # + élő szerver (launchd) és SessionStart hook
```

Symlinkeli a `gitgraph`-ot és a `gg`-t a `~/.local/bin`-be, a slash commandot a
`~/.claude/commands`-ba. Idempotens. Függősége nincs a Python 3 stdliben túl;
minden git-hívás **csak olvas**.

A `--live` ezen felül:

- `~/Library/LaunchAgents/co.torma.gitgraph.plist` — a szervert a bejelentkezés
  indítja és életben tartja (`/usr/bin/python3`, napló: `~/.git-graph/serve.log`),
- `~/.claude/settings.json` → `SessionStart` hook (a saját bejegyzését ismeri fel,
  idegen hookhoz nem nyúl; a fájlról mentés készül).

Leszerelés: `./install.sh --uninstall-live` (a symlinkek maradnak).

## Élő mód a Claude Desktopban

A cél: **ne kelljen parancsot írni a chatbe**, mégis friss gráfot láss.

1. A `gg --serve` a loopbackon szolgál ki: `/` a friss HTML, `/data` a friss
   adat, `/fingerprint` egy pár száz bájtos ujjlenyomat (HEAD + refek hash-e +
   piszkos fájlok száma).
2. A lap kétmásodpercenként az **ujjlenyomatot** kéri, és csak tényleges
   változásra tölt `/data`-t — a nyitott commit-panel, a szűrők és a görgetés
   megmaradnak.
3. Melyik repót mutatja? Amit az URL mond: `http://<slug>.localhost:7788` — a
   **SessionStart hook** ezt az URL-t adja át (ugyanazt, amit a launch config
   is használ), így minden session panelje a **sajátját** mutatja akkor is, ha
   több session fut egyszerre. A szerver a `?repo=<útvonal>` alakot is érti
   (kézi használatra), paraméter és slug nélkül pedig a `~/.git-graph/current`
   a tartalék — azt szintén a hook írja.
4. A hook a session indulásakor megkéri Claude-ot, hogy nyissa meg a Browser
   panelt ezzel az URL-lel. Utána már csak a panel **Show/Hide Browser**
   kapcsolója kell.

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
(`.git/info/exclude`), ugyanúgy, mint a `.git-graph/` mappát. Ha a repó viszont
**már követi** a fájlt (mert van benne saját dev-szerver bejegyzés), nem nyúl
hozzá, csak figyelmeztet — ott neked kell eldöntened, mi legyen a sorával.

Nincs `launch.local.json`: mérve, a `.claude/launch.d/` drop-in mappa létezik
ugyan, de csak framebuffer (VNC) forrásokra — egy oda tett preview-bejegyzést a
`preview_start` nem talál meg. A lokális kizárás tehát az egyetlen jó válasz.

> A `preview_start` **nem parancssori program**, hanem Claude eszköze — a
> terminálból nem futtatható. Vagy a session hookja kéri meg rá Claude-ot
> (ez a normál út, nem kell gépelni semmit), vagy kézzel beilleszted a fenti
> URL-t a Browser panel címsorába. Rendszer-böngészőben: `open <URL>`.

A hook némán kilép, ha a mappa nem git repó, vagy ha a szerver nem fut — az
„off kapcsoló" tehát az agent leállítása (`./install.sh --uninstall-live`).

## Felépítés

| Útvonal | Mi |
| --- | --- |
| `gitgraph` | maga a script (~930 sor: adatgyűjtés + beágyazott HTML/CSS/JS sablon) |
| `gg` | symlink a `gitgraph`-ra — rövid alias |
| `ggl` | symlink a `gitgraph`-ra; ezen a néven a `--launch-config` a default |
| `install.sh` | symlinkek a PATH-ra és a Claude commands mappájába |
| `commands/git-graph.md` | `/git-graph` slash command: publikálja/frissíti az Artifact oldalt |
| `docs/artifact-findings.md` | **mit tud és mit nem az Artifact platform** — mérésekkel |
| `docs/desktop-live.md` | miért a Browser panel + lokális szerver az élő út — mérésekkel |
| `docs/mcp-plan.md` | terv az élő, magától frissülő verzióhoz (blokkolva, lásd findings) |
| `probe/` | eldobható MCP-mérőeszköz a blokkoló újratesztelésére |

## Kimenet

Mindig **ugyanoda**, a repón belülre: `<repó>/.git-graph/index.html`. Ez
szándékos — így ugyanabból a fájlból frissül ugyanaz az Artifact oldal.

A `.git-graph/` mappát a script a repó **lokális** ignore-listájába
(`.git/info/exclude`) veszi fel, nem a követett `.gitignore`-ba: az eszköz
idegen repókban is fut, ott pedig nem módosíthat commitolható fájlt.

## Artifact

A publikálás nem CLI — a Claude `/git-graph` parancsa végzi. A cím konvenció
szerint `<repónév> Git Graph` (a repónév az `origin` remote URL-jéből, mappanév
csak fallback). Ez alapján találja meg és **frissíti** a meglévő oldalt ahelyett,
hogy duplikátumot hozna létre. Repónként külön Artifact.

Publikálás után a parancs lefuttatja a `gg --set-artifact <url>`-t, ami a repó
**lokális** git configjába (`.git/config`, sosem commitolódik) elteszi:

| Kulcs | Mi |
| --- | --- |
| `gitgraph.artifact` | a közzétett oldal URL-je |
| `gitgraph.artifactHead` | a HEAD a publikálás pillanatában |

Ettől a `gg` minden futásnál kiírja a linket, és jelzi, ha azóta új commit jött
(`← ELAVULT`).

## `--open`

Az Artifact **pillanatkép**, a helyi fájl mindig friss — a `--open` ezért nem
vakon választ:

| Parancs | Mit nyit |
| --- | --- |
| `gg --open` | az Artifactot, **ha** az a mostani HEAD-et mutatja; különben a helyi fájlt |
| `gg --open artifact` | mindig az Artifactot (ha nincs megjegyezve, a helyit) |
| `gg --open local` | mindig a frissen generált helyi fájlt |

Mindegyik a **rendszer böngészőjében** nyit. A Claude Artifact-ablakát külső
folyamat nem tudja vezérelni — részletek és mérés: [docs/artifact-findings.md](docs/artifact-findings.md).

## Uncommitted Changes

Ha a munkakönyvtárban van változás, a gráf tetején — a Git Graph mintájára —
megjelenik egy **ál-sor**: `Uncommitted Changes (3 fájl)`, üres karikával,
szaggatott vonallal a HEAD-re. A zárójelben az érintett fájlok száma — így a
panel kinyitása nélkül is látszik. Rákattintva ugyanaz a részletek-panel nyílik, mint egy
commitnál: fájlonkénti `+`/`−` a HEAD-hez képest, a követetlen fájlok pedig
`új` jelöléssel (számok nélkül — a diff nem látja őket).

Nem commit, ezért a fejléc számlálójába nem számít bele, és a szűrők sem rejtik
el. Élő módban magától megjelenik és tűnik el, ahogy szerkesztesz.

## Hogyan rajzol

A git saját lane-kiosztását követi: a commit abba a sávba ül, amelyik már rá
vár (a gyereke foglalta le); az első szülő viszi tovább a sávot, a további
(merge) szülők új vagy meglévő sávot kapnak. A vonal merge-nél rögtön a merge
commit alatt hajlik, leágazásnál közvetlenül a szülő fölött. Sávonként ciklikus
Git Graph-színek.
