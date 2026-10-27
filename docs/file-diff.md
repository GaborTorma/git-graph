# Fájl-diff

A commit fájljainak diffje a részletek-panelben: szöveges diff, renderelt markdown, és a
képek képként.

## Működés

A részletek-panel fájlsorai lenyithatók (a sorra kattintva — a fájlnév maga a
GitHub-link marad): alatta a fájl diffje, a Claude app diff-nézetének mintájára —
sorszám, `+`/`−`, a cserélt soroknál a megváltozott szavak erősebb háttérrel, a
hunkok közt „N változatlan sor”. Az Uncommitted sornál az indexhez, a Stage-elt sornál a HEAD-hez képesti diff,
követetlen fájlnál a teljes tartalom hozzáadottként. Ha a diff legalább 1000 px
széles (széles Artifact-ablak), **side-by-side** nézetre vált:
balra a régi, jobbra az új oldal, a cserélt sorok egymás mellett — átméretezéskor
magától, újratöltés nélkül.

A lenyitott fájlsor és a diffje egy kerek kártya, mint a lenyitott commit: a sor
hover-színéből nyílik (a közepéről halványul, közben megjelenik a kerete és az árnyéka), a
tartalma 20 %-ról indulva jelenik meg. Ha a commit csukódik, a lenyitott fájljai vele együtt
csukódnak, és újranyitva csukva vannak.

A diff nincs a teljes adatban: a lap lenyitáskor kéri, fájlonként (a
`file_diff` toollal). A commitok diffje gyorstárazva, az
Uncommitted soré élőben frissül. Egy fájlból legfeljebb 3000 sor látszik.

### Képek

A képfájl (`png`, `jpg`/`jpeg`, `gif`, `webp`, `avif`, `svg`, `ico`, `bmp`) és a
markdown-nézet `![alt](út)` képe képként jelenik meg, a Mermaid-diagramok
elrendezésében. Az új vagy törölt kép egyedül, balra áll, zöld vagy piros bal csíkkal. A változott pár
a középvonalon találkozik (a régi piros, az új zöld kerettel); ha nem fér el, egymás
alá törik, mindkettő balra. A kép természetes méretben jelenik meg, legfeljebb a hasáb szélességéig;
mögötte sakktábla. Az SVG alapból kép, a sarokgombbal a kódja látszik.

A `file_diff` a képet data URI-ként adja (az Artifact CSP-je külső képet nem enged),
képenként legfeljebb 1 MB-ot; fölötte csak a méretet. A két oldal ugyanonnan jön, mint a
szöveges diffé. A markdown-képet a lap képenként kéri (`file_diff` `image`): az út a
markdown-fájl mappájához képest, a `/…` a repó gyökeréből értendő, oldalanként a saját
változatából. A külső (`http(s)://`) kép alt szöveg marad, a HTML `<img>` forrásként.

## Követelmények

