---
name: page-language-os-locale
description: A lapon a navigator.language az OS nyelve, nem a Claude appé — az app nyelvét csak a szerver olvashatja ki (config.json locale)
metadata:
  type: project
---

Mérve 2026-10-07-én (contract 0.2.72), mérőlappal. Az app beállítása `"locale": "en-US"`
(`~/Library/Application Support/Claude/config.json`), a macOS nyelve `hu-HU`:

- `navigator.language` `hu`, `navigator.languages` `["hu","hu-HU"]`, az `Intl` locale `hu`, a
  `timeZone` `Europe/Budapest`.
- A `document.documentElement.lang` üres; a `window.claude` típusaiban nincs locale.
- `userAgent`: `… Claude/2.26454.0 Chrome/152.0.7977.130 Electron/44.4.3 …`.

**Why:** a lap a Claude app nyelvét követi (CLAUDE.md „Megjelenés”), azt pedig a lap maga nem látja.

**How to apply:** az app nyelvét a Python adja (`config.json` `locale`); a `navigator.language` csak
tartalék.
