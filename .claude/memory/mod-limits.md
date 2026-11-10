---
name: mod-limits
description: "Modból: Artifact open kérdés nélkül megy, publish nem (auto mód), capability-deklarálás sehogy; show_pane hívható; classic.* nem jön; a mod-panel nem DOM"
metadata:
  node_type: memory
  type: project
  originSessionId: d1b66ed6-bb87-473f-9f58-41922cfc1afa
  modified: 2026-11-09T18:53:35.190Z
---

Mérve 2026-10-09-én (Claude Code 2.1.293), eldobható moddal, auto módban:

- `$.tool.call({ tool: 'Artifact', action: 'open', url })` megerősítés nélkül átmegy (~270 ms), friss
  sessionben megnyitja a panelt. A `read` is átmegy.
- A `publish` modból elutasítva: *„auto mode classifier gave no verdict … the request that produced
  this action did not ask for one”* — a modhívás mögött nincs kérés. `permissions.allow` szabály nem
  segít: az `Artifact(publish)` / `Artifact(<URL>)` forma nem illeszkedik, a tág `Artifact` csak az
  `open`-t viszi. A `consent` mezőt kódba írt szöveggel nem mértük: az auto mód már a megírását is
  megkerülésnek vette.
- **Felhasználói műveletből a publish megy** (mérve 2026-10-31, Claude Code 2.1.316, auto mód): a mod
  saját slash commandja (`command.run`) `$.tool.call` `Artifact` `publish`-t hív. Új lap `consent`
  nélkül: 2,9 s, URL-t ad. Ugyanez `$.ui.ask` + valódi „Igen” kattintás után, a `consent`-ben a
  kattintás szövegével (`The user pressed "Igen" on "…"`): 0,8 s (változatlan újraküldés,
  `unchanged: true`). A `consent` a `ToolCallReserved` mezője, emberi körként jut a jogosultság-ellenőrzéshez.
- Kérés nélküli publisht (`session.start`-ból) 2.1.316-on nem mértünk: az auto mód már a kód
  megírását blokkolta. Másik sessionből meglévő Artifact frissítését (`url` + `read`) sem.
- `classic.SessionStart` / `classic.PostToolUse` a modban nem fut le, akkor sem, ha a plugin hookja
  illeszkedik (`tool.call` igen).
- A hook `additionalContext`-je `session.append` `door: 'hook-context'` sorként átírható.
- A mod-panel (`$.ui.open` + `ui.render`) saját elemfa (`Box`, `Text`, `Svg`…): DOM, HTML, script
  nincs → a lap nem mehet mod-panelbe.
- Újranézve 2026-10-31-én (a mod-API típusai, 2.1.309-es skill, CLI 2.1.316): még mindig nincs
  HTML / iframe / webview elem. A desktop táblája: `Box`, `Text`, `Button`, `Input`, `Select`,
  `Svg`, `Link`, `Code`, `Markdown`, `Client`. A `Client` „surface module” is ugyanezt az elemfát
  rajzolja (`ClientElements`; nincs DOM, timer, `eval`). A legközelebbi az `Svg`
  `isInteractive: true`: script nélküli sandbox-keret (hover, CSS `:hover`, `<title>`), a scriptet
  és az eseménykezelőt kiszűri; `source` max. 131 072 karakter. A gráf így csak statikus SVG-ként,
  a sor-, panel- és diff-logika újraírásával férne be.

2026-11-04–06. között az app a beépített `Artifact` helyett egy `claude-artifacts` MCP szervert
adott; visszavonták (anthropics/claude-code#107400), 2026-11-09 óta újra az `Artifact` van, a
plugin csak ezt használja. Ebből az időből: a `show_pane` (`pane: "artifact"`) modból hívható, de
csak ablakban nyitott sessionben hat; capability-t modból deklarálni az auto mód akkor sem engedett,
`allow`-szabállyal és valódi kattintás `consent`-jével sem.

**Mérve 2026-11-10-én (Claude Code 2.1.321, desktop app 4.23118.1, auto mód)**, eldobható moddal
(`session.start`-ból, kérés nélkül, a modell nélkül): az `Artifact` `read` (2,0 s), a `publish`
`url` + `file_path` + `contract`-tal (1,1 s) és a `publish` `capabilities`-szel (1,1 s, a
deklaráció átment) **mind sikerült**, elutasítás és kérdés nélkül. A 2.1.321 óta a mod saját
`$.tool.call`-jai nem kérnek engedélyt (a release note szerint a `deny`-szabály és a szervezeti
szabály marad). A korábbi mérések (2.1.293–2.1.317) ezzel elavultak.

**Why:** ezért új és elavult lapot, capability- és contract-változást a hook a sessiontől kér; a
mod csak megnyit (`Artifact` `open`) ([[hook-publishes-mod-opens]], [[publish-from-session]]).

**How to apply:** a mod publikál és nyit ([[hook-publishes-mod-opens]]); a `git-graph.artifactHash`
mondja meg, mikor kell publikálni. Újranyitás: [[artifact-open-paths]].
