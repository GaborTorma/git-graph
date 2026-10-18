---
name: app-focus-sources
description: Honnan tudható, melyik session van előtérben — a Claude app session-JSON-jai (lastFocusedAt) és a main.log setFocusedSession sora; session-váltásra nincs hook
metadata:
  type: reference
---

Mérve 2026-10-04-én (Claude Code 2.1.286):

- **Session-fájlok**: `~/Library/Application Support/Claude/claude-code-sessions/<fiók>/<szervezet>/local_<id>.json`
  — `cwd`, `worktreePath`, `cliSessionId` (a hookok `session_id`-ja), `isArchived`, `lastFocusedAt`
  (ms). A repóban dolgozó, nem archivált sessionök közül a legnagyobb `lastFocusedAt` van előtérben.
  A `lastFocusedAt` 1–3 s késéssel, kötegelve íródik. 253 fájl, egyenként ~770 KB-ig: mindet
  beolvasni ~520 ms, `stat`-tal < 1 ms.
- **App-napló**: `~/Library/Logs/Claude/main.log`, váltásonként
  `[CCD] LocalSessions.setFocusedSession: sessionId=local_<id>` (előtte egy `sessionId=null`). A
  `lastFocusedAt`-hoz képest +1…+20 ms-mal már ott van. Másodpercre kerekít, ~10 MB-onként forog
  (`main.log` → `main1.log`, új inode). Csak az új sorokat olvasni < 0,1 ms; induláskor a végéből
  2 MB ~13 ms.
- **Hookok**: session-váltás a UI-ban semmit nem süt el (a 33 hookesemény közt nincs fókusz). A
  `UserPromptSubmit` a promptoló sessionből jön, `session_id`-val és `cwd`-vel; a `CwdChanged` egy
  Bash `cd`-re elsül, a Bash cwd-visszaállítására nem. Új hook a futó sessionökben azonnal él.
- A `Session Storage` leveldb `cmdk-navigation-history`-ja is tartja a sorrendet, de tömörítés után
  olvashatatlan — a JSON a stabilabb.
- Mindkettő belső formátum: ismeretlen formánál a kód nem dönt.

Kód: `git_graph/claude_app.py` (`focused_worktree`, `app_sessions`, `app_log_focus`). Kapcsolódik:
[[focused-worktree-design]], [[app-worktrees-json]].
