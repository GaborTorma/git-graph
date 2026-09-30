# Mit tud és mit nem az Artifact platform

Mérési napló. Minden állítás mögött **tényleges próbálkozás** áll, nem
dokumentáció-olvasás — a dokumentáció több ponton feltételes módban fogalmaz,
és egy helyen önmagával is feszül.

Mérés dátuma: **2026-08-25**, `gabor@torma.co.hu` fiók, Claude Desktop (macOS),
runtime contract **0.2.23**.

> **2026-09-15 — a kérdést megkerültük.** Az élő gráf azóta **nem** az Artifacton
> fut, hanem a Claude Desktop **Browser paneljében**, lokális szerverrel
> (`gg --serve`): ott nincs CSP-korlát, a lap közvetlenül pollozhat. Az alábbi
> mérések érvényben maradnak arra, amire szólnak — a **publikált Artifact**
> képességeire. Az élő út mérései: [desktop-live.md](desktop-live.md).
>
> Ami azóta változott: a contract **0.2.23 → 0.2.49**, és a fiók
> capability-listája bővült — `artifact, assets, db, downloads, mcp, room,
> sample, self`. Az `assets` tehát **már elérhető** (lásd lent: akkor nem volt).
> A `host:` MCP-t **nem mértem újra** — az élő úthoz nincs rá szükség.

## A kiinduló kérdés

A `gg` statikus HTML-t generál, amit a `/git-graph` Artifactként publikál. A cél
egy **magától frissülő** gráf lett volna: commitolsz → az Artifact-ablakban
átrajzol. Ehhez a lapnak friss adathoz kellene jutnia. Ez a napló azt rögzíti,
milyen utak vannak, és melyik járható.

## Eredmények

| Mechanizmus | Állapot | Bizonyíték |
| --- | --- | --- |
| Külső `fetch` / CDN / saját szerver | **blokkolva** | szigorú CSP, egyetlen kivétel a Google Fonts |
| `assets` → `_blob/{id}` relatív fájl | **nem elérhető** | `list_assets` → `unavailable_to_account` |
| `mcp` + `host:` (helyi MCP szerver) | **elutasítva** | deploy `422: capabilities.mcp: unavailable` |
| `mcp` + valódi claude.ai konnektor | **működik** | deploy átment `{"server":"Google Calendar",…}`-val |
| `artifact` (az oldal újrapublikálja magát) | **működik** | deploy átment |
| `downloads` | **működik** | deploy átment |

Elérhető képességek a fiókon: `artifact`, `downloads`, `mcp`, `self`.
Az `assets` **nincs** köztük.

## A `host:` ügy — a legfontosabb tanulság

A terv az volt, hogy egy helyi MCP szerver szolgáltatja a gráf-adatot, és a lap
`host:<név>`-vel hívja. Megépült (lásd [`../probe/`](../probe/)), regisztrálva
**mindkét** helyre, külön néven:

- `gg-probe-code` — `claude mcp add` (Claude Code), `✔ Connected`
- `gg-probe-app` — `~/Library/Application Support/Claude/claude_desktop_config.json`

Mindkettő **él és válaszol** — a sessionből hívva valós payloadot adnak. A
publikálás viszont következetesen elutasítja:

```
deploy 422: capabilities.mcp: unavailable — … If the reason concerns the
capability declaration itself, fix the declaration instead — upgrading
will not resolve it.
```

Három kontroll-mérés zárja ki a téves magyarázatokat:

1. `{"servers": []}` → **más** hiba (*„servers is empty"*) → az első nem alaki hiba
2. `{"server": "Google Calendar", …}` → **átmegy** → nem az egész `mcp` hiányzik
3. `contract: "latest"` → ugyanaz → nem contract-pin ügy (a hibaüzenet ezt ki is mondja)

Újratesztelve **Claude Desktop frissítés után** és az **„AI-powered artifacts"
kapcsoló bekapcsolása után** is: változatlan.

### A dokumentáció ellentmondása

A `mcp` capability leírása szerint a `server` lehet *„`host:<name>` for a local
MCP server on the viewer's device (Claude app only)"* — tehát elvileg **van**
ilyen mechanizmus. Ugyanennek a doksinak a konnektor-bekezdése viszont:

> Only claude.ai connectors are valid `server` values — the Claude app's own
> servers … and other locally-configured MCP servers in your tool list are not.

A típusdefiníció pedig kétszer is feltételes módban fogalmaz:

> „…**once the shell routes `host:` calls to the app**…"

Hogy „nincs még kiélesítve" vagy „elvileg sem érvényes", a doksiból **nem
dönthető el**. A gyakorlati következmény ugyanaz: nem használható.

## Az „AI-powered artifacts" kapcsoló

*claude.ai → Settings → Visuals → AI-powered artifacts.* Bekapcsolás előtt a
rendszer ezt mondta: *„Your connectors this session. **None are connected right
now.**"* Utána viszont felsorolta a tényleges konnektorokat (`visualize`,
`Vercel`, `neon`).

