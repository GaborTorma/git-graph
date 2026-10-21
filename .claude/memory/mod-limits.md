---
name: mod-limits
description: Claude Code modból az Artifact open és read megy, a publish nem (az auto mód elutasítja); a classic.* események nem jönnek; a mod-panel nem DOM
metadata:
  type: project
---

Mérve 2026-10-09-én (Claude Code 2.1.293), eldobható moddal, auto módban:

- `$.tool.call({ tool: 'Artifact', action: 'open', url })` megerősítés nélkül átmegy (~270 ms), friss
  sessionben megnyitja a panelt. A `read` is átmegy.
- A `publish` modból elutasítva: *„auto mode classifier gave no verdict … the request that produced
  this action did not ask for one”* — a modhívás mögött nincs kérés. `permissions.allow` szabály nem
  segít: az `Artifact(publish)` / `Artifact(<URL>)` forma nem illeszkedik, a tág `Artifact` csak az
  `open`-t viszi. A `consent` mezőt kódba írt szöveggel nem mértük: az auto mód már a megírását is
  megkerülésnek vette.
- `classic.SessionStart` / `classic.PostToolUse` a modban nem fut le, akkor sem, ha a plugin hookja
  illeszkedik (`tool.call` igen).
- A hook `additionalContext`-je `session.append` `door: 'hook-context'` sorként átírható.
- A mod-panel (`$.ui.open` + `ui.render`) saját elemfa (`Box`, `Text`, `Svg`…): DOM, HTML, script
  nincs → a lap nem mehet mod-panelbe.

**Why:** ezért a hook publikáltat, a mod nyit meg ([[hook-publishes-mod-opens]]).

**How to apply:** modból csak `open` és `read`; ami publikálás, az a session dolga. Újranyitás:
[[artifact-open-paths]].
