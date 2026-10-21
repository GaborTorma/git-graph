---
name: host-bridge-long-poll
description: A host egy callTool-t ≥50 s-ig nyitva tart; sűrű kérdezésre rate_limited (~20 hívás után); a lap megszakítása nem jut el a szerverhez
metadata:
  type: project
---

Mérve 2026-10-04-én és 2026-10-06-án (contract 0.2.67), műszerezett dev-példánnyal:

- Egy `callTool` legalább 50 s-ig nyitva marad (50 013 ms után is `ok`) → a `changes` `wait` felső
  határa 50 s.
- Gyors váltogatásnál, váltásonként 2 s-ig 250 ms-onként kérdezve ~20 hívás után a host visszafogta a
  hívásokat (`rate_limited`, `durationMs: 0`). Váltásonként egy hívással nem jött elő.
- A lap megszakítása (`callTool` `signal`) a lapon pontos (`cancelled`), de a szerver nem kap
  `notifications/cancelled`-et: a várakozó a határidejéig fut. Lap-újratöltés sem zárja le.
- Nyitott várakozók mellett a rövid hívások kiszolgálódnak; a nyitott hívás túléli, ha a keret
  sessionök között költözik.

**Why:** ezért váltotta egyetlen nyitott `changes` long-poll a 2 s-os pollozást és a külön
fókusz-hívást (#29).

**How to apply:** ne kérdezz sűrűn a lapról; az árva várakozót a szerver határideje zárja, és
`WAITERS_MAX` fölött nem vár. A mai felépítés: [[focused-worktree-design]].
