# git-graph

Git Graph-szerű, élő commit-gráf **bármelyik repóból** — Artifactként a Claude
appban.
A gráf a VS Code [`mhutchie.git-graph`](https://marketplace.visualstudio.com/items?itemName=mhutchie.git-graph)
mintáját követi, a megjelenés a Claude appét: az app design-systemje (CDS, a fizzy-lake
téma: semleges szürkék, kék akcentus, az app ikonjai, Anthropic Sans és Mono), Claude Light /
Dark kódszínek, napokra bontott egysoros lista. A soron kattintva lefelé nyílik a
commit: szerző GitHub-avatarral, szülő(k), GitHub-link, fájlok és
szintaxisszínezett diff. A lenyitott commit kerek kártya: a sor hover-színéből nyílik (a
közepéről halványul, közben megjelenik a kerete), csukáskor a lenyitott fájljai vele együtt
csukódnak. Ha a helyi ág és a remote-ja ugyanott áll, egy
badge-ben látszanak, egyetlen felhő-és-ág ikonnal (az alapágé teli). Az ág-badge végén a távolságai,
csak a nem nulla irány: `↑a ↓b` az alapághoz (amire az `origin/HEAD` mutat —
mennyit jött az ág, mennyit haladt közben a main), `☁ ↑c ↓d` a saját, azonos nevű
upstreamjéhez (ha nem egy helyen állnak; a más nevű upstream, pl. az `origin/main`-ből
indított branché, nem számít: `-u`-val pusholva a saját remote branche lesz az); a csak remote-os ág badge-én utolsóként `⑂ ↑e ↓f` a
helyi párjához. Ha az alapág helyi párja (`main`) előrébb jár a remote-jánál, a
`☁ ↑` szakasz piros (a `main`-en nem dolgozunk, ez anomália): a halvány chipen halvány
piros, piros kerettel, a teli chipen teli piros. Közös ős nélküli ágon (pl. egy `git subtree push` remote-ja) a távolság helyén
áthúzott lánc áll, a commitjai (a fő történet tükrei) halványak, és szaggatott ív köti
őket a forrásukhoz ([Subtree-remote](docs/subtree-remote.md)). Ha a badge nem fér ki, csak a név
rövidül.

**Fejléc** ([Fejléc](docs/header.md)): a repó neve és a HEAD-chip mellett az ágválasztó, a keresés
és a fájlok gombja, az app ghost gombjai. Az ágválasztó gombja a kijelölést mutatja (legfeljebb 3
név, utána ikonok, `+N`), kijelölésnél x-szel; a menü végén remote-onként egy kapcsoló rejti el a
remote ágait. A keresés (⌘F) lenyílik a mezővel és a „Csak ref-es commitok” kapcsolóval; az
üzenetben, a szerzőben, a ref-nevekben és a hash elején keres, ékezettől függetlenül. Szűrve a
gomb kiírja a szűrést, az x mindkét szűrőt törli.

A részletek-panel fájlsorain a fájl előtt a típusa ikonja áll, utána a `+`/`−` számok; a
sor lenyitva a diffet mutatja ([Fájl-diff](docs/file-diff.md)). Az ikonok a
[Catppuccin VS Code-ikonjai](https://github.com/catppuccin/vscode-icons) (MIT),
a lap színeire hangolva. Frissítés: `python3 scripts/file-icons.py`.

A `git-graph` parancs a Claude Bash eszközének szól (a plugin `bin/`-jéből), nem a
terminálnak — a skillek és a hook ezt hívják:

```sh
git-graph --publish          # az Artifact publikálásának lépései a sessionnek
git-graph --published <URL>  # a session publikálása után: URL + hash a .git/config-ba
git-graph --mcp              # MCP szerver a Claude appnak (az app indítja, nem kézzel)
git-graph --artifacts        # az ismert repók Artifactjai (<repó>\t<URL>)
git-graph --forget           # a repó git-graph nyomai törlése (az Artifactot nem törli)
```

## Telepítés

Claude Code plugin, saját marketplace-szel (maga ez a repó):

```sh
claude plugin marketplace add GaborTorma/git-graph
claude plugin install git-graph@git-graph
```

A plugin hozza a modot (a `/git-graph` commanddal), a `/git-graph:forget-artifact`
skillt, a SessionStart hookot, és a Claude
Bash eszközének PATH-jára a `git-graph` parancsot. Függősége
nincs a Python 3 stdliben túl (a lap a Mermaid vendorolt buildjét hozza, a
markdown-diff diagramjaihoz); minden git-hívás **csak olvas**. Hálózatra csak
a szerzők GitHub-avatarjáért megy, GitHub-os repónál, gyorstárazva.

A pluginnak nincs telepítési eseménye, ezért a gépi részt az **első session
hookja** állítja be — és minden verzióváltáskor frissíti (idempotens, csak
változáskor ír):

- `~/.git-graph/bin/git-graph` — a kód stabil másolata (a `git_graph` csomag
  egyetlen futtatható zipben). A plugin útvonala verziónként más, az app ezt futtatja.
- `~/Library/Application Support/Claude/claude_desktop_config.json` → `git-graph`
  MCP szerver (előtte mentés). Az app csak induláskor olvassa: ilyenkor a
  session szól, hogy **egyszer újra kell indítani**.
- `~/.claude/settings.json` → `permissions.additionalDirectories` += `~/.git-graph`
  (előtte mentés). A session innen publikálja az Artifact lapját, és csak olyan fájlt
  csatolhat, amelyet olvashat.

**Eltávolítás:** két lépés.

1. `/git-graph:forget-artifact` egy sessionben, **Mind** választással — törli az Artifactokat (a `git-graph --artifacts`
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

A plugin **modja** a session indulásakor, a modell nélkül a repó Artifactját nézi:

- ha **naprakész**, megnyitja;
- ha **még nincs**, vagy a lapja **elavult** (a git-graph frissült, vagy a
  capability-lista, a contract változott — a lap hashe eltér a
  `git-graph.artifactHash`-től), előbb publikálja, aztán megnyitja.

**Worktree-k:** repónként egy Artifact van, a worktree-k közösen látják (a fő
checkout slugján). A „saját” worktree az előtérben lévő sessioné: a lap a
Claude app naplójából és session-adataiból tudja, melyik session van épp elöl,
és session-váltáskor prompt nélkül, ~50 ms alatt átáll. Kézzel nem választható
— a HEAD ott van, ahol a session dolgozik. A fejléc chipje a saját ágat mutatja
a sávja színében; worktree-ben a worktree-jellel (mappa) és az ág
távolságaival. Rákattintva a lista a HEAD commitjához ugrik; ha az ágválasztó elrejti a HEAD-et, a chip
halványabb, és a kattintás előbb minden ágra áll vissza. Az ágválasztóban választva a lista a
kijelölés legfelső csúcsához ugrik. A saját worktree „Nem
commitolt változások” sora a lista fölötti sávban ül (nem mai időnél a nappal),
a többi worktree-é a listában, az ideje szerint, a worktree jelével és ágával. Minden worktree HEAD-je
badge-et kap, elöl a worktree jelével (a fő checkouté az üres mappa, ha vannak worktree-k);
leválasztott HEAD-nél az ág helyén lánc-ikon áll (`worktree-név | ⛓`, a fő checkouté `main | ⛓`,
worktree nélkül `⛓ HEAD`; a fejléc chipjén a lánc és a rövid hash), utána a HEAD-commit távolsága
az alapágtól, mint az ágaké; a saját commit és WIP nélküli worktree-k csonkkal ágaznak le a
commitjukról, több csonk legyezőszerűen. Ami nem a sajáté, halványabb (a sehol ki nem
vett ágak a fő checkouté). Az ágválasztó worktree-nként csoportosít: fejléc (a
sajáté a fejléc chipjének színével), alatta az ágai — amelyikben utoljára ki volt
véve, a worktree HEAD-reflogja szerint —, a gazdátlanok utánuk, a remote-ok (fejléc kapcsolóval, alatta a csak remote ágak) a
végén. A menü a lap magasságának ~80 %-áig nyúlhat le. A helyi ág és az azonos nevű upstreamje egy opció (ha egy helyen állnak, egy sor a közös
felhő-és-ág ikonnal, különben egymás alatt az ág és a felhő): a sorra kattintva mindkettő kijelölődik, egy kipipált sor pipájára
kattintva csak az kerül ki; ha semmi sem marad, újra minden ág látszik. A worktree
fejlécére kattintva az összes ága kijelölődik; a gomb a kijelölést mutatja
([Fejléc](docs/header.md)). HEAD worktree-nként; worktree nélkül csak az ágak. A menü
tetején szűrő: ág- vagy worktree-név szerint szűkít (a worktree nevére az összes
ága), a worktree-fejléc csak akkor marad, ha alatta
legalább egy ág látszik; az Enter az első találatot választja.

A hook némán kilép, ha a mappa nem git repó; headless (`-p`, SDK) sessionben a mod
nem lép. Az „off kapcsoló" a plugin kikapcsolása
(`claude plugin disable git-graph@git-graph`), vagy a lap fogaskerék-menüje: az
**Automatikus megnyitás** repónként (`git-graph.autoOpen`; ha be van kapcsolva,
az elavult lapot is frissíti), az **Automatikus publikálás** a gépen, minden
repóra (`~/.git-graph/settings.json`: Artifact nélküli repóban a mod létrehozza-e). Mindkettő alapból be van kapcsolva; a `git-graph --forget` a
repóét kikapcsolja.

## Felépítés

| Útvonal | Mi |
| --- | --- |
| `bin/git-graph` | a `git-graph` parancs: a `git_graph` csomag belépője |
| `git_graph/` | a Python-oldal modulokra bontva: adatgyűjtés, diff, MCP szerver, publikálás, hook, telepítés |
| `page/` | a lap: az Artifact betöltője (`loader.html`) és az élő kód (HTML, CSS, JS), amit a szerver ad |
| `tests/` | modulonkénti tesztek és füstteszt az MCP szerverre (stdlib `unittest`) |
| `.claude-plugin/plugin.json` | a plugin manifestje — a verzió egyetlen forrása |
| `.claude-plugin/marketplace.json` | a `git-graph` marketplace (egyetlen plugin: ez a repó) |
| `hooks/hooks.json` | SessionStart hook: `git-graph --session-hook` (telepít, regisztrál); és a mod (publikál, megnyit) |
| `hooks/register.ts` | a plugin modja: az Artifactot a modell nélkül publikálja, ha kell, és megnyitja — a session indulásakor és a `/git-graph` commandra |
| `skills/forget-artifact/SKILL.md` | `/git-graph:forget-artifact`: az aktuális vagy az összes repó Artifactjának törlése + `git-graph --forget` (választás; eltávolítás előtt: mind) |

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
(`callTool("host:git-graph", …)`): mindig egy nyitva tartott `changes`-hívás
vár, és a szerver akkor válaszol, ha a repó (refek, HEAD, munkakönyvtár) vagy az
előtérben lévő session megváltozik — git-műveletnél ~50 ms, fájlszerkesztésnél
legfeljebb ~2 s alatt —, és csak változáskor jön a teljes `graph_data`
(150–300 ms). A lábléc kiírja a mért időket. Egy lenyitott fájl diffje a `file_diff` toolból jön.

Megkötések (a platformé, mérve — [host-bridge-limits](.claude/memory/host-bridge-limits.md)):

- csak a **Claude appban**, a saját gépeden, tulajdonosként megy — böngészőben,
  telefonon a lap annyit ír ki, hogy az appban kell megnyitni;
- a `git-graph` MCP-nek a **Claude app configjában** kell lennie (az
  plugin hookja teszi be; a `claude mcp add` nem elég), és az app csak
  induláskor olvassa be;
- az első megnyitáskor az app engedélyt kér a `git-graph` szerverhez.

**Publikálás:** a lap csak betöltő, így feltölteni csak akkor kell, ha maga a
betöltő vagy a repó neve változik. Egy plugin-frissítés után a gépen futó
git-graph percen belül magától frissül, a lap újratölt — app-újraindítás sem kell. A
publikálást és a megnyitást a plugin **modja** végzi, a modell nélkül, a session indulásakor
(Claude Code 2.1.321 óta; `git-graph --mod-plan` dönt, sessionönként egyszer):

- **Új vagy elavult lap** (változott a betöltő, a capability-lista vagy a contract): `Artifact`
  `read` a meglévőn, majd `Artifact` `publish` a lappal, a teljes `host:git-graph`
  capability-listával és a rögzített runtime-contracttal (`PUBLISH_CONTRACT`, minden lapon
  ugyanaz), végül `git-graph --published <URL>`, ami az URL-t, a lap és a deklaráció hashét
  visszaírja.
- **Utána, és naprakész lapnál**: `Artifact` `open`, és előhozza a panelt.

Kézzel ugyanezt a mod `/git-graph` commandja végzi, a beállításoktól függetlenül, akárhányszor:
publikál, ha kell (Artifact nélkül újat is), és megnyit.

Kikapcsolt automatikus megnyitásnál (`git-graph.autoOpen=false`, a `--forget`
is ezt írja) a mod a session indulásakor nem lép; a `/git-graph` ilyenkor is megnyitja. Új
Artifactot a mod magától csak bekapcsolt automatikus publikálásnál (a gép beállítása) hoz létre;
a `/git-graph`-é bekapcsolt megnyitással indul.

A repó **lokális** git configjában (`.git/config`, sosem commitolódik):

| Kulcs | Mi |
| --- | --- |
| `git-graph.artifact` | a közzétett oldal URL-je |
| `git-graph.artifactHash` | a publikált lap hashe (változatlanra nem tölt fel) |
| `git-graph.autoOpen` | `false`: a session indulásakor a lap nem nyílik meg, és nem frissül (a lap beállítás-menüje és a `--forget` írja, az új Artifact `--published`-je törli) |

Kézi URL-megadás: `git-graph --set-artifact <url>`.

## Billentyűk

| Billentyű | Commiton | Fájlon |
| --- | --- | --- |
| `↑` / `↓` | kijelölés az előző / következő commitra (nem nyit) | előző / következő fájl; az elsőről fel a commitra, az utolsó (bezárt) fájlsorról le az alatta lévő commitra |
| `→` | kinyitja a commitot, és belép a fájljaiba | kinyitja a diffet (vagy ha már nyitva van) és az első blokkra lép |
| `←` | becsukja a commitot | nyitott diffet becsuk (blokkon is); bezárt fájlon vissza a commitra |
| `⌘` / `Ctrl` + `↓` / `↑` | szülő / gyerek ugyanazon az ágon | |
| `⇧⌘` / `⇧Ctrl` + `↓` / `↑` | merge-nél a beolvasztott ág (második szülő), visszafelé a merge | |
| `H` | kijelölés a saját worktree HEAD-jén | |
| `⇧↑` / `⇧↓` | csak görget (három diff-sornyit), a kijelölés marad | ugyanígy — egy hosszú blokk olvasásához |
| `Esc` | előbb a keresett szöveget üríti (a ref-szűrő marad), aztán a nyitott commitot csukja | ugyanígy |
| `Esc` (teljes képernyőn) | szerkesztés közben a szerkesztést fejezi be, a kereső mezőben a keresést törli, különben bezárja a teljes képernyőt | |
| `⌘F` / `Ctrl+F` | a keresés popupja, a fókusz a mezőben | |

Fájlon a `→` kinyitja a diffet, és rögtön az első módosított blokkra lép (egy blokk a
`···` elválasztóig tart); `↓` vagy `→` a következő blokkra, az utolsó után a következő fájlra, `↑`-ra visszafelé,
`←`-re bezárja a fájlt. A görgő egy kattanása egy commitot lép.

## Nem commitolt változások

Ha a munkakönyvtárban van változás, a Git Graph mintájára megjelenik egy
**ál-sor**: *Nem commitolt változások*, üres karikával, szaggatott vonallal a
HEAD-re. Ha van stage-elt változás, alatta egy második ál-sor, *Stage-elt
változások*: a felső a még nem stage-elt (az indexhez képest), az alsó a stage-elt
(a HEAD-hez képest) változásokat mutatja, láncban a HEAD-re kötve. Worktree-nként
külön, mindegyik a saját HEAD-jére kötve. A sor végén,
mint a commitoknál: az idő (a fájlok utolsó módosítása), a gép git-felhasználója
és a diff. A saját worktree-é a lista fölötti sávban ül; a többié a listában, az
ideje szerinti helyen (sosem a HEAD-je alatt), elöl a worktree chipjével.
Rákattintva ugyanaz a részletek-panel nyílik, mint egy commitnál: fájlonkénti
`+`/`−`, a követetlen fájlok pedig `új` jelöléssel (számok
nélkül — a diff nem látja őket).

Nem commit, ezért a fejléc számlálójába nem számít bele; ágszűrésnél csak annak
a worktree-nek a sora látszik, amelyikben a szűrt ág van kivéve. Élő módban magától megjelenik és tűnik el, ahogy szerkesztesz.

## Fájl-diff

A részletek-panel fájlsorai lenyithatók: alatta a fájl diffje (szöveg, renderelt markdown,
kép), széles ablakban side-by-side. Részletek és követelmények:
[docs/file-diff.md](docs/file-diff.md).

A kóddiffet a CodeMirror rajzolja; az Uncommitted sor és a saját worktree HEAD-commitjának
fájljai dupla kattintással szerkeszthetők, a mentés automatikus, a lemez közbeni változása
befésülődik. A HEAD-commit kóddiffje a lemez szövegét mutatja, a nem commitolt eltérések kék /
narancs rétegben: [docs/code-diff.md](docs/code-diff.md).

## Fájlfa és teljes nézet

Az eszközsor jobb szélső gombja a gráf mellé nyitja a fájlfát (a lenyitott commit fájljai,
commit nélkül a worktree állapota); a fájlfejléc ikonja a fájlt teljes képernyőn nyitja: középen a
diff, jobbra a fa (diff-szűrő, név- és tartalomkereső) és a commitlista, amelyen commit váltható:
[docs/full-view.md](docs/full-view.md).

A funkcióoldalak listája:
[docs/README.md](docs/README.md). A funkcióoldalak képei a lap tesztjeinek fixture-repóiból
készülnek, újragenerálhatóan:

```sh
uv run --no-project --with playwright==1.63.0 python scripts/screenshots.py
```

## GitHub-linkek

Ha az `origin` GitHub-repó, a lap a GitHubra linkel:

- **Issue / PR**: a commit-üzenetekben (sor, panel-cím, body) a `#12` és az
  `owner/repo#12` — a `/issues/12` a PR-ra is átirányít. A `C#1`-szerű szöveg
  és az URL-fragment (`lap.html#3`) nem lesz link.
- **Commit hash**: a kinyitott commit fejében, mellette megnyitás- és másolás-ikon.
- **Fájlváltozás**: a fájlnév utáni megnyitás-ikon a fájl diffje a commit-oldalon
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

A **merge-commit** pöttye telt mag gyűrűvel. A beolvasztott commitjai alapból alá csukódnak
(a ref-es commitok maguk látszanak, alattuk szaggatott él); a pötty mellett `+N` áll, a merge
gráfoszlopára kattintva animálva kibomlik. A fogaskerék-menü „Merge-ek összecsukása” kapcsolója
repónként állítja az alapot ([Merge-ek összecsukása](docs/merge-collapse.md)).

A **friss commitok** pöttye körül halvány gyűrű van, az üzenetük a gyűrű (a
sáv) színét kapja. Friss a legújabb commit és a vele egy sorozatban készültek:
visszafelé addig, amíg két szomszéd között legfeljebb 10 mp telt el — minden
ágon, a committer-idő szerint (`--amend`, rebase is frissít). A kiemelés 5
percig tart; egy újabb sorozat leváltja az előzőt.
