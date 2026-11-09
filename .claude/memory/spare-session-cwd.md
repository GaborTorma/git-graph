---
name: spare-session-cwd
description: "Az app új chathez előre melegített (spare) sessiont használ — a mod session.start-ja a ~/.claude/spares/spare-* mappában fut, nem a repóban"
metadata:
  node_type: memory
  type: project
  originSessionId: cb738e31-c1d5-4355-9475-6cb3a145821b
  modified: 2026-11-09T18:50:10.630Z
---

Az app (2.1.317) új chathez előre indít egy sessiont (`main.log`: `spare local_… starting`,
majd a chat indulásakor `spare … claimed`), a `~/.claude/spares/spare-<id>` mappában. A
transcriptben `{"type":"relocated","relocatedCwd":…}` sor jelzi. A mod `session.start`-ja a
spare indulásakor fut, a `$.session.cwd()` akkor még a spare mappája; relokációra nincs esemény.
A CLI SessionStart hookjai viszont már a végleges mappában futnak. Tünet (2026-11-09): új chatben
nem nyílt meg az Artifact, a `sessions.json`-ban nincs bejegyzés a sessionre.

**Why:** a `--mod-plan` a spare mappájában nem talál repót, és csendben kilép.

**How to apply:** a mod (`hooks/register.ts`, `settledCwd`) másodpercenként újranézi a mappát,
amíg `/.claude/spares/` van benne. Feltevés, élesben még nem mérve: a `$.session.cwd()` a
relokáció után a végleges mappát adja. Ha mégsem, a `relocated` sor a transcriptből olvasható.
Kapcsolódik: [[hook-publishes-mod-opens]], [[mod-limits]].
