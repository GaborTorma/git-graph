# git-graph

Git Graph-szerű commit-gráf generátor: **bármelyik repóból** egyetlen önálló
HTML fájl, amit a Claude `/git-graph` parancsa Artifactként publikál. A VS Code
`mhutchie.git-graph` elrendezését követi.

Használat és felépítés: [README.md](README.md).

## Repó térkép

| Útvonal | Mi ez |
| --- | --- |
| `gitgraph` | a teljes eszköz egyetlen fájlban: git-adatgyűjtés + beágyazott HTML/CSS/JS sablon |
| `gg` | symlink a `gitgraph`-ra (rövid alias) |
| `install.sh` | symlinkek: `~/.local/bin/{gitgraph,gg}`, `~/.claude/commands/git-graph.md` |
| `commands/git-graph.md` | a `/git-graph` slash command (publikálás/frissítés) |
| `docs/artifact-findings.md` | **mérési napló**: mit tud és mit nem az Artifact platform |
| `docs/mcp-plan.md` | terv az élő verzióhoz — jelenleg blokkolva |
| `probe/` | eldobható MCP-mérőeszköz a blokkoló újratesztelésére |

## Parancsok

```sh
./install.sh          # symlinkek felrakása (idempotens)
gg --help             # a teljes súgó
gg                    # az aktuális repó → <repó>/.git-graph/index.html
python3 gitgraph …    # symlink nélkül, közvetlenül
```

Nincs teszt-suite és nincs build — egyfájlos stdlib script. Változtatás után az
ellenőrzés: `gg` futtatása több repón (eltérő sávszámmal, merge-ekkel), és a
generált HTML megnyitása. A JS-t a fájlból kivágva `node --check`-kel lehet
szintaxis-ellenőrizni.

## Konvenciók

- **Nyelv**: magyar — kommentek, doksi, commit-body, a generált UI feliratai.
  A táblázat-fejlécek (`Graph / Description / Date / Author / Commit`) viszont
  **angolul** maradnak: az a Git Graph felismerhető arca.
- **Függőség**: kizárólag Python 3 stdlib. Ez szándékos — az eszköznek bárhol
  futnia kell, `pip install` nélkül. Ne hozz be libet.
- **Minden git-hívás olvas.** A script sosem módosít repót. Egyetlen kivétel a
  `.git/info/exclude` és a `.git/config` `gitgraph.*` kulcsai — mindkettő
  lokális, sosem commitolódik.
- **Verziókezelés**: SemVer, kézi `vX.Y.Z` tag, Conventional Commits.
- **Env**: a toolnak nincs env-függősége, ezért nincs `.env.example`. Ha a
  tunneles MCP-irány megvalósul (`docs/mcp-plan.md` B változat), a bearer token
  `.env`-be megy.

## Gotchák

- **Osztálynév-ütközés az egyfájlos oldalon**: a `.head` (táblázat-fejléc) egyszer
  már ráült a `badge head` elemre. A badge-variánsok azóta `ref-*` névtérben, a
  fejléc `.thead`. Rövid, generikus osztálynevet ne vezess be.
- **`<meta charset="utf-8">` a generált fájl legelső sora** — enélkül
  `file://`-ról latin-1-ként olvasódik.
- **Repónév az `origin` remote-ból**, nem a mappanévből (a mappa eltérhet:
  `auto-bpm` → `WristBPM`). Ez adja az Artifact címét is.
- **A kimenet mindig `<repó>/.git-graph/index.html`** — ez stabil szerződés az
  Artifact-frissítéssel. Ne tedd konfigurálhatóvá a default helyet.

Részletes platform-tanulságok (CSP, capabilities, MCP): `docs/artifact-findings.md`.
