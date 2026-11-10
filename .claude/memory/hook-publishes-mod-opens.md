---
name: hook-publishes-mod-opens
description: A mod publikál és nyit (2.1.321 óta), a hook csak telepít és regisztrál; sessionönként egyszer (sessions.json); resume, /clear, compact nem zárja be a lapot
metadata:
  type: project
---

- 2026-11-10 óta (a Fejlesztő döntése, a 2.1.321-es mérés után; a régebbi kliens nem érdekes) a
  plugin modja (`hooks/register.ts`) végez mindent a session indulásakor, a modell nélkül: a
  `git-graph --mod-plan` terve szerint új vagy elavult lapnál `Artifact` `read` + `publish`
  (teljes `PUBLISH_CAPS`, `PUBLISH_CONTRACT`), `--published`, majd `Artifact` `open` +
  `show_pane`. A SessionStart hook csak telepít és regisztrál, a sessiontől nem kér semmit.
  Élesben mérve 2026-11-10-én a Lesownon: új chat → a mod újrapublikálta (0.2.96, 7 tool), a
  `--published` frissítette a hasheket.
- Előtte (2.1.293–2.1.317) a mod nem publikálhatott (auto mód), ezért a hook kérte a sessiont
  (`publish_steps` additionalContextként). A `publish_steps` ma csak a kézi skilleké.
- Sessionönként egyszer: `~/.git-graph/sessions.json` (`session_id → slug`, 7 nap után törlődik), a
  `source`-tól függetlenül — a `resume`, a `/clear` és a `compact` nem zárja be a lapot; archiválásra
  nincs hook. Elbukott publikálás után abban a sessionben nincs újrapróba.
- Kapcsolók a lap fogaskerekén (`settings` tool): automatikus megnyitás repónként
  (`git-graph.autoOpen`) és automatikus publikálás a gépen (`~/.git-graph/settings.json`, az új
  Artifacthoz).

**Why:** a modell köre és a hook szövege nélkül, a session indulásakor rendeződik a lap.

**How to apply:** automatikus publikálás és megnyitás → mod ([[mod-limits]], [[spare-session-cwd]]);
kézi → skill a `git-graph --publish` / `--open-url` lépéseivel ([[publish-from-session]]).
