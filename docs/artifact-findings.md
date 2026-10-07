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

~~Következmény: ha egy prompt pillanatában a repó lapjai közül pontosan egy
látszik, az a promptoló session panelje.~~ **Megdőlt (lent):** a próbalap a
másik sessionben nem volt nyitva — ugyanazt az Artifactot mutató sessionök
egy keretet látnak.

### Egy Artifact = egy keret, minden sessionben

Ideiglenes naplózás a `git-graph --mcp`-ben (a teljes `tools/call` üzenet) és
a lapon (betöltésenként véletlen `load`, `innerWidth`/`innerHeight`,
`document.hasFocus()`), három session között váltva, amelyek mind a repó
lapját mutatták:

| Idő | `load` | Méret | Session |
| --- | --- | --- | --- |
| 13:38:44 | `7182wi` | 606 × 1471 | ez a session |
| 13:39:19 | `7182wi` | 912 × 1471 | Graph test-2 |
| 13:39:29 | `7182wi` | 914 × 1471 | Új teszt 3 |
| 13:39:40 | `7182wi` | 606 × 1471 | vissza |

- **Egyetlen keret** (ugyanaz a `load`) vándorol a sessionök panelje között;
  nem töltődik újra, láthatósága nem változik. Panelenkénti azonosító így
  értelmetlen.
- **A host semmit nem küld a hívással** (se `_meta`, se session) — csak a tool
  nevét és argumentumait.
- A keret **mérete** sessionönként más (a panelek szélessége), de ez törékeny
  (azonos szélesség, ablak-átméretezés).
- Az `Artifact open` a lekérdezést (`?…`) is levágja, mint a horgonyt.
- A platform a `window.name`-ben tartja a bootstrapját (`{"hot":…,"usable":…}`);
  a `location.reload()`-ot a `window.name`, a horgony (`replaceState`), a
  `sessionStorage` és a `history.state` is túléli, egy újraépült keret viszont
  friss `window.name`-mel indul; a `sessionStorage` a keretek között közös.

### Az előtérben lévő session: a Claude app session-fájljai

A Claude app sessionönként JSON-t tart:
`~/Library/Application Support/Claude/claude-code-sessions/<fiók>/<szervezet>/local_<id>.json`
— benne `cwd`, `worktreePath`, `cliSessionId` (a hookok `session_id`-ja),
`isArchived` és **`lastFocusedAt`** (ms). A fenti váltások időpontjai
másodpercre egyeztek a `lastFocusedAt` értékekkel (13:39:18 / 13:39:28 /
13:39:39). A repóban dolgozó, nem archivált sessionök közül a legnagyobb
`lastFocusedAt` az előtérben lévő.

253 fájl, egyenként akár ~770 KB: mindet beolvasni ~520 ms, `stat`-tal
< 1 ms — a szerver csak a megváltozott fájlt olvassa újra (váltáskor egyet,
~5 ms). Belső fájl: a formátuma változhat, ismeretlennél nem dönt.

Mellékesen: az app `Session Storage` leveldb-jében a `cmdk-navigation-history`
is a legutóbb megnyitott sessiont tartja elöl — de nyers leveldb-naplóból,
tömörítés után olvashatatlan; a JSON a stabilabb.

### Gyorsabban: az app naplója

A `lastFocusedAt` **1–3 s késéssel** kerül a fájlba (az app kötegelve írja:
gyors egymás utáni váltásnál a köztes session fájlja +2,9 s-mal frissült). Erre
épült egy méret alapú tipp (a panelek más szélesek), de rossz worktree-re is
átváltott, mielőtt a fájl kijavította — kivezetve.

Az app naplója (`~/Library/Logs/Claude/main.log`) minden váltáskor ír:

```
2026-10-04 14:52:06 [info] [CCD] LocalSessions.setFocusedSession: sessionId=null
2026-10-04 14:52:06 [info] [CCD] LocalSessions.setFocusedSession: sessionId=local_834e9f2a-…
```

Mérve (10 váltás, 20 ms-onként figyelve): a sor a fájlba később kerülő
`lastFocusedAt`-hoz képest **+1…+20 ms**-mal már a naplóban van. Az azonosító
a session-fájl neve (`local_<id>.json`), abból jön a munkakönyvtár. A napló
másodpercre kerekít, ~10 MB-onként forog (`main.log` → `main1.log`, új inode);
a szerver csak az új sorokat olvassa (< 0,1 ms), induláskor a végéből 2 MB-ot
(~13 ms). Belső napló: ha a sor eltűnik, a session-fájl marad a forrás.

### A keret a váltás alatt: rejtve

Eseménynaplóval a lapon (`resize`, láthatóság, fókusz, IntersectionObserver,
rAF-kimaradás), egyforma és eltérő méretű panelek között váltogatva:

- Egyforma méretnél **nincs `resize`**, de a keret a váltás alatt nem látszik:
  a `requestAnimationFrame` 0,5–11 s-ig nem fut (amíg a session nem
  rajzolódott be), megjelenéskor az IntersectionObserver `0 → 1`-et jelez.
  `visibilitychange`, `focus` / `blur`, `pageshow` nem jön.
- A `server_unavailable` hibák mind a rejtett szakaszba estek: a host-híd a
  rejtett keretnek nem válaszol. A lap ezért hibánál megnézi, rajzol-e (egy
  rAF 250 ms-on belül); ha nem, csendben vár, és a megjelenéskor kérdez.

Ez a rejtett szakasz akkor volt, amikor a két session között egy **másik
Artifact** (a régi, worktree-nkénti lap) látszott. Ugyanazon Artifact sessionjei
között a keret **rejtés nélkül költözik**: se IntersectionObserver, se
rAF-kimaradás, csak `resize` — egyforma panelméretnél semmi.

