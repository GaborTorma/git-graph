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
>
> **2026-09-30 — a `host:` híd MŰKÖDIK** (contract **0.2.66**). A `probe/`
> újramérve: a deploy elfogadta a `{"server": "host:gg-probe-app", "tools":
> ["ping"]}` manifestet (`capabilities mcp: host gg-probe-app[1 tool]`), és a
> Claude appban megnyitott lapon a `callTool("host:gg-probe-app", "ping")`
> friss payloadot adott — ugyanaz a szerverfolyamat (pid) felelt, amit a Code
> session is elér. Ma már a doksi is kimondja: *„Locally-configured MCP servers
> connected in this session can also be declared, as host servers"*. Korlátok
> (a típusdefinícióból): csak a Claude appban (böngészőfülben
> `server_not_connected`), csak a tulajdonosnak, nem read-only toolra az app
> megerősítést kérhet, a `watchTool` pollozása ≥ ~30 s. Csak a Claude app
> configjában (`claude_desktop_config.json`) felvett szerver számít — a
> `claude mcp add`-os nem (`gg-probe-code`: nem is volt deklarálható).

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
  lásd lent: *Headless publikálás*. 2026-10-01 óta ez sem kell: a **session**
  publikál, a hook kérésére — lásd lent: *Publikálás a sessionből*.
- **A Claude Artifact-ablakát külső folyamat nem nyitja meg.** A (2026-10-01
  óta kivezetett) `--open` a rendszer böngészőjében nyitott. A panel útja a sessionön belülről a
  `/git-graph`, illetve a `ctrl+]`. (A beépített `/artifacts` lista `o`
  billentyűje is böngészőben nyit.)
- **~~Élő adat csak claude.ai konnektorból jöhet.~~** Megdőlt (2026-09-30): a
  `host:` híd működik — lásd lent: *Élő Artifact a `host:` hídon*. Az eredeti
  gondolatmenet: git-gráfhoz ez GitHub
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

> **Kivezetve (2026-10-01):** a publikálás a sessionbe költözött (lásd lent:
> *Publikálás a sessionből*), a `publish_page()` és a launchd agent kikerült.
> A mérések megmaradnak — ha egyszer mégis session nélkül kellene publikálni.

Egy `claude -p` folyamat publikált; a beállítás a `publish_page()`-ben volt.
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

## Élő Artifact a `host:` hídon (2026-09-30)

A beágyazott adatú lap minden változásnál újra feltöltendő volt — nagy repón
~50 s, mert a modell az élő és a helyi példányt is végigolvassa. Ezért az
Artifact most **vékony lap**: csak a sablon, adat nélkül. A Claude appban
megnyitva a gépen futó `gg --mcp`-t hívja (`callTool("host:git-graph", …)`):
2 s-onként az olcsó `fingerprint`-et, és csak változáskor a `graph_data`-t.

| Mérés | Eredmény |
| --- | --- |
| `fingerprint`, a `gg --mcp` saját ideje | 36–42 ms |
| `graph_data`, 31 KB / 151 KB adat | 152 ms / 274 ms |
| vékony lap (~27 KB) feltöltése | 5–8 s (régi nagy lap első cseréje: 20–30 s) |
| teljes MCP-ág a lapon, hamis híddal (Browser panel) | `fingerprint` ~130 ms, `graph_data` ~190 ms |
| **a Claude appban, valódi híddal** | `fingerprint` 262 ms, `graph_data` 414 ms |
| **változás → a lapon látszik** (fájltörlés 05:56:28 → kirajzolva 05:56:31) | **~3 s** (≤ 2 s poll + ~0,7 s) |

Két buktató, mindkettő mérve:

- **A lap capability-deklaráció nélkül nem kap MCP-t** (`use("mcp")` → `null`).
  ~~A headless publikáló csak akkor tudja deklarálni a `host:git-graph`-ot, ha
  a sessionje is látja a szervert (`--mcp-config`).~~ 2026-10-01-én újramérve:
  a deklaráció a szerver nélkül is átmegy (lásd lent).
- **A futó Claude app felülírja a `claude_desktop_config.json`-t** a
  memóriabeli változattal (beállítás-mentéskor) — a közben beírt bejegyzés
  elveszett. Beírás után azonnal újra kell indítani.

A vékony lapot csak sablon- (kód-) vagy repónév-változáskor kell feltölteni;
a SessionStart hook ellenőrzi (hash).

## Publikálás a sessionből (mérve, 2026-10-01, Claude Code 2.1.285, contract 0.2.66)

Kérdés: kiváltható-e a headless `claude -p` és a launchd agent azzal, hogy a
hook a futó sessiont kéri meg a publikálásra? A kód csak plugin-frissítéssel
változik, az pedig csak új sessionnel lép életbe — ilyenkor először a hook fut.

