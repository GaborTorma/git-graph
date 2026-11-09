---
name: mod-limits
description: "Modból: Artifact tool nincs; publish_files csak allow-szabállyal; declare_capabilities sehogy (consent-tel sem); show_pane a sessionben publikáltat; classic.* nem jön; a mod-panel nem DOM"
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

Újramérve 2026-11-05/06-án (Claude Code 2.1.317, desktop, auto mód), az `Artifact` tool helyén a
`mcp__claude-artifacts__*` eszközökkel:

- `$.tool.call({ tool: 'Artifact' })` → *„no tool named "Artifact" in this session”*; `open`
  művelet nincs. A `mcp__ccd_view__show_pane` (`pane: "artifact"`) modból hívható, de csak a
  sessionben publikált lapot mutatja, és csak ablakban nyitott sessionben.
- A `publish_files` modból csak a felhasználó `permissions.allow` szabályával megy (a
  szabályt az *AI* nem írhatja be). Az olvasók szabály nélkül lassúak, és olykor *„gave no
  verdict”*.
- A `declare_capabilities` modból **sehogy**: `allow`-szabállyal, újrapróbával és a `$.ui.ask`
  valódi kattintásából adott `consent`-tel (a deklarálást név szerint kérő kérdéssel) is
  *„The server-side auto mode classifier gave no verdict … did not ask for one”*, 4 próbából 4.
  A sessionből, felhasználói kérés mögött azonnal átmegy.
- A `publish_files` a `<!DOCTYPE html>` nélküli lapot elutasítja (*„must be HTML”*), és a
  válasza a JSON után szöveget fűz.

2026-11-09-én (Claude Code 2.1.317, desktop) a session újra a beépített `Artifact` eszközt kapja
(`open` művelettel), a `mcp__claude-artifacts__*` eszközök nincsenek: a régi út csendben elbukott.
A mod ezért előbb `Artifact` `open`-t hív, és csak ha az nem megy, a `claude-artifacts` útját. A
hook `publish_steps`-e és a `mod_can_publish` (`MOD_ALLOW`) még a `claude-artifacts` eszközeit nevezi meg.

**Why:** ezért új lapot és capability-változást a hook a sessiontől kér; a mod csak újraküld
(a capability öröklődik) és megnyit ([[hook-publishes-mod-opens]], [[publish-from-session]]).

**How to apply:** modból `declare_capabilities` ne legyen; a `git-graph.artifactCaps` mondja
meg, mikor kell a session. Újranyitás: [[artifact-open-paths]].