### Nyitva tartott hívás és a host korlátja

- A host egy `callTool`-t legalább 50 s-ig nyitva tart (mérve: a `wait`
  határidejére, 50 013 ms után is `ok`); a `wait` felső határa ezért 50 s.
- A lap ezért egy `fingerprint`-hívást (`wait`, `cursor`) nyitva tart, a szerver
  a naplóban megjelenő váltásra ~50 ms-on belül válaszol, az új fókusszal.
- **`rate_limited`**: váltásonként 2 s-ig 250 ms-onként kérdezve gyors
  váltogatásnál ~20 hívás után a host visszafogta a hívásokat (`durationMs: 0`).
  Váltásonként egy hívással (a válasz hozza a fókuszt) másodpercenkénti
  váltogatás mellett sem jött elő.

### A leválasztott worktree ága: a Claude app nyilvántartása

A session törlésekor az app a worktree-t megtartja, a HEAD-jét leválasztja
(a reflogban egyetlen, üzenet nélküli bejegyzés), az ágat is megtartja. A git
ezután semmivel nem köti az ágat a worktree-hez: az ágnak nincs reflogja, a
worktree configjában nincs nyoma. Az app viszont nyilvántartja:
`~/Library/Application Support/Claude/git-worktrees.json` →
`worktrees.<név>` = `{path, branch, sourceBranch, leasedBy, …}` (`leasedBy:
null`: nincs hozzá session). A worktree admin-mappájában egy üres
`claude-desktop-worktree` jelzőfájl is van.

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

### Egy nyitott hívás: long-poll (mérve, 2026-10-06, contract 0.2.67)

A 2 s-os pollozás és a külön fókusz-hívás egyetlen `changes` long-pollá vált
(#29). Előtte műszerezett dev-példánnyal mérve (a szerver minden hívást
naplózott, a lap a következő hívásban visszaküldte az előző eredményét és az
eseményeit):

- **Keret-költözés ugyanazon Artifact sessionjei között** (4 váltás): a nyitott
  hívás túléli, a válasz mindig megérkezik.
- **Rejtett keret** (közben másik Artifact; 10 s, 24 s, 122 s): ami a rejtés
  pillanatában válaszolt, megérkezett. Rejtve indított hívás **1–186 ms alatt
  `server_unavailable`**, a szerverig el sem jut; az időzítők sem futnak (rAF
  24–122 s-ig állt, egy 1 s-os `setTimeout` csak megjelenéskor lőtt). A régi
  kurzorral újrahívva azonnal a helyes állapot jön.
- **Megszakítás** (`callTool` `signal`): a lapon pontos (`cancelled`, 3001 ms-nál
  3000-es abortra), de a szerver **nem kap** `notifications/cancelled`-et — a
  várakozó a határidejéig fut. Lap-újratöltés sem zárja le a nyitott hívást.
- **Párhuzamosság**: nyitott várakozók mellett a rövid hívások kiszolgálódnak; egy
  szerverfolyamat az app összes git-graph lapját szolgálja (három repó lapja
  várt egyszerre).

Az állapot költsége (`repo_state`, az app PATH-jával): git-graph (3 worktree)
52 → 17 ms, Music 48 → 14 ms, 10 582 fájlos repó 139 → 94 ms — a valódi git
bináris (a `/usr/bin/git` `xcrun`-shim, 12 → 6 ms/hívás), a párhuzamos
`for-each-ref` és `status`, és a `diff --numstat` elhagyása (a ns-os mtime is
jelzi egy módosított fájl újabb szerkesztését) hozta. A nagy repón a maradék a
követetlen fájlok keresése (`status` 90 ms, `-uno`-val 24 ms). A git
`core.fsmonitor`-ja ezt 27 ms-ra vinné, de csak úgy, ha az indexbe írja a
token-jét (írás nélkül 154 ms) — az `index.lock` miatt ez nem járható. Egy
`stat`-előszűrő (10 fájl: worktree-nként `HEAD`, `index`, `logs/HEAD`, a
`packed-refs` és a ref-mappák) 0,025 ms.

Harnessben a lapon mérve (adatlekéréssel és rajzolással): ág létrehozása /
törlése ~0,4 s, új fájl / szerkesztés / törlés 0,8–2,2 s; üresjáratban 6 s alatt
egy hívás sem zárult le.

## A lap nyelve: az OS-é, nem az appé (mérve, 2026-10-07, contract 0.2.72)

Az i18n előkérdése: honnan tudja a lap, milyen nyelvű a Claude app. Egy
eldobható mérőlap a Claude appban megnyitva (`db` capability-vel írta vissza az
értékeket, a session `ArtifactData`-val olvasta). Az app beállítása
`"locale": "en-US"` (`~/Library/Application Support/Claude/config.json`), a
macOS nyelve `hu-HU` — a kettő szándékosan eltért.

| Érték | Mért |
| --- | --- |
| `navigator.language` | `hu` |
| `navigator.languages` | `["hu","hu-HU"]` |
| `Intl.DateTimeFormat().resolvedOptions().locale` | `hu` |
| `…timeZone` | `Europe/Budapest` |
| `document.documentElement.lang` | üres |
| `userAgent` | `… Claude/2.26454.0 Chrome/152.0.7977.130 Electron/44.4.3 …` |

- **A `navigator.language` az OS nyelvét adja**, nem az app beállítását: magyar
  macOS-en angol appal is `hu`.
- **A runtime API nem adja át az app nyelvét**: a 0.2.72-es `window.claude`
  típusaiban nincs locale, az `<html lang>` üres.
- Ami ebből következik: az app nyelvét csak a gépen futó szerver tudja kiolvasni
  (`config.json` `locale`), a `navigator.language` csak tartalék.

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
