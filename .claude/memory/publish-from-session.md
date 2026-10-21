---
name: publish-from-session
description: Az Artifactot a session publikálja (a hook kéri) — meglévőre csak Artifact read után, csak végigolvasott fájlt; a lépésekben git-graph áll, nem abszolút út
metadata:
  type: project
---

Mérve 2026-10-01-én (Claude Code 2.1.285, contract 0.2.66):

- Az Artifact API-t csak a modell éri el. A Code-tab és az interaktív terminál-CLI sessionben az
  Artifact tool már az első körben megvan, nem deferred.
- Friss sessionből meglévő Artifactra a publish `read` nélkül elutasítva. Az elutasítás az élő
  verziót adja, és *„now counts as viewed”* — a második publish átmegy. Változatlan újraküldést is
  elutasít.
- A modell csak végigolvasott fájlt publikál (*„never distributes what it has not seen”*), a `Read`
  ~25k token/hívás. Egy 180 ezer karakteres JSON-sort nem tudott elolvasni → nem publikált.
  Frissítéskor az élő példányt is végigolvassa.
- A Code-tab session látja az app configjának szerverét (`mcp__git-graph__*`); az app minden
  sessionnek külön `git-graph --mcp`-t indít.
- A hook az eredményt nem látja → a `git-graph --published <URL>` írja vissza az URL-t és a hasht
  (az `artifact.html`-ből számolva).
- A lépésekben `git-graph` áll, nem abszolút út: a plugin `bin/`-je a Bash PATH-ján van, és egy
  `Bash(git-graph:*)` engedély lefedi.
- Headless (`-p`, SDK; `CLAUDE_CODE_ENTRYPOINT=sdk-*`) sessionben a hook nem kér publikálást.

**Why:** a headless `claude -p` + launchd út ([[headless-publish-retired]]) helyett ez lett a
publikálás; a mod nem publikálhat ([[mod-limits]]).

**How to apply:** `publish_steps` / `git-graph --publish`: `read` → `publish` a `PUBLISH_CAPS`-szal →
`git-graph --published <URL>`. A lapba ne kerüljön nagy, egysoros tartalom
([[artifact-holds-no-data]]).
