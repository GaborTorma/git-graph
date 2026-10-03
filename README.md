# git-graph

Git Graph-szerű, élő commit-gráf **bármelyik repóból** — Artifactként a Claude
appban.
A gráf a VS Code [`mhutchie.git-graph`](https://marketplace.visualstudio.com/items?itemName=mhutchie.git-graph)
mintáját követi, a megjelenés a Claude appét: meleg paletta, Claude Light / Dark
kódszínek, napokra bontott egysoros lista. A soron kattintva lefelé nyílik a
commit: szerző GitHub-avatarral, szülő(k), GitHub-link, fájlok és
szintaxisszínezett diff. Ha a helyi ág és a remote-ja ugyanott áll, egy
badge-ben látszanak (`main | origin`). A kereső (⌘F) az üzenetben, a
szerzőben, a ref-nevekben és a hash elején keres, ékezettől függetlenül;
minden szónak egyeznie kell. Escape vagy a mező × gombja törli; ha közben nyitva
volt egy commit, a teljes listában az kerül legfelülre.

A `git-graph` parancs a Claude Bash eszközének szól (a plugin `bin/`-jéből), nem a
terminálnak — a skillek és a hook ezt hívják:

```sh
git-graph --publish          # az Artifact publikálásának lépései a sessionnek
git-graph --published <URL>  # a session publikálása után: URL + hash a .git/config-ba
git-graph --mcp              # MCP szerver a Claude appnak (az app indítja, nem kézzel)
git-graph --artifacts        # az ismert repók Artifactjai (<repó>\t<URL>)
git-graph --forget           # a repó git-graph nyomai törlése (az Artifactot nem törli)
git-graph --forget-artifact <URL>  # egyetlen Artifact nyomai (egy megszűnt worktree-é)
```

## Telepítés

Claude Code plugin, saját marketplace-szel (maga ez a repó):

```sh
claude plugin marketplace add GaborTorma/git-graph
claude plugin install git-graph@git-graph
```

A plugin hozza a `/git-graph:artifact` skillt, a SessionStart hookot, és a Claude
Bash eszközének PATH-jára a `git-graph` parancsot. Függősége
nincs a Python 3 stdliben túl; minden git-hívás **csak olvas**. Hálózatra csak
a szerzők GitHub-avatarjáért megy, GitHub-os repónál, gyorstárazva.

A pluginnak nincs telepítési eseménye, ezért a gépi részt az **első session
hookja** állítja be — és minden verzióváltáskor frissíti (idempotens, csak
változáskor ír):

- `~/.git-graph/bin/git-graph` — a script stabil másolata. A plugin útvonala
  verziónként más, az app ezt futtatja.
- `~/Library/Application Support/Claude/claude_desktop_config.json` → `git-graph`
  MCP szerver (előtte mentés). Az app csak induláskor olvassa: ilyenkor a
  session szól, hogy **egyszer újra kell indítani**.

**Eltávolítás:** két lépés.

1. `/git-graph:remove` egy sessionben — törli az Artifactokat (a `git-graph --artifacts`
   listája alapján, mindegyiket külön jóváhagyással), és repónként a `git-graph
   --forget`-tel a `git-graph.*` kulcsokat, a helyi lapokat és a
   regiszterbejegyzést. Közben kikapcsolja az automatikus publikálást, hogy a
   hook ne kérjen újat. Kihagyható: akkor az Artifactok és a
   kulcsok maradnak, és egy újratelepítés ugyanazokat éleszti újra.
2. `claude plugin uninstall git-graph@git-graph`. Az app által indított `git-graph
   --mcp` percenként megnézi a Claude Code nyilvántartását
   (`installed_plugins.json`), és ha a plugin két egymást követő ellenőrzésnél
   hiányzik, leszereli a fentieket — az MCP-bejegyzést és a `~/.git-graph`-ot. Olvashatatlan vagy ismeretlen formátumú
   nyilvántartásnál nem töröl semmit. Ha az app nem fut, a leszerelés a
   következő indulása után történik meg; az appot utána érdemes újraindítani.

**Verziózás:** SemVer, a verzió egyetlen forrása a
`.claude-plugin/plugin.json`. Bump nélkül a `claude plugin update` nem hoz le
semmit. Kiadás: `vX.Y.Z` tag.

Fejlesztés közben, bump nélkül: `claude --plugin-dir .` (csak az adott
sessionre). Ilyenkor a hook ugyanúgy telepít, de mivel a nyilvántartásban nincs
benne, a `git-graph --mcp` ~1 perc múlva leszerel — a következő session újra telepít.

## Élő nézet: az Artifact

A cél: **ne kelljen parancsot írni a chatbe**, mégis friss gráfot láss.

A **SessionStart hook** a session indulásakor a repó Artifactját nézi:

- ha **naprakész**, megkéri Claude-ot, hogy nyissa meg (`git-graph.artifact`);
- ha **még nincs**, vagy a lapja **elavult** (a git-graph frissült — a lap
  hashe eltér a `git-graph.artifactHash`-től), megkéri, hogy publikálja: a lap
  csak kódfrissítéskor változik, az pedig csak új sessionnel lép életbe — és
  ilyenkor először ez a hook fut.

**Worktree-k:** minden worktree saját Artifactot kap (saját slug, saját
Uncommitted sor). A hook az `EnterWorktree` / `ExitWorktree` után is lefut
(PostToolUse), így a session közben nyitott worktree is megkapja a magáét. A
megszűnt worktree-k Artifactjait a hook felismeri (a `git worktree list`-ben
már nincsenek), és megkéri Claude-ot, hogy törölje őket, majd
`git-graph --forget-artifact <URL>`-lel takarítsa a kulcsaikat — a `/worktree-close`-nak
ehhez nem kell tudnia a git-graph-ról.

A hook némán kilép, ha a mappa nem git repó; headless (`-p`, SDK) sessionben nem
kér publikálást. Az „off kapcsoló" a plugin kikapcsolása
(`claude plugin disable git-graph@git-graph`), vagy a publikálásé a
`~/.git-graph/no-auto-publish` fájl.

## Felépítés

| Útvonal | Mi |
| --- | --- |
| `bin/git-graph` | maga a script: adatgyűjtés + MCP szerver + telepítés |
| `page/` | a lap: az Artifact betöltője (`loader.html`) és az élő kód (HTML, CSS, JS), amit a szerver ad |
| `tests/` | füstteszt az MCP szerverre (stdlib `unittest`) |
| `.claude-plugin/plugin.json` | a plugin manifestje — a verzió egyetlen forrása |
| `.claude-plugin/marketplace.json` | a `git-graph` marketplace (egyetlen plugin: ez a repó) |
| `hooks/hooks.json` | SessionStart és worktree-váltás (PostToolUse) hook: `git-graph --session-hook` (telepít + megnyittatja vagy publikáltatja a gráfot + az árva worktree-Artifactokat töröltet) |
| `skills/artifact/SKILL.md` | `/git-graph:artifact`: `git-graph --publish`, és publikálja vagy megnyitja az Artifactot |
| `skills/remove/SKILL.md` | `/git-graph:remove`: az Artifactok törlése és a repók kitakarítása az eltávolítás előtt |
| `docs/artifact-findings.md` | **mit tud és mit nem az Artifact platform** — mérésekkel |
| `docs/desktop-live.md` | a korábbi Browser panel-út mérései (a `host:` híd óta nem használt) |
| `docs/mcp-plan.md` | a korábbi terv az élő Artifacthoz (azóta a `host:` híddal megvalósult) |
| `probe/` | eldobható MCP-mérőeszköz a blokkoló újratesztelésére |

## Kimenet

A repón **kívülre**, `~/.git-graph/<slug>/` alá — a slug a mappanév és az
útvonal hashe; a lap ezzel kérdezi a `git-graph --mcp`-t (`~/.git-graph/repos.json`):

| Fájl | Mi |
| --- | --- |
| `artifact.html` | az Artifact betöltője — adat és kód nélkül, ezt publikálja a session |

A projektmappába nem kerül semmi.

## Artifact

Az Artifact **élő**, de sem adatot, sem kódot nem tárol: egy betöltő, amely a
Claude appban megnyitva a lap kódját (`page_code`) és az adatot is a gépeden
futó `git-graph --mcp`-ből kéri, az app **host-hídján** át
(`callTool("host:git-graph", …)`): 2 mp-enként az olcsó `fingerprint` (refek, HEAD, munkakönyvtár — ~40 ms), és
csak változáskor a teljes `graph_data` (150–300 ms). A lábléc kiírja a mért
időket. Egy lenyitott fájl diffje a `file_diff` toolból jön.

Megkötések (a platformé, mérve — [docs/artifact-findings.md](docs/artifact-findings.md)):

- csak a **Claude appban**, a saját gépeden, tulajdonosként megy — böngészőben,
  telefonon a lap annyit ír ki, hogy az appban kell megnyitni;
- a `git-graph` MCP-nek a **Claude app configjában** kell lennie (az
  plugin hookja teszi be; a `claude mcp add` nem elég), és az app csak
  induláskor olvassa be;
- az első megnyitáskor az app engedélyt kér a `git-graph` szerverhez.

**Publikálás:** a lap csak betöltő, így feltölteni csak akkor kell, ha maga a
betöltő vagy a repó neve változik. Egy plugin-frissítés után a gépen futó
git-graph percen belül magától frissül, a lap újratölt — app-újraindítás sem kell. Az Artifact API-t csak a modell éri el, ezért a
**session** publikál: a hook (vagy a `/git-graph:artifact` skill a `git-graph --publish`-sal)
kiírja az `artifact.html`-t és a lépéseket — meglévő Artifactnál előbb `read`
(friss sessionből a platform különben elutasítja), majd `publish` a
`host:git-graph` capability-vel, végül `git-graph --published <URL>`, ami az URL-t és
a lap hashét visszaírja. Változatlan lapnál nincs teendő.
Ha létezik a `~/.git-graph/no-auto-publish` fájl, a hook nem kér publikálást
(a `git-graph --forget` után: csak a kézi `/git-graph:artifact` megy).

A repó **lokális** git configjában (`.git/config`, sosem commitolódik):

| Kulcs | Mi |
| --- | --- |
| `git-graph.artifact` | a közzétett oldal URL-je |
| `git-graph.artifactHash` | a publikált lap hashe (változatlanra nem tölt fel) |
| `git-graph.<slug>.artifact`, `….artifactHash` | ugyanez egy worktree-é — a worktree-k `.git/config`-ja közös |

Kézi URL-megadás: `git-graph --set-artifact <url>`.

## Billentyűk

| Billentyű | Commiton | Fájlon |
| --- | --- | --- |
| `↑` / `↓` | kijelölés az előző / következő commitra (nem nyit) | előző / következő fájl |
| `→` | kinyitja a commitot, és belép a fájljaiba | kinyitja a fájl diffjét |
| `←` | becsukja a commitot | nyitott diffet becsuk; bezárt fájlon vissza a commitra |
| `⌘` / `Ctrl` + `↓` / `↑` | szülő / gyerek ugyanazon az ágon | |
| `⇧⌘` / `⇧Ctrl` + `↓` / `↑` | merge-nél a beolvasztott ág (második szülő), visszafelé a merge | |
| `H` | kijelölés a HEAD-en | |
| `Esc` | előbb a keresést üríti, aztán a nyitott commitot csukja | ugyanígy |
| `⌘F` / `Ctrl+F` | kereső | |

Nyitott fájlon a `↓` belép a diffbe, és a módosított blokkokon lép (egy blokk a
`···` elválasztóig tart); az utolsó után a következő fájlra, `↑`-ra visszafelé,
`←`-re a fájlsorra. A görgő egy kattanása egy commitot lép.

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
széles (széles Artifact-ablak), **side-by-side** nézetre vált:
balra a régi, jobbra az új oldal, a cserélt sorok egymás mellett — átméretezéskor
magától, újratöltés nélkül.

A diff nincs a teljes adatban: a lap lenyitáskor kéri, fájlonként (a
`file_diff` toollal). A commitok diffje gyorstárazva, az
Uncommitted soré élőben frissül. Egy fájlból legfeljebb 3000 sor látszik.

## GitHub-linkek

Ha az `origin` GitHub-repó, a lap a GitHubra linkel:

- **Issue / PR**: a commit-üzenetekben (sor, panel-cím, body) a `#12` és az
  `owner/repo#12` — a `/issues/12` a PR-ra is átirányít. A `C#1`-szerű szöveg
  és az URL-fragment (`lap.html#3`) nem lesz link.
- **Commit hash**: a kinyitott commit fejében, mellette megnyitás- és másolás-ikon.
- **Fájlváltozás**: a fájlsor végén a megnyitás-ikon a fájl diffje a commit-oldalon
  (a soron kattintva helyben nyílik a diff).
- **Szülő**: a szülő-ikon melletti hash és megnyitás-ikon a gráfban a szülőre ugrik.

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
színek: a 0. sáv a Claude narancs, a többi vele egyező telítettségű. A vonal
annak a sávnak a színét viseli, amelyben a hossza nagy részén fut: a merge-vonal
a beolvasztott ágét, a leágazó a saját ágáét.

A **friss commitok** pöttye körül halvány gyűrű van, az üzenetük a gyűrű (a
sáv) színét kapja. Friss a legújabb commit és a vele egy sorozatban készültek:
visszafelé addig, amíg két szomszéd között legfeljebb 10 mp telt el — minden
ágon, a committer-idő szerint (`--amend`, rebase is frissít). A kiemelés 5
percig tart; egy újabb sorozat leváltja az előzőt.
