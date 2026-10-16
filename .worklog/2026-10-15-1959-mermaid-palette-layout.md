# Mermaid-diagramok a lap palettáján

A markdown-diff Mermaid-diagramjai most a lap színeivel rajzolódnak, világos és
sötét témában is, `neo` stílusban és ELK-elrendezéssel; a keret a kártyák
hátterét kapja. A flowchart a forrás irányában és elforgatva is elkészül, és az
a változat kerül a lapra, amelyik a panelen jobban elfér: széles, egyoldalas
nézetben egy függőleges lánc vízszintes lesz, egymás melletti változatoknál
keskeny panelen függőleges marad. Szélességváltáskor a két kész rajz közül
választ, újrarajzolás nélkül.

A diagramok eddig a Mermaid saját színeivel, a lap stílusától elütve jelentek
meg, és egy hosszú lánc sokszor nem fért el a panelen.

A Mermaid 12.2.0-ra váltott, saját karcsú buildként (`scripts/mermaid.sh`,
3,7 MB): a hivatalos 5,5 MB-os build nem fér át a host-hídon, a határ mérve
3,67 és 5,08 MB között van. A nehéz függőségek helyén csonk áll, ezért a
mindmap, az architecture, a pie, a gitGraph, a packet, a radar, a treemap és a
képletes felirat kódnézetben marad, alatta a hibával.

Két kiemelési hiba is javult. Ha egy flowchart-sorban csak egy él célpontja
változott, a szó-kiemelés egy idegen csomópont feliratában jelölt egy betűt;
most csak a felirat-szöveg számít. Egy új felirat kiemelt darabja (pl. egy
vessző) eddig az első előfordulását színezte a rajzon, akár egy másik
csomópontban; most a saját csomópontjában keresi.

Nyitva maradt: a csonkolt diagramtípusok rajza.

- [`[e2739d11]`](https://github.com/GaborTorma/git-graph/commit/e2739d11265a4d1797b640adb3747526942e412f) · feat(diff): draw mermaid diagrams in the page palette with ELK layout
- [`[f4cbbbb2]`](https://github.com/GaborTorma/git-graph/commit/f4cbbbb283dcf9c8150e20841cbea832225144f1) · feat(diff): turn flowcharts to the direction that fits the panel
- [`[c009a08e]`](https://github.com/GaborTorma/git-graph/commit/c009a08e08a91ff2455dc5649796f9e609f0d301) · fix(diff): stop marking node labels when only an edge target changes
- [`[e125edc6]`](https://github.com/GaborTorma/git-graph/commit/e125edc68127ade688140fdb677f2254f1329507) · fix(diff): highlight a changed mermaid label only in its own node
