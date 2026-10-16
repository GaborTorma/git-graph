# Listaelemek a markdown-diffben

A markdown-fájlok diffje a listák elemeit most elemenként párosítja. Ha két meglévő
elem közé új elem kerül, a változatlan elemek a helyükön maradnak, és az új elem is
oda kerül, ahová írták.

Eddig az egész lista egy bekezdésnek számított, mert az elemek közt nincs üres sor.
Ha hosszú új elem került a lista közepére, a régi és az új lista nem hasonlított
eléggé. Ilyenkor minden elem töröltnek és újnak látszott, a side-by-side nézetben
elcsúszva. A markdown-nézet sorrendje is csak az üres sorok mentén bontott, ezért az
új elem a lista végére csúszott.

A szerver blokkhatára most ugyanaz, mint a lapé: listaelem, címsor, vonal, táblázat,
idézet. A kódblokk belseje nem bomlik.

- [`[8d681c85]`](https://github.com/GaborTorma/git-graph/commit/8d681c85f6365d7bfef092f2f88db4091bbee8e8) · fix(diff): pair list items when new items are inserted between them
- [`[b213cd74]`](https://github.com/GaborTorma/git-graph/commit/b213cd747946fe4410f33fb1a5408f592edd8363) · fix(diff): keep a new list item in place in the markdown view
