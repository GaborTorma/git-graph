# Takarítás: átmeneti kód, történeti doksik, rövidebb CLAUDE.md

Egy visszatekintés („mit csinálnánk másképp nulláról”) után kikerült a már
fölösleges átmeneti kód és a történeti doksik, a CLAUDE.md pedig a harmadára
rövidült.

Az átmeneti kódból kikerült a 0.12.x-es stabil belépő ága a `bin/git-graph`-ból
és a tesztje, valamint a 0.13 előtti `git-graph.autoPublish` kulcs
kezelése az automatikus megnyitásban. A 0.14 a kiadott verzió, a stabil
másolat mindenhol már zip, és egyetlen regisztrált repóban sincs régi kulcs.

A `docs/desktop-live.md`, a `docs/mcp-plan.md` és a `probe/` egy kivezetett,
illetve már megvalósult útról szólt; a git-történetben megmaradnak.

A CLAUDE.md minden sessionben betöltődik, és 377 sorra nőtt; most 134 sor. A
gotchák indoklása és a mérések szó szerint átkerültek a
`docs/architecture.md`-be, a CLAUDE.md-ben csak egysoros szabály és hivatkozás
maradt.

Nyitva maradt a lap viselkedési tesztje (Playwright-harness fixture-rel és kamu
MCP-vel) és a `tsc --checkJs` a Checkben. Ez a következő, feature-jellegű kör.

- [`[337b4a6f]`](https://github.com/GaborTorma/git-graph/commit/337b4a6f9b2d4744d991ac9fef71ee9ec40e0258) · chore: drop the 0.12 entry shim and the pre-0.13 autoPublish fallback
- [`[f603c98a]`](https://github.com/GaborTorma/git-graph/commit/f603c98a088fba7ea5326f3b31435821c39fe9f2) · docs: remove the historical desktop-live, mcp-plan notes and the probe tool
- [`[a85431bc]`](https://github.com/GaborTorma/git-graph/commit/a85431bc3ff87ad4a1678f9f9a8d8bbba3595540) · docs(claude): trim CLAUDE.md to one-line rules, move the rationale to docs/architecture.md
