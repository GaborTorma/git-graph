---
name: mermaid-build
description: "A Mermaid az Artifact CSP-je alatt blobból fut; a 12.x hivatalos buildje nem fér át a hídon, ezért karcsú build (csonkokkal, ELK-kal)"
metadata:
  node_type: memory
  type: project
  originSessionId: 6c217818-29d6-4775-994b-afdcea10d6d8
  modified: 2026-10-26T08:07:44.800Z
---

Mérve 2026-10-15-én (Claude 2.37337.1, contract 0.2.80), mérőlappal, Mermaid 11.17.2-vel:

- Fut `<script src=blob:>`-bal (betöltés 261 ms), `new Function`-nal (290 ms) és CDN-ről (300 ms); a
  render 82–229 ms. CSP-sértés nincs: az SVG-be `<style>`-t ír, `eval`-t nem használ.
- A hibás diagram dob (`Parse error on line 3: …`) → erre épül a kódnézetre visszaeső ág.
- Ugyanez helyben, az Artifact CSP-jével kiszolgálva headless Chromiumban is zöld → a `tests/page/` a
  CSP-t is lefedi ([[artifact-csp]]).

Döntés (2026-10-15): a hivatalos `dist/mermaid.min.js` (12.x: 5,5 MB) nem fér át a hídon
([[host-bridge-response-size]]), ezért karcsú build (`scripts/mermaid.sh`, esbuild): a `cytoscape`, a
`katex` és a `@mermaid-js/parser` helyén csonk (ezeknél kódnézet és hiba), az ELK benne van (a
3,7 MB-ból 1,44 MB az `elkjs`). A `@mermaid-js/layout-elk` (a 11-hez) a rajzoló saját másolatát hozza
(~3,5 MB, 5,08 MB-os build) → elvetve; a 12-ben az ELK beépített.

ER-diagram (mérve 2026-10-26): az ELK a vonalat az entitás után 16 egységgel fordítja, a kör a
fordulóra kerül; felirat nélküli kapcsolatnál a két vég jelölői össze is érnek. A dagre ezt elkerüli,
de ferde élekkel, szélesebben rajzol → elvetve, az ER is ELK. Kipróbálva és elvetve:
- `edgeNodeBetweenLayers` a gyökéren (configból nem állítható, csak forrásban): hat, de a felirat
  is külön ELK-réteg, körülötte is nő a hely — a Fejlesztő ezt nem kérte.
- csomópontonként `elk.margins`, `elk.spacing.individual`, `edgeNodeBetweenLayers`: az ELK nem veszi
  figyelembe (a vonal hossza 16 marad).
Ami lett: a `scripts/mermaid.sh` esbuild-pluginja az ER-entitást az ELK-nak `ER_STUB`-bal (30)
magasabbnak adja fent és lent, utána a dobozt visszaállítja, a vonal végét a dobozig húzza
(`erStubs`) → 46 egység egyenes, a felirat körül az eredeti hely. A flowchart nem kapja.

**Why:** a Mermaid a lap első külső JS-függősége, és a host-híd mérete a szűk keresztmetszet.

**How to apply:** frissítésnél a `scripts/mermaid.sh` verziója, futtatás, és a verzió a `page.py`
kommentjében is; a build maradjon a mért határ alatt.
