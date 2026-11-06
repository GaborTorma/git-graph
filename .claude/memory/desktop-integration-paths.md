---
name: desktop-integration-paths
description: "Beépülés a desktop appba saját panelként: a panelkészlet zárt, a Code fül felülete a claude.ai-ról jön, az asar zárva; a böngészőpanel localhostot scripttel futtat"
metadata:
  node_type: memory
  type: project
  originSessionId: 7f157f16-affc-478a-9cc7-8f5f06c530b5
  modified: 2026-11-06T07:36:04.074Z
---

Mérve 2026-11-03-án (Claude desktop 4.4212.0, Claude Code 2.1.316):

- **A panelkészlet zárt**: `diff`, `file`, `terminal`, `pr`, `tasks`, `plan`, `artifact`, `preview`
  (a helyi bundle-ben `new Set([...])`); plugin nem regisztrál új paneltípust.
- **A Code fül felülete távoli**: a `mainView` a claude.ai-t tölti (`loadURL(NA())`), a panelek kódja
  nincs az `app.asar`-ban — helyi patch-csel nem érhető el.
- **Az asar zárva**: fuse `EnableEmbeddedAsarIntegrityValidation`, `OnlyLoadAppFromAsar` be,
  `RunAsNode`, `EnableNodeCliInspectArguments` ki; a `--remote-debugging-port` / `-pipe` kapcsolót az
  `index.pre.js` tiltólistája (`HZ`) szűri. Patch = újraaláírás, a frissítés felülírja.
- **A böngészőpanel (`preview`)** a `http://127.0.0.1:<port>` lapot felső szintű keretben, scripttel,
  `localStorage`-dzsel futtatja (`window.claude` nincs). Egy `git-graph` HTTP-szerver így a hídon
  kívül, közvetlenül adhatná a lapot. Megnyitás: a modell `preview_start`-ja; modból és
  `launch.json`-ból nem mértük.
- **Mod-panel**: elemfa, DOM nincs ([[mod-limits]]). Mérve 2026-11-06-án (Claude Code 2.1.317,
  `pane-probe` próbamod): a desktop a jobb oldali panel-oszlopba teszi (`surface: desktop`,
  `placement: dock`), egy nyitott Artifact alá osztva, saját címsorral, nagyítás és bezárás
  gombbal. A session-infó oldalsávba (Environment, Context, Changes, ahová a Terminal
  minimalizálódik) nem kerül; oda plugin nem tesz elemet. Amíg a session nincs ablakban, a
  `$.ui.open` válasza `{ isPlaced: false, reason: "no-surface" }`.

**Why:** a „git-graph saját panelként, mint a fájl vagy a diff” kérdésre ez a teljes felderítés.

**How to apply:** új panelt ne keress az appban; a jelöltek az `artifact` (mostani út) és a
`preview` panel localhost-szerverrel. Kapcsolódó: [[artifact-open-paths]], [[host-bridge-limits]].
