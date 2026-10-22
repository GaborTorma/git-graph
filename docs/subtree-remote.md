# Subtree-remote

Egy `git subtree split` / `push` remote-ja (pl. egy mappa külön repóba tükrözve) a
gráfban: a története a fő történettől független, és a commitjai a fő történet
commitjainak tükrei — ugyanaz a subject, szerző és author-dátum, más hash.

## Működés

### Független történet a chipen

Az ág chipje az alapághoz (amire az `origin/HEAD` mutat) mért távolságot mutatja
(`↑a ↓b`). Közös ős nélkül ez a két oldal összes commitja volna (pl. `↑4 ↓296`), ami
félrevezető: ilyenkor a távolság helyén, egy elválasztó után áthúzott lánc áll, a
tooltip pedig kimondja: „Külön történet: nincs közös őse az alapággal”. A helyi és a csak
remote-on élő ágra is érvényes.

A szerver (`branch_tracks`) a `for-each-ref` `%(ahead-behind:…)` számaiból dönt:
nincs közös ős ⇔ az alapág egyetlen commitja sem érhető el a refből, azaz a lemaradás
az alapág teljes commitszáma. Ehhez egyetlen `git rev-list --count <alapág>` kell, és az
is csak akkor fut, ha van ág, amelynek mindkét iránya nem nulla (a `claude-plugins`
repóban 0,01 s); refenkénti `merge-base` nincs.

## Követelmények

```gherkin
Feature: Subtree-remote a gráfban

  Rule: R-1 — A közös ős nélküli ág chipje nem mutat távolságot az alapághoz

    Scenario: Subtree-remote ága
      Given a "widgets/main" remote ágnak nincs közös őse az alapággal
      When a Fejlesztő megnézi a chipjét
      Then a chipen nincs "↑" és "↓" szakasz
      And egy elválasztó után áthúzott lánc ikon áll
      And a tooltip: "Külön történet: nincs közös őse az alapággal"

    Scenario: Szétvált, de rokon ág
      Given a "feat" ág 1 committal előrébb és 1 committal mögötte jár az alapágnak
      Then a chipje "↑1 ↓1"
```

## Használat

- A chip tooltipje (hover) mondja ki, hogy az ág külön történet.
