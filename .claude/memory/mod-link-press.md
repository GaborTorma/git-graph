---
name: mod-link-press
description: Egy mod a desktop app válaszainak fájllinkjére kattintást elkapja (AssistantMessage átrajzolása Markdown + onLinkPress); a diff-kártyára nincs fogás
metadata:
  node_type: memory
  type: project
  originSessionId: 0de08fe0-10c4-4388-addf-0019cd830876
  modified: 2026-10-27T14:16:46.241Z
---

Mérve 2026-10-27-én (Claude Code 2.1.308, desktop app), eldobható moddal (`link-probe`):

- `on('ui.render', { component: 'AssistantMessage' }, …)` a desktop felületen is a mod fáját rajzolja; a
  `$.ui.resolve(e).Markdown` `onLinkPress`-e a kattintást a modhoz viszi (toast jött), a kinézet
  változatlan.
- A `Markdown` csak `https:`, `http:` és `file:` linket rajzol linkként: a válasz relatív linkjét
  (`[x](page/js/x.js)`) a mod `file://<cwd>/…`-ra írja át, és a `pressableLinks`-ben csak ezeket
  sorolja fel — a többi link az appé marad.
- Az Edit/Write diff-kártya (`ToolUse`) csak egészében cserélhető, a kattintás nem akasztható rá.

**Why:** a „fájllink a git-graph-ban nyíljon” ötlet erre épül; a mod-API leírása és a valóság a
`classic.*`-nál már eltért ([[mod-limits]]), ezért mérni kellett.

**How to apply:** fájllink → mod `AssistantMessage`-átrajzolással; a megnyitáshoz a lapot a
`changes` long-pollon át kell értesíteni, és a már nyitott lapot a mod `open`-je nem hozza elő
([[artifact-open-paths]]).
