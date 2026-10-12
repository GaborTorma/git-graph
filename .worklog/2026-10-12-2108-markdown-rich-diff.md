# Renderelt Markdown-diff

A `.md` fájlok diffje a lapon renderelve jelenik meg. A csak hozzáadott blokk
zöld, a csak törölt piros. Ha egy bekezdés, címsor vagy listaelem módosult, a
régi változata pirosan, alatta az új zölden látszik, a cserélt szavak
kiemelve. A táblázat és a kódblokk soronként színezett. A változatlan
blokkokból csak a változás szomszédai és az előtte álló legközelebbi címsor
látszanak, a többi `···`. A diffdoboz sarkában egy kapcsoló vált a nyers
diffre; a lap megjegyzi, és minden `.md` fájlra érvényes (#6).

A README, a CLAUDE.md és a mérési naplók nyers sordiffje nehezen olvasható:
a formázás elvész, és egy hosszú bekezdésben nem látszik, mi változott
érdemben.

A blokkokat csak a teljes szövegből lehet helyesen felépíteni, egy hunk
közepén a kódblokk vagy a lista el lenne vágva. Ezért a `file_diff` új
`full` paramétere a teljes fájlt adja egyetlen hunkban, és ezt a lap külön
gyorstárazza. Az összecsukás a lapon történik. A renderelő saját, kis
inline-feldolgozó, mert a lapra lib nem kerül. A szó-kiemelés helyét
jelölőkarakterek viszik át az inline formázáson, a végén `<mark>` lesz
belőlük. Egy hiba miatt a sor levágott eleje (a listajel, a `#`, a `>`) a
kiemelést is eltolta, ezért a levágás a kiemelés helyét is eltolja (`cut`).
A YAML front matter kódként jelenik meg, különben a záró `---` aláhúzott
címsort csinálna belőle.

Nyitva maradt, hogy ha egy commit kódkerítést ad hozzá vagy töröl, a két
változat blokkszerkezete eltér, és a renderelés pontatlan lehet; erre ott a
nyers nézet. Az élő appban a renderelt nézetet a Fejlesztő megnézte és
jóváhagyta; a kapcsolót ott még senki nem próbálta ki.

- [`[2d3f7f83]`](https://github.com/GaborTorma/git-graph/commit/2d3f7f83a58ac9dcd0cf1559aa2c8b2c5fe16779) · feat(page): render markdown file diffs with highlighted changes
