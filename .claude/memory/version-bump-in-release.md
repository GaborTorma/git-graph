---
name: version-bump-in-release
description: A plugin.json verzióját a /workflow:release emeli, nem a feature- vagy fix-commit
metadata:
  type: feedback
---

A `.claude-plugin/plugin.json` `version`-jét a `/workflow:release` emeli (a release-commitban),
nem a feature- vagy fix-commit (rögzítve: 2026-10-12).

**Why:** a Fejlesztő így döntött; a korábbi gyakorlat (bump a feature-commitban) a
`CLAUDE.md`-ben is állt, ezt váltja le.

**How to apply:** munka közben ne nyúlj a `plugin.json` verziójához; a forrásból futó
pluginhoz (`+dev.src.<hash>`) és a `--dev-install`-hoz sem kell bump. Release-kor a
`git cliff --bumped-version` szerinti verzió kerül a `plugin.json`-ba.