```gherkin
Feature: A fájl-diff: képek és a lenyitott kártya

  Rule: R-1 — A képfájl diffje képet mutat, nem „Bináris fájl.” feliratot

    Scenario Outline: Új és törölt kép
      Given egy commit <változás> a "logo.png" fájlt
      When a Fejlesztő kinyitja a fájl diffjét
      Then a kép egyedül, balra jelenik meg
      And a bal csíkja <szín>

      Examples:
        | változás  | szín  |
        | hozzáadja | zöld  |
        | törli     | piros |

    Scenario: Változott kép side-by-side nézetben
      Given egy commit módosítja a "logo.png" fájlt
      And a diff legalább 1000 px széles
      When a Fejlesztő kinyitja a fájl diffjét
      Then a régi kép a bal félen jobbra igazodik, piros kerettel
      And az új kép a jobb félen balra igazodik, zöld kerettel

    Scenario: A pár nem fér el egymás mellett
      Given egy commit módosítja a "screenshot.png" fájlt
      And a két kép együtt szélesebb a diffnél
      When a Fejlesztő kinyitja a fájl diffjét
      Then a két kép egymás alá kerül, mindkettő balra igazodik
      And a régi az első

    Scenario: Átnevezett, változatlan kép
      Given egy commit tartalomváltozás nélkül átnevezi a "logo.png" fájlt
      When a Fejlesztő kinyitja a fájl diffjét
      Then a kép egyszer jelenik meg, semleges kerettel

  Rule: R-2 — A kép megjelenése: természetes méret, sakktábla, méretkorlát

    Scenario: Átlátszó kép sötét témában
      Given a "logo.png" átlátszó hátterű
      And a lap sötét témában fut
      When a Fejlesztő kinyitja a fájl diffjét
      Then a kép mögött sakktábla-minta áll

    Scenario: Széles kép
      Given a kép szélesebb a hasábnál
      Then a kép a hasáb szélességére kicsinyedik
      But a keskeny kép nem nő a természetes mérete fölé

    Scenario: Túl nagy kép
      Given a "photo.jpg" 2,4 MB
      When a Fejlesztő kinyitja a fájl diffjét
      Then a kép helyén ez áll: "Túl nagy kép (2,4 MB)."

  Rule: R-3 — Az SVG-fájl alapból kép, a kódja egy gombbal látszik

    Scenario: Nézetváltás
      Given egy commit módosítja az "icon.svg" fájlt
      When a Fejlesztő kinyitja a fájl diffjét
      Then a régi és az új SVG képként jelenik meg, a képfájl párjának elrendezésében
      When a Fejlesztő a kódnézet gombjára kattint
      Then a szöveges diff jelenik meg

  Rule: R-4 — A markdown-kép a markdown-nézetben képként jelenik meg, oldalanként a saját változatából

    Background:
      Given a "docs/README.md" tartalmaz egy "![gráf](img/graph.png)" sort

    Scenario: A kép és a markdown is változik
      Given egy commit módosítja a "docs/img/graph.png" fájlt és a "docs/README.md" fájlt
      When a Fejlesztő a markdown-nézetben kinyitja a "docs/README.md" diffjét
      Then a régi oldalon a szülő commit képe látszik
      And az új oldalon a commit képe látszik

    Scenario Outline: Útvonal-feloldás
      Given a hivatkozás "<hivatkozás>"
      Then a kép a "<fájl>" fájlból jön

      Examples:
        | hivatkozás          | fájl                |
        | img/graph.png       | docs/img/graph.png  |
        | ../logo.svg         | logo.svg            |
        | /docs/img/graph.png | docs/img/graph.png  |

    Scenario: Nem commitolt és stage-elt sor
      Given a "docs/img/graph.png" a lemezen módosult, de nincs stage-elve
      When a Fejlesztő az Uncommitted sor markdown-nézetében kinyitja a diffet
      Then a régi oldalon az indexbeli kép látszik
      And az új oldalon a lemezen lévő kép látszik

    Scenario: Hiányzó kép
      Given a "docs/img/graph.png" a régi változatban nincs meg
      Then a régi oldalon a "gráf" alt szöveg látszik, "nem található" jelöléssel

    Scenario: Külső kép
      Given a hivatkozás "https://img.shields.io/badge/x-y-green"
      Then az alt szöveg látszik, és a szerver nem tölt le semmit

    Scenario: Kép a szöveg sorában
      Given egy bekezdés sorában kép áll szöveg között
      Then a kép a sorban, a helyén jelenik meg, lebegés nélkül

    Scenario: Csak képből álló bekezdés
      Given egy bekezdés csak a "![gráf](img/graph.png)" képből áll
      And a commit módosítja a "docs/img/graph.png" fájlt
      Then a kép a képfájl párjának elrendezésében jelenik meg (R-1)

    Scenario: HTML-kép
      Given a markdownban egy "<img src=\"img/graph.png\" align=\"left\">" HTML-blokk áll
      Then a blokk forrásként, kódként jelenik meg

  Rule: R-5 — A lenyitott fájl kártya, mint a commit: a hoverből nyílik, a committal csukódik

    Scenario: Nyitás a hoverből
      Given az egér a fájlsoron áll
      When a Fejlesztő rákattint
      Then a sor és a lenyíló diff hover-színű, és a közepéről a széléig halványul
      And közben megjelenik a kerek kerete és az árnyéka, a nyitással együtt érve véget

    Scenario: A commit csukása a fájlt is csukja
      Given egy commit lenyitva, benne egy lenyitott fájllal
      When a Fejlesztő becsukja a commitot
      Then a fájl diffje a committal együtt csukódik
      And a commit újranyitásakor a fájl csukva van
```

## Használat

- A részletek-panelben a fájlsorra kattintva nyílik és csukódik a diff; a fájlnév a
  GitHub-link.
- Markdown-fájlnál a jobb felső kétgombos kapcsoló vált a renderelt és a nyers diff között;
  SVG-nél a kép és a kód között. A lap mindkettőt megjegyzi.
- A side-by-side nézethez szélesítsd az Artifact ablakát (a diff legalább 1000 px).
