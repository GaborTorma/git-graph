---
name: mod-limits
description: "Claude Code modból az Artifact open és read megy; a publish csak felhasználói műveletből (slash command, $.ui.ask + consent), kérés nélkül nem; a classic.* események nem jönnek; a mod-panel nem DOM"
metadata:
  node_type: memory
  type: project
  originSessionId: d1b66ed6-bb87-473f-9f58-41922cfc1afa
  modified: 2026-10-31T11:46:52.387Z
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

**Why:** ezért a hook publikáltat, a mod nyit meg ([[hook-publishes-mod-opens]]).

**How to apply:** modból kérés nélkül csak `open` és `read`; publikálás modból csak a felhasználó
műveletére (command, kattintás) — különben a session dolga. Újranyitás:
[[artifact-open-paths]].
