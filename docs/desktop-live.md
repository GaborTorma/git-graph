# Élő gráf a Claude Desktopban — mérési napló

Mérés dátuma: **2026-09-15**, Claude Desktop **1.52386.6**, Claude Code CLI
**2.1.195**, Artifact runtime contract **0.2.49**, macOS.

A kérdés: hogyan jelenjen meg a commit-gráf **egyetlen gombnyomásra** — úgy,
ahogy a terminál- vagy az Artifact-panel —, **friss tartalommal**, és **anélkül,
hogy parancsot kellene írni a chatbe**.

## Mérések

| Amit próbáltam | Eredmény |
| --- | --- |
| Browser panel, `file://` a repóból | megnyílik, a JS fut — de **`data:` origin**, azaz beágyazott pillanatkép; a fájl felülírása után 4 mp-cel sem töltött újra |
| Browser panel, `http://127.0.0.1:7788` | **valódi http origin**; a lapról `fetch('/fingerprint')` **működik** (CSP-korlát nincs) |
| Kérésenkénti újragenerálás | működik: két kérés között `dirty: 2 → 1` |
| `.claude/launch.json`, csak `url` (parancs nélkül) | `preview_start` **rácsatlakozik** a futó szerverre: *„no process was started"* |
| `show_pane` paneltípusok | `diff / file / terminal / pr / tasks / plan` — **nincs** web/artifact panel |
| Artifact capability-lista | bővült: `artifact, assets, db, downloads, mcp, room, sample, self` (0.2.23-kor az `assets` még `unavailable_to_account` volt) |

A desktop app csomagjában megtalálható a Browser panel felhasználói felülete is:
URL-sáv (`userUrlBar`), tabok (`openPreviewTab`, `reopenClosedPreviewTab`),
pin-elt tab, Show/Hide Browser kapcsoló. Ez a keresett „gomb".

## Amit ebből eldöntöttem

**Az Artifact nem lehet az élő felület.** A publikálás session-oldali eszköz —
mindig chat-parancs kell hozzá —, a kimenet pedig pillanatkép. Az Artifact
marad annak, amire való: **megosztható** gráf (`/git-graph`).

**A `docs/mcp-plan.md` B változata (tunnel + egyéni konnektor) okafogyott.**
Az ottani kerülőút csak azért kellett volna, mert az Artifact lapja nem ér el
lokális adatot. A Browser panel viszont sima böngésző: a lap a loopbackot
közvetlenül pollozhatja. Nem kell repó-olvasó szolgáltatást az internetre tenni.

## A megvalósult architektúra

```
launchd agent ──> gg --serve (127.0.0.1:7788)
                     │   /            friss HTML
                     │   /data        friss adat (~300 KB egy 210 commitos repón)
                     │   /fingerprint HEAD + refek hash + dirty (173 B, ~66 ms)
                     │
   ~/.git-graph/current ◄── SessionStart hook (gg --session-hook)
                     │        a session repóját írja be
                     ▼
       Claude Desktop Browser panel ── 2 mp-enként fingerprint,
                                       változásra /data + helyben újrarajzol
```

Mért számok egy 210 commitos repón: `/fingerprint` 173 B / ~66 ms,
`/data` 316 KB / ~630 ms. Ezért két külön végpont: a pollozás olcsó, a drága
átvitel csak tényleges változáskor történik.

## Ellenőrzött viselkedés

- a lapon `dirty` 1 → 2 **újratöltés nélkül**, a fájl létrehozása után ~2 mp-cel
- repóváltás a `current` fájlon át: a panel átvált (cím, repónév, 210 sor),
  a fejléc és az ág-lista is követi
- a statikus `gg` kimenet változatlanul működik (`LIVE = false`, nincs pollozás)

## Amit az első éles nap kihozott

Két hiba jött elő, mindkettő a több-session használatból, illetve valós
commit-szövegből:

- **Rossz repó a panelen.** A repót eleinte egyetlen globális fájl
  (`~/.git-graph/current`) mondta meg, amit minden session indulása felülírt —
  több nyitott session mellett a panel véletlenszerűen váltogatott. Javítás: a
  repó a kérés URL-jébe került (`/?repo=…`), a hook ezt az URL-t adja át; a
  `current` csak tartalék a paraméter nélküli `/`-hez. Mérve: két panel,
  `git-graph` (2 sor) és `varazskez` (78 sor) egyszerre, több poll-cikluson át
  megmaradt a sajátjánál.
- **Szétesett lap.** A `varazskez` repó egyik commit-üzenete tartalmazza a
  `</script>` karakterláncot (*„JSON-LD </script>-escape"*) — ez a beágyazott
  `DATA`-ban korán lezárta a script blokkot, és a maradék JSON szövegként ömlött
  a lapra. Javítás: `embed()` — `</` → `<\/` és U+2028/29 escape. A generált
  oldalon ellenőrizve: pontosan egy `<script>`/`</script>` pár marad.

## A launch config és a hostnév-trükk

A `.claude/launch.json` bejegyzésével a panel **névvel** indítható
(`preview_start name="git-graph"`), URL begépelése nélkül. A query viszont nem
fér bele:

```
'url' is 'http://127.0.0.1:7788/?repo=…', a localhost address with a path or
query…  A localhost "url" must be just the server's origin
```

A hibaüzenet saját példája (`http://app.localhost:3000`) mutatta az utat: a
**hostnév** szabad. Mérve, hogy a panel Chromiumja a `*.localhost` neveket a
loopbackra oldja (`http://teszt-szlag.localhost:7788` → a szerverünk válaszolt),
így a repó a hostnévbe költözött: `<mappanév>-<útvonal-hash>.localhost`. A
szerver a `Host` fejlécből és a `~/.git-graph/repos.json` regiszterből azonosít;
ismeretlen slugra 503 + „futtasd a repóban: gg --launch-config".

Amit még megmértem a launch config körül:

- **`.claude/launch.d/` drop-in**: a csomag szerint ide „bootoló scriptek" tehetnek
  egy-bejegyzéses JSON-t, hogy ne kelljen a felhasználó `launch.json`-jébe
  belenyúlni. Preview-bejegyzésre viszont **nem működik**: `launch.json` nélkül
  *„No .claude/launch.json found"*, mellette pedig a `preview_start <drop-in név>`
  a `launch.json` bejegyzését nyitotta meg, nem a drop-inét. Framebuffer-forrásokra
  való, nem erre.
- **`preview_start` nem CLI.** Claude eszköze; a terminálból nincs megfelelője.
  A gépelés nélküli út ezért marad a SessionStart hook, a kézi út pedig a Browser
  panel címsora (vagy `open <URL>` a rendszer böngészőjébe).

- **`index.lock`-ütközés.** A szerver kétmásodpercenként `git status`-t futtat,
  az pedig frissíti az indexet, tehát lockot vesz — egy `git commit` emiatt
  tényleg elhasalt („Unable to create index.lock"). Javítás: minden git-hívás
  `--no-optional-locks`-kal megy. Utána 20/20 gyors `git status` ment hiba nélkül
  a pollozás alatt.

## Nyitott, nem mért

Túléli-e a Browser-panel tabja az **új sessiont**. A csomagban van tab-perzisztencia
és pin, de ezt egy sessionből nem tudtam bizonyítani. A hook ettől függetlenül
megoldja: minden session indulásakor újra megnyittatja a panelt.
