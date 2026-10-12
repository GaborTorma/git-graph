# Az Artifact panel újranyitása

Az `/git-graph:artifact-open` és az `/git-graph:artifact-publish` a megnyitás után
a `show_pane`-nel elő is hozza az artifact-panelt. Az `artifact-open` a
`git-graph --open-url`-lel dönti el, megnyitható-e a lap — ugyanúgy, mint a mod —,
és már nem ír semmit (eddig a `--publish` kiírta a lapot).

Egy sessionben már megnyitott lapra a modell `Artifact open`-je csak kártyát tett
a beszélgetésbe, a bezárt panel nem nyílt ki. Mérve: bezárt panelnél az `open`
utáni `show_pane` a lappal együtt megnyitja, akkor is, ha a lapot nem ez a
session publikálta (`docs/artifact-findings.md`).

- [`[61c1f937]`](https://github.com/GaborTorma/git-graph/commit/61c1f937b9622b948f329cf2e6720d342aaf8f93) · fix(skills): bring up the artifact pane when reopening the graph
