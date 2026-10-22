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

### Tükör-commitok a forráshoz kötve

A subtree-remote commitjai a fő történet commitjainak másolatai. A tükör-commit sora
halvány (mint a más worktree-é), a gráfpöttye üres karika, és a pöttyétől vékony,
szaggatott ív fut a forrás-commit pöttyéhez, a tükör sávjának színével. Ha a forrás
nem látszik (szűrő), az ív elmarad.

A párosítás a szerveren történik (`mark_mirrors`), a `graph_data`-ban a tükör-commit
`mirrorOf` mezője a forrás sha-ja. Tükör az a commit, amelynek
- van párja a látható commitok közt ugyanazzal a subjecttel, szerzővel és author-dátummal,
- a kettőnek nincs közös őse (nincs közös gyökér-commitjuk),
- és a pár az alapág történetéhez tartozik, a tükör nem.

A cherry-pick ezért nem tükör: a másolatnak közös őse van az eredetivel. A gyökereket a
lap commitjaiból számolja (egy menet); ahol a limit elvágja a történetet, ott a jelöltekre
`git rev-list --max-parents=0` dönt.

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

  Rule: R-2 — A tükör-commit halvány, és a forrásához kötve látszik

    Scenario: Subtree-remote commitja
      Given a "widgets/main" commitja a "main" egy commitjának tükre
      And a kettőnek nincs közös őse
      Then a tükör-commit sora halvány
      And a gráfpöttye üres karika
      And szaggatott ív köti a forrás-commit pöttyéhez

    Scenario: Cherry-pick
      Given a "pick" ágon egy "main"-commit cherry-pickje áll
      Then a cherry-pick sora nem halvány, és nem kap ívet
```

## Használat

- A chip tooltipje (hover) mondja ki, hogy az ág külön történet.