| Mérés | Eredmény |
| --- | --- |
| `host:git-graph` deklarálása Code-tab sessionből, a szerver **nélkül** (nem volt az app configjában) | **átmegy**, csak figyelmeztetés: *„no successful call to it was observed in this session"* |
| Látja-e a Code-tab session az app configjának szerverét | **igen**: `mcp__git-graph__*` toolok; az app minden sessionnek külön `gg --mcp`-t indít |
| Artifact tool az első körben — Desktop (Code tab) | **van**, nem deferred |
| Artifact tool az első körben — interaktív terminál-CLI (pty, `CLAUDE_CODE_*` env nélkül) | **van** (`ARTIFACT=YES`, miközben a SessionStart hookok még futottak) |
| Publish meglévő Artifactra, `read` nélkül, friss sessionből | **elutasítva**; az elutasítás az élő verziót adja, és *„now counts as viewed"* — a második publish átmegy |
| A sessionből publikált lap az appban | **működik**: `callTool("host:git-graph", "fingerprint")` friss payloadot adott |

Következmény: a hook a hash-eltérésnél `additionalContext`-ben adja a
lépéseket (`read` → `publish` a `PUBLISH_CAPS`-szal → `gg --published <URL>`,
ami a hasht visszaírja). A headless út, a `--mcp-config` és a launchd agent
kikerült; a leszerelés figyelését a `gg --mcp` vette át. Headless (`-p`, SDK)
sessionben a hook nem kér publikálást.

Az app MCP-naplója (`~/Library/Logs/Claude/mcp-server-git-graph.log`) a
host-híd `tools/call` hívásait **nem** naplózza — a lap működését onnan nem
lehet ellenőrizni.

## A lapról a sessionbe: `comments.sendToClaude` (mérve, 2026-10-01, Claude Code 2.1.285)

Kérdés: tud-e a lap egy gombnyomással kérést küldeni a futó Code-sessionnek
(„merge-öld ezt az ágat” → a session a saját commandjával hajtja végre), író
végpont és nem read-only MCP nélkül. Eszköz: eldobható próbalap
`capabilities: {comments: {}}`-vel, egy `sendToClaude({anchor, text})` gombbal.

- **A `sample` NEM erre való**: állapot nélküli modellhívás, a sessionről nem tud.
- **Eljut**: a session „Artifact comment sent to Claude” üzenetet kap (szál-id,
  horgony-elem), és a szálban válaszol (`ArtifactComments reply`/`resolve`).
- **Annak a sessionnek megy, amelyiknek a paneljén a lap nyitva van** — nem
  minden figyelőnek. Két session ugyanazon a lapon: mindkettő a saját paneljén
  nyomott gombot kapta. Worktree-s munkánál így magától a jó session lép.
- **Figyelés (`watch`) és felfegyverzés nem kell hozzá**: a figyelés
  lekapcsolása után is megérkezett. (Önmagában a figyelés szabályai: publikálás
  vagy a Fejlesztő üzenetében kapott link felfegyverez, a hookból kapott link
  nem — de ez a panelről küldött kérést nem érinti.)
- **Hozzájárulás**: az app Artifactonként egyszer kérdez; utána a másik
  sessionben sem, és az app újraindítása után sem.
- A kérés **kommentszálként megmarad** az Artifacton; a session a végén lezárja.
- A session a szöveget megbízhatatlan adatként kapja — kérésként kezeli, a
  merge-et és a PR-t a workflow szerint jóváhagyással futtatja. Ez a kívánt
  viselkedés.

Következmény: a hook mai `open`-je elég; a lapon a `comments` capability kell
(`PUBLISH_CAPS`), a gomb csak `canSendToClaude() === "available"` esetén.

## Dinamikus kódfuttatás a lapon (mérve, 2026-10-02, contract 0.2.66)

Kérdés: le tudja-e kérni a lap a saját rajzoló kódját az MCP-ből, és le tudja-e
futtatni? Ha igen, egy plugin-frissítés után nem kell újrapublikálni.
Eldobható mérőlap, `mcp` capabilityvel publikálva, a Claude appban megnyitva:

| Mód | Eredmény |
| --- | --- |
| `eval`, `new Function`, `setTimeout(string)` | **megy** |
| inline `<script>` (`textContent`), `<script src=blob:>` | **megy** |
| `import(blob:)` (ES modul) | **megy** |
| `<script src=data:>`, `import(data:)` | tiltott (`script-src-elem`) |
| inline `<style>` beszúrása | **megy** |

A CSP HTTP-headerben jön (`<meta>` nincs). A lényeges része:
`script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: <CDN-lista>`,
`style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`,
`connect-src 'self' <Google Fonts>`. A külső `fetch` tehát továbbra is tiltott,
de az MCP-ből kapott szöveg futtatható.

## Közös Artifact a worktree-knek (mérve, 2026-10-04, Claude Code 2.1.286, contract 0.2.67)