Tehát a kapcsoló **azt oldja fel, hogy egy publikált oldal elérje a claude.ai
konnektoraidat**. Az `assets`-et és a `host:`-ot **nem** érinti.

## Ami ebből következik

- **~~A `gg`-ből soha nem lesz Artifact-frissítés.~~** Megdőlt (2026-09-30):
  CLI-alparancs továbbra sincs, de egy headless `claude -p` publikálni tud —
  lásd lent: *Headless publikálás*. Ezen megy a `gg --publish` és a szerver
  háttér-publikálása.
- **A Claude Artifact-ablakát külső folyamat nem nyitja meg.** A `--open` a
  rendszer böngészőjében nyit. A panel útja a sessionön belülről a
  `/git-graph`, illetve a `ctrl+]`. (A beépített `/artifacts` lista `o`
  billentyűje is böngészőben nyit.)
- **Élő adat csak claude.ai konnektorból jöhet.** Git-gráfhoz ez GitHub
  konnektor lenne — de az csak a **felpusholt** állapotot látja, a lokális,
  pusholatlan commitokat nem. Alternatíva: a helyi MCP szervert tunnellel
  kitenni és **egyéni** claude.ai konnektorként felvenni — ez működne a lokális
  repóval is, de internetre tesz egy repó-olvasó szolgáltatást (token auth +
  repó-whitelist kötelező). Részletek: [mcp-plan.md](mcp-plan.md).
- **Nem mért, nyitott kérdés**: egy már nyitott Artifact-panel magától
  újrarajzol-e republish után — az `artifact` capability doksija szerint
  *„every open view … reloads to it"*, de ez az oldalról indított publishre
  van kimondva. (A korábbi (2) kérdésre a válasz: igen, lásd lent.)

## Headless publikálás (mérve, 2026-09-30, Claude Code 2.1.285)

Egy `claude -p` folyamat publikál; a végleges beállítás a `publish_page()`-ben.
Az út buktatói, sorrendben:

1. **A `-p "/git-graph"` nem fut le**: a slash command helyi parancsként nyelődik
   el (`num_turns: 0`). Promptként kell kérni.
