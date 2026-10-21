---
name: host-bridge-hidden-frame
description: Rejtett Artifact-keretben a host-híd azonnal server_unavailable-t ad, és a lap időzítői sem futnak — a lap a megjelenéskor hív újra
metadata:
  type: project
---

Mérve 2026-10-04-én, 2026-10-06-án és 2026-10-12-én (contract 0.2.66–0.2.67):

- A keret rejtve van, amíg session-váltás közben egy **másik** Artifact látszik, vagy a session még nem
  rajzolódott be. Ugyanazon Artifact sessionjei között rejtés nélkül költözik
  ([[artifact-single-frame]]).
- Rejtve indított hívás 1–186 ms alatt `server_unavailable` (*„host:git-graph is not available while
  this artifact is hidden — try again once it is shown”*), `retryable`; a szerverig el sem jut. Ami a
  rejtés pillanatában már válaszolt, megérkezik; a régi kurzorral újrahívva azonnal a helyes állapot
  jön.
- Rejtve az időzítők sem futnak: a `requestAnimationFrame` 0,5–122 s-ig állt, egy 1 s-os `setTimeout`
  csak megjelenéskor lőtt.
- A rejtést nem jelzi `visibilitychange`, `focus` / `blur`, `pageshow`, és egyforma panelméretnél
  `resize` sem. Az `IntersectionObserver` igen (`0 → 1` megjelenéskor).

**Why:** 2026-10-12-én a betöltő az első `page_code`-hívását rejtve indította, nem próbálta újra, és a
lap ezzel a hibával állt meg.

**How to apply:** host-hívásnál `retryable` hibára újrapróba (a betöltő 1 s múlva hív újra, az a
megjelenéskor fut le). A lap hibánál megnézi, rajzol-e (egy rAF 250 ms-on belül); ha nem, csendben
vár. Mérőlap is várja meg a megjelenést.