Kérdés: kiváltható-e a worktree-nkénti Artifact egy repónként közös lappal,
amely a „saját” worktree-t a link `#horgony`-ából tudja, és mennyibe kerül a
worktree-nkénti WIP-adat a 2 s-os pollozásban.

### `#horgony` az `Artifact open`-nel — NEM jut át

Eldobható próbalap `db` capabilityvel: minden betöltésnél, `hashchange`-nél és
a `location.hash` 500 ms-os pollozásakor sort írt a `db`-be (betöltés-azonosító,
`hash`), a session `ArtifactData`-val olvasta vissza.

| Lépés | Eredmény |
| --- | --- |
| publish (a panel magától megnyitja) | 1 betöltés, `hash: ""` |
| `open …#wt-alpha` a nyitott lapra | se betöltés, se `hashchange`, se hash-eltérés |
| másik Artifact `open`, majd `open …#wt-beta` | ugyanaz: a próbalap kerete megmaradt, nem töltött újra |
| Artifact panel bezárva (`close_pane`), `open …#wt-delta`, `show_pane`, `open …#wt-epsilon` | ugyanaz: a keret a panel bezárását is túléli |
| újrapublikálás (kontroll) | új betöltés, `hash: ""` — a naplózás működik, a reload horgony nélküli |
| `open …#wt-zeta` a reload után | semmi |

Az `open` válasza és a panel nézetének URL-je (`preview_list`:
`artifact_view`) is horgony nélkül adja vissza a címet — az eszköz a horgonyt
eldobja. Böngészőben a link bejelentkezést kért, ott nem mértem (a `host:` híd
amúgy is csak az appban él).

### A szerver sem tudja, melyik session lapja hív

A `git-graph --mcp` példányok **app-szintűek**: 2 db, `cwd: /`, az app
indulásakor (00:38) indultak, a 06:30-as session nem kapott újat. A host-híd
hívásából tehát a session (és a munkakönyvtára) nem derül ki. A
`comments.sendToClaude` viszont továbbra is a lapot mutató sessionhöz megy
(lásd fent) — a platform tudja, a lap nem.

### Session-váltás: hook nincs, a panel láthatósága mérhető

Ideiglenes, naplózó hook a git-graph repó `.claude/settings.local.json`-jában
(`SessionStart`, `UserPromptSubmit`, `CwdChanged`, `Notification`,
`ConfigChange`, `InstructionsLoaded`, `FileChanged`, `Stop`, `SessionEnd`). A
hookok a már futó sessionökben is azonnal életbe léptek.

- **Session-váltás a UI-ban: semmi nem sül el** (oda, vissza, oda — írás
  nélkül). A dokumentáció 33 eseménye között sincs fókusz- vagy
  láthatóság-esemény.
- **`UserPromptSubmit`** a promptoló sessionből jön, `session_id`-val és
  `cwd`-vel — a prompt pillanatában az a session van előtérben.
- **`CwdChanged`** egy Bash `cd`-re elsült (`old_cwd`, `new_cwd`); a Bash
  eszköz cwd-visszaállítására nem.

A lap a saját panelje elrejtését érzékeli — a próbalapon, session-váltáskor:

| Jel | Elrejtve |
| --- | --- |
| `document.visibilityState` / `hidden` | változatlan (`visible`) |
| `innerWidth` / `innerHeight` | változatlan |
| `IntersectionObserver` a `body`-n | **`false`**, visszaváltáskor `true` |

Következmény: ha egy prompt pillanatában a repó lapjai közül pontosan egy
látszik, az a promptoló session panelje — így a panel a sessionhöz (és annak
worktree-jéhez) köthető.

### WIP-költség worktree-nként

Eldobható klónokon, `--no-optional-locks`-szal, egy kör = `for-each-ref` +
`worktree list` + worktree-nként `status --porcelain`, `diff --numstat HEAD`,
`rev-parse HEAD --abbrev-ref HEAD` (25 kör mediánja):

| Worktree-k | git-graph (~60 fájl) | 10 582 fájlos repó |
| --- | --- | --- |
| 1 | 56 ms | 148 ms |
| 3 | 127 ms | 412 ms |
| 5 | 202 ms | 678 ms |
| 5, szálanként párhuzamosan | 53 ms | 326 ms |

A nagy repón a `status --porcelain` 87 ms, ebből ~60 ms a követetlen fájlok
keresése (`--untracked-files=no`: 26 ms); a `diff --numstat HEAD` 26 ms.

**Buktató**: friss worktree-ben (vagy klónban) az index stat-adatai még nem
frissültek, és a `--no-optional-locks` miatt a pollozás sosem írja vissza —
így minden kör újrahasheli a fájlokat: ugyanaz a mérés **~450 ms**
worktree-nként, amíg egy zároló git-parancs (bármelyik `git status` a
Fejlesztőtől) nem frissíti az indexet.

Következmény: a horgonyos „saját worktree” nem járható; a WIP-adat
párhuzamosan gyűjtve 5 worktree-vel is belefér a 2 s-os pollozásba.

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