2. **`-p` módban az Artifact tool alapból KI** (a kódban: `sdk_default_off`).
   Az opt-in: `CLAUDE_CODE_ARTIFACT=1`. Desktop session shelljéből nélküle is
   ment, mert onnan `CLAUDE_CODE_ENTRYPOINT=claude-desktop` öröklődik — tiszta
   (launchd, Terminal.app) környezetben nem. A modell saját toolkészletről adott
   válasza („Do you have Artifact?") megbízhatatlan — az init-esemény
   `tools` listája a mérvadó (`--output-format stream-json --verbose`).
3. **Friss sessionben az első publish elutasítás**, mert a session „nem látta"
   az élő verziót; a változatlan újraküldést is elutasítja. Megoldás: előbb
   `Artifact read`. (A skill-es út 6–10 kört futott emiatt.)
4. **Lassú indulás 444 toollal** (MCP-szerverek, claude.ai konnektorok). Karcsú:
   `--strict-mcp-config` + `ENABLE_CLAUDEAI_MCP_SERVERS=false` → ~30 tool;
   `--setting-sources project` → user-hookok és pluginok nélkül, init 0,3 s.
   A `--strict-mcp-config` egyedül az Artifact-ot is kivette; a `--tools`
   szűkítés MCP mellett ártott (`ToolSearch` nélkül minden MCP-séma betöltődött:
   lassabb, és cache-miss); `--tools Artifact` `Read` nélkül nem publikál (a
   publish a `Read` jogon át olvassa a fájlt).
5. **Az Artifact kapuja a policy-lekérdezés után nyílik** — karcsú indulásnál
   az init (0,4 s) előtt csak kb. 60%-ban. Sima `-p "<prompt>"`: 10-ből 6
   futás publikált. Megoldás: `--input-format stream-json`, hiányzó toolnál
   `interrupt` control-üzenet és újrakérdezés 0,3 s-onként UGYANABBAN a
   folyamatban (a kapu ~0,8 s-nál nyílt) — új folyamat újra zárt kapuval indul.
   A `CLAUDE_CODE_ARTIFACT=1` ezen nem segít.
6. **A modell csak végigolvasott fájlt publikál** („never distributes what it
   has not seen"), a `Read` ~25k token/hívás. Egy 180 ezer karakteres
   JSON-sort nem tudott elolvasni → nem publikált. Ezért a beágyazott adat
   soronként egy rekord, és nincs benne előre számolt link. Frissítéskor az
   élő változatot is végigolvassa (a merge-védelem miatt).

Időmérés, a `Published` tool-válaszig (a záró modellszöveget nem várjuk meg):

| Változat | Idő |
| --- | --- |
| skill-en át (`Invoke the git-graph skill`), 444 tool | 20–78 s |
| direkt prompt, 444 tool, Sonnet low | 7,5–11,5 s |
| **karcsú + stream-json + kapu-poll, Sonnet low (végleges)** | **5,6–6,2 s** (+3 s, ha a modell `Read`-del is beleolvas) |
| ugyanez, 165–200 KB-os lap létrehozása | ~18 s |
| ugyanez, 200 KB-os lap frissítése | ~50 s (mindkét példány végigolvasva) |
| meleg session (`--input-format stream-json`, folyamatosan futó claude) | 2,9–3,3 s |

A meleg session gyorsabb, de futó folyamatot és életciklust igényel; háttérben
publikálásnál a hideg is elég (senki nem vár rá). Egy tétlen meleg folyamat
~270 MB RAM, ~0,5% CPU.

Modellek (hideg, direkt prompt): a Sonnet 5.5 low a leggyorsabb megbízható; az
Opus 5.5 low 15 s körül; a Haiku 4.5 hasonló idő, de a skill-es úton 78 s-ig
is elhúzódott. A Sonnet `medium` effort nem gyorsabb, és többet `Read`-el.

## Implementációs tanulságok (a generátorból)

- **CSS osztálynév-ütközés**: a táblázat-fejléc `.head` szabálya ráült a
  `class="badge head"` elemre is → a HEAD-badge felvette a `display:grid` +
  `min-width:860px` + `text-transform:uppercase` értékeket, teljes szélességű
  sávvá nyúlt, és kinyomta a commit-üzenetet. Azóta a badge-variánsok `ref-*`
  névtérben, a fejléc `.thead`. **Tanulság**: rövid, generikus osztálynevek egy
  egyfájlos oldalon összeérnek.
- **Sticky fejléc görgetőkonténerben**: `overflow-x: auto` a szülőn az
  `overflow-y`-t is `auto`-vá teszi → a `position: sticky; top: 41px` a belső
  konténerhez tapadt, nem a laphoz, és az első sor fölé csúszott. Megoldás:
  VS Code-panel elrendezés (fix fejsáv + egyetlen görgethető régió).
- **`<meta charset="utf-8">` a fájl legelső sora**: enélkül a helyi
  `http.server`/`file://` latin-1-nek olvassa („beĂĄllĂ­tĂĄs"). A böngésző
  prescan az első 1024 bájtban keresi.
- **Repónév a remote-ból**, ne a mappanévből: a mappa `auto-bpm`, a repó
  `WristBPM`. `git remote get-url origin` → basename, `.git` levágva,
  mappanév-fallbackkel.
- **`listTools()` paraméter NÉLKÜL hívandó**, és `{servers: [{server,
  authStatus, tools}]}`-t ad — nem `{tools: […]}`-t. (Elsőre rosszul írtam meg;
  a típusdefiníció olvasása fogta meg.)
- **MCP Python SDK 2.x**: a `FastMCP` **`MCPServer`** néven él tovább
  (`from mcp.server.mcpserver import MCPServer`). Az 1.x import
  `ModuleNotFoundError`-t ad migrációs üzenettel.
- **MCP `tools/call` válasz-alak**: a `content[0].text` egy **JSON string**,
  `structuredContent` nincs. A capability `result.payload`-ja ezt parse-olja —
  a lapon `payload`-ot kell olvasni, nem `content`-et túrni.
- **GUI-ból indított MCP szerver**: abszolút python-út kell (a venv-é), mert az
  app PATH-ja minimális. Ellenőrizve `PATH=/usr/bin:/bin`-nel.
- **`watchTool` `refetchInterval` ~30 másodpercre padlózott** — „másodpercenkénti
  élő" nem lesz belőle.
