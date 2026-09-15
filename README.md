# git-graph

Git Graph-szerű commit-gráf **bármelyik repóból**, egyetlen önálló HTML fájlba.
A VS Code [`mhutchie.git-graph`](https://marketplace.visualstudio.com/items?itemName=mhutchie.git-graph)
elrendezését és Dark+/Light+ palettáját követi.

```sh
gg                    # az aktuális repó → <repó>/.git-graph/index.html
gg --open             # …és megnyitja (Artifactot, ha az aktuális; különben a helyi fájlt)
gg ~/dev/masik-repo   # másik repó
gg --limit 200        # csak az utolsó 200 commit (alap: mind)
gg --out graf.html    # máshova (relatív út a hívás helyéhez)
```

## Telepítés

```sh
./install.sh
```

Symlinkeli a `gitgraph`-ot és a `gg`-t a `~/.local/bin`-be, a slash commandot a
`~/.claude/commands`-ba. Idempotens. Függősége nincs a Python 3 stdliben túl;
minden git-hívás **csak olvas**.

## Felépítés

| Útvonal | Mi |
| --- | --- |
| `gitgraph` | maga a script (~930 sor: adatgyűjtés + beágyazott HTML/CSS/JS sablon) |
| `gg` | symlink a `gitgraph`-ra — rövid alias |
| `install.sh` | symlinkek a PATH-ra és a Claude commands mappájába |
| `commands/git-graph.md` | `/git-graph` slash command: publikálja/frissíti az Artifact oldalt |
| `docs/artifact-findings.md` | **mit tud és mit nem az Artifact platform** — mérésekkel |
| `docs/mcp-plan.md` | terv az élő, magától frissülő verzióhoz (blokkolva, lásd findings) |
| `probe/` | eldobható MCP-mérőeszköz a blokkoló újratesztelésére |

## Kimenet

Mindig **ugyanoda**, a repón belülre: `<repó>/.git-graph/index.html`. Ez
szándékos — így ugyanabból a fájlból frissül ugyanaz az Artifact oldal.

A `.git-graph/` mappát a script a repó **lokális** ignore-listájába
(`.git/info/exclude`) veszi fel, nem a követett `.gitignore`-ba: az eszköz
idegen repókban is fut, ott pedig nem módosíthat commitolható fájlt.

## Artifact

A publikálás nem CLI — a Claude `/git-graph` parancsa végzi. A cím konvenció
szerint `<repónév> Git Graph` (a repónév az `origin` remote URL-jéből, mappanév
csak fallback). Ez alapján találja meg és **frissíti** a meglévő oldalt ahelyett,
hogy duplikátumot hozna létre. Repónként külön Artifact.

Publikálás után a parancs lefuttatja a `gg --set-artifact <url>`-t, ami a repó
**lokális** git configjába (`.git/config`, sosem commitolódik) elteszi:

| Kulcs | Mi |
| --- | --- |
| `gitgraph.artifact` | a közzétett oldal URL-je |
| `gitgraph.artifactHead` | a HEAD a publikálás pillanatában |

Ettől a `gg` minden futásnál kiírja a linket, és jelzi, ha azóta új commit jött
(`← ELAVULT`).

## `--open`

Az Artifact **pillanatkép**, a helyi fájl mindig friss — a `--open` ezért nem
vakon választ:

| Parancs | Mit nyit |
| --- | --- |
| `gg --open` | az Artifactot, **ha** az a mostani HEAD-et mutatja; különben a helyi fájlt |
| `gg --open artifact` | mindig az Artifactot (ha nincs megjegyezve, a helyit) |
| `gg --open local` | mindig a frissen generált helyi fájlt |

Mindegyik a **rendszer böngészőjében** nyit. A Claude Artifact-ablakát külső
folyamat nem tudja vezérelni — részletek és mérés: [docs/artifact-findings.md](docs/artifact-findings.md).

## Hogyan rajzol

A git saját lane-kiosztását követi: a commit abba a sávba ül, amelyik már rá
vár (a gyereke foglalta le); az első szülő viszi tovább a sávot, a további
(merge) szülők új vagy meglévő sávot kapnak. A vonal merge-nél rögtön a merge
commit alatt hajlik, leágazásnál közvetlenül a szülő fölött. Sávonként ciklikus
Git Graph-színek.
