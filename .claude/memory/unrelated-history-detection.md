---
name: unrelated-history-detection
description: Közös ős nélküli történet (subtree-remote) felismerése merge-base nélkül — a chipen és a tükör-commitoknál
metadata:
  type: project
---

Két mért-olcsó egyenértékűség, refenkénti `git merge-base` helyett:

- **Ág ↔ alapág**: nincs közös ős ⇔ a `%(ahead-behind:<base>)` lemaradása = `git rev-list --count <base>`
  (az alapág egyetlen commitja sem érhető el). Egy számlálás, csak ha van jelölt (mindkét irány > 0);
  a `claude-plugins` repóban 0,01 s. → `branch_tracks`, `unrelated: true`.
- **Commit ↔ commit**: van közös ős ⇔ van közös gyökér-commitjuk. A gyökérhalmaz a látható commitokból
  egy visszafelé menetben (a `--date-order` miatt a szülő a gyerek után jön); a limit elvágta
  történetnél `rev-list --max-parents=0`. → `mark_mirrors`, `mirrorOf`.

**Why:** a tükör forrása lehet pusholatlan (a `claude-plugins` `main`-je 16-tal járt az `origin/main`
előtt), ezért az „alapágból elérhető” feltétel kevés volt; a gyökér-alapú döntés a pusholatlant is fogja.
**How to apply:** új „rokon-e” kérdésnél ezeket használd; a cherry-pick közös ősű, nem tükör.
