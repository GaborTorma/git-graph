# Mermaid-diagramok a markdown-diffben

A renderelt markdown-diffben a ```mermaid blokk diagramként jelenik meg, nem
kódként. A változott diagramnak a régi és az új változata látszik egymás
mellett (a középvonalon találkozva), ha elfér; bennük csak a változott elemek
színesek — a régiben pirosak az eltűntek, az újban zöldek az újak —, a
változott szöveg a diff szó-kiemelésével. Ha a változás csak törlés vagy csak
beszúrás, egy diagram elég. Side-by-side-ban a diagram és az előtte álló
változatlan címsor egyszer, a teljes szélességen. A diagram a lap témáját
követi; ha hibás, a kódnézet marad, alatta a Mermaid hibájával.

A doksik (CLAUDE.md, worklogok, PR-leírások) egyre több diagramot
tartalmaznak, kódként a változásuk nehezen olvasható volt (#45).

Előbb mérés: a Mermaid 11.17.2 egyfájlos buildje az Artifact CSP-je alatt
blobból is fut, CSP-sértés nélkül, és a 3,6 MB a host-hídon is átmegy (a
`page_code` válaszaként, ismételten ~270 ms). Ez a lap első külső
JS-függősége: vendorolt fájl a `page/vendor/` alatt, licenccel, verzióra
rögzítve (a CDN is működött volna, de akkor hálózat kellene a laphoz). A lap
csak diagramos diffnél kéri, a `page_code` új, opcionális `part: "mermaid"`
paraméterével — nem új tool, így a betöltőt nem kellett újrapublikálni. A
változott elemeket a két rajz összevetése adja: a csomópontok és élek
azonosítója (a rajzolás előtagja és a sorszám nélkül), ahol nincs, a
feliratuk. A lap-tesztek ezentúl az Artifact mért CSP-jével futnak.

Nyitva maradt: a szekvenciadiagram nyilainak iránycseréje és a csomópont
alakjának változása (azonos felirattal) nem jelölődik; a kiemelt szöveg csak
akkor, ha a rajzon egyben szerepel.

- [`[0bda5ccf]`](https://github.com/GaborTorma/git-graph/commit/0bda5ccf3c2829aa46e1c7915cef7b31679f6604) · docs(findings): record that mermaid runs under the artifact CSP
- [`[7d4c3222]`](https://github.com/GaborTorma/git-graph/commit/7d4c322244aa409d5c25f410fabdaa9e880b8e9f) · feat(diff): render mermaid diagrams in the markdown diff
- [`[ed71b5de]`](https://github.com/GaborTorma/git-graph/commit/ed71b5de0a7b8a52a501b12aa60a16df7902991b) · feat(diff): mark only the changed parts of mermaid diagrams
