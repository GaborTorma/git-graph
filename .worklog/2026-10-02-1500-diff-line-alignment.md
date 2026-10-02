# Igazított sorok a side-by-side diffben

A lenyitott fájl-diff side-by-side nézetében a régi és az új oldal hasonló
sorai most egymás mellé kerülnek. Egy beszúrt listaelem fölé üres hely jut a
bal oldalon, alatta a többi sor a párjával egy sorban áll, és a szó-kiemelés
csak a valóban változott részt jelöli (pl. az átírt sorszámot).

Eddig a törölt és a hozzáadott blokk sorai pozíció szerint párosodtak. A git
soronként, szó szerint diffel, ezért egy beszúrt elem átszámozza az alatta
lévőket, és az egész lista egyetlen törlés + hozzáadás blokká válik — a
pozíció szerinti párosítás így minden sort a szomszédja mellé tett.

A párosítás a Pythonban történik (`pair_lines`): a sorpárok hasonlósága
(`difflib`, legalább 60%) alapján sorrendtartó, a hasonlóságok összegét
maximalizáló illesztés, a horgonyok közti maradék pozíció szerint párosodik
(módosított sor). A lap ugyanezt a párosítást rajzolja, amiből a szó-kiemelés
készül. 100×100 sornál nagyobb blokkban a régi, pozíció szerinti párosítás
marad, hogy a lap ne lassuljon. Az egymás alatti nézet nem változott.

- [`[b813ba7d]`](https://github.com/GaborTorma/git-graph/commit/b813ba7d0850701ebf32aaf906cafab9e1b38b55) · fix(diff): align similar lines in the side-by-side view
