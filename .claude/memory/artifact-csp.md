---
name: artifact-csp
description: Az Artifact CSP-je — a külső fetch tilos; az eval, a blob-script, az import(blob:) és a CDN-lista scriptje fut; a data: nem
metadata:
  type: project
---

Az Artifact CSP-je HTTP-headerben jön (`<meta>` nincs). Mérve 2026-10-02-én (contract 0.2.66) és
2026-10-15-én (0.2.80), eldobható mérőlappal:

- `script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: <CDN-lista>` — megy: `eval`, `new Function`,
  `setTimeout(string)`, inline `<script>` (`textContent`), `<script src=blob:>`, `import(blob:)`, és a
  jsdelivr / cdnjs / unpkg `<script src>`-je is.
- Tiltott: `<script src=data:>`, `import(data:)` (`script-src-elem`).
- `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com` — inline `<style>` beszúrható.
- `connect-src 'self' <Google Fonts>` — külső `fetch`, saját szerver nem érhető el. A CDN-lista csak
  scriptre él, `fetch`-re nem.

**Why:** erre épül, hogy a lap kódja élőben jön (`page_code` → `import(blob:)`), és hogy a Mermaid
blobból fut ([[mermaid-build]]). Külső adat csak az MCP-n át jöhet ([[host-bridge-limits]]).

**How to apply:** lapkódot blobból vagy `new Function`-nal futtass, data-URI-s scriptet soha; külső
képet, adatot a Python ágyazzon be (pl. az avatar data URI-ként). A `tests/page/harness.py` `CSP`
konstansa ennek a mért része — ha a platform változik, ott is frissítsd.
