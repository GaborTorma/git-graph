---
name: artifact-capabilities
description: Melyik Artifact capability él a fiókon, mit old fel az „AI-powered artifacts” kapcsoló, és miért nem jó a sample a sessionnel beszélni
metadata:
  type: project
---

- 2026-08-25-én (contract 0.2.23) a fiókon: `artifact`, `downloads`, `mcp`, `self`; az `assets`
  `unavailable_to_account` volt.
- 2026-09-15-én (0.2.49): `artifact, assets, db, downloads, mcp, room, sample, self`.
- Az `artifact` (a lap újrapublikálja magát) és a `downloads` deployja átment.
- *claude.ai → Settings → Visuals → AI-powered artifacts*: azt oldja fel, hogy a publikált lap elérje
  a claude.ai konnektorokat. Az `assets`-et és a `host:`-ot nem érinti.
- A `sample` állapot nélküli modellhívás, a futó sessionről nem tud. A lapról a sessionnek a
  `comments` capability szól ([[comments-send-to-claude]]).
- Mérőlapnál a `db` a visszacsatolás: a lap a saját `db`-jébe írja az eredményt, a session
  `ArtifactData`-val olvassa.

**Why:** a capability-lista fiókonként és idővel változik, a doksi pedig több ponton feltételes
módban fogalmaz ([[dig-before-declaring-limits]]).

**How to apply:** capability-re épülő terv előtt eldobható mérőlappal ellenőrizd; a deploy válasza
(`422: capabilities.<x>: unavailable`) a mérvadó, nem a doksi.

**„outside the scope you consented to. Reload to review.”** (`not_in_manifest`): a lap
deklarációjából hiányzik a tool. A néző hozzájárulása szerverenként szól (`mcp:host:git-graph`),
nem toolonként, ezért az újratöltés nem segít. Mérve 2026-11-04-én és 2026-11-09-én: a Lesown
lapján 5 tool volt, a `git-graph.artifactCaps` mégis a 7 toolos hasht őrizte (a `--published`
a deklarálás sikerétől függetlenül írja). Ellenőrzés: `Artifact read` → `artifact-stored-declaration`;
javítás: `Artifact publish` a lappal és a teljes `capabilities`-szel, utána `--published`.
