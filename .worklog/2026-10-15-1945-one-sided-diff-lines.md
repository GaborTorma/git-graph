# Egyoldalú változások és újratördelés a diffben

A fájl-diff most pontosabban mutatja, mi változott egy sorban. Ha egy változás
csak beszúrás vagy csak törlés, az érintetlen oldal változatlanként látszik: a
csak átkerült (újratördelt) sor jel és szín nélkül, a szavanként változott
semleges háttérrel és szó-kiemeléssel, az egészében új vagy törölt sor teljes
zölddel vagy pirossal. A tiszta újratördelés nem számít változásnak, a
markdown-nézetben az ilyen blokk el is marad. Side-by-side-ban a két oldal
felülről egymás mellé kerül, a pár nélküli törölt és új sorok is egymás mellé.

Eddig egy újratördelt bekezdés minden sora `+` / `−` jelet kapott, egy
táblázatban egy szavas változás teljes piros-zöld sort adott, ha a szomszédja
cserélődött, és a side-by-side lyukakat hagyott.

A markdown-nézetben egy bekezdés vagy listaelem egy egységként színeződik,
ugyanúgy egymás alatt és side-by-side is; a listaelem folytatósorának
behúzása nem számít változásnak. A táblázat változott utolsó sora a
táblázatában marad. A nézetváltó gomb lebegő gomb lett a jobb felső sarokban,
nem tolja el a tartalmat.

Utána a sorok kinézetéről (`styles`) és a markdown-sorrendről a szerver dönt
egyszer, a lap ezt rajzolja ki; a lap-tesztek közös fixture-ökön és
segédfüggvényeken át olvasnak.

- [`[df79a185]`](https://github.com/GaborTorma/git-graph/commit/df79a185fb2244863101f73f8ad797a8920344d5) · fix(diff): mark a single one-sided row even when its neighbours were replaced
- [`[cf16175b]`](https://github.com/GaborTorma/git-graph/commit/cf16175b02ad9ef7f1f1b11a7d94e733b034a727) · fix(diff): ignore the indentation of a wrapped list line
- [`[a2ca0a77]`](https://github.com/GaborTorma/git-graph/commit/a2ca0a77121e083a303a35901f8ccb64b058c550) · fix(diff): treat a markdown block as one unit when colouring changes
- [`[47f015e6]`](https://github.com/GaborTorma/git-graph/commit/47f015e6404bf0e7ac0fea2d7cae78dd4efe51d0) · fix(diff): put unpaired old and new rows next to each other side by side
- [`[4f4a130f]`](https://github.com/GaborTorma/git-graph/commit/4f4a130fe0d0bdbce46c8028e4d8ad2864348cff) · fix(diff): keep a changed last table row in its table
- [`[ff640b54]`](https://github.com/GaborTorma/git-graph/commit/ff640b54ef4d8586b3f67028c6c12b7dee55e3d4) · fix(diff): start the side-by-side view below the view toggle
- [`[3b809103]`](https://github.com/GaborTorma/git-graph/commit/3b809103c7808ba280a41a607b2bb7f792ce95b5) · fix(diff): keep a leading gap marker beside the view toggle
- [`[94639af5]`](https://github.com/GaborTorma/git-graph/commit/94639af5f194117323a6a822868a83abaa0d3814) · fix(diff): float the markdown view toggle over the diff
- [`[8fc66477]`](https://github.com/GaborTorma/git-graph/commit/8fc6647707c99f9cc5a25b184dcee317c9e2934a) · fix(diff): keep a wholly new line fully coloured in a one-sided change
- [`[a8d22731]`](https://github.com/GaborTorma/git-graph/commit/a8d227311c27b0a6b1c1c5c8537f2751273aaed2) · fix(diff): line up a one-sided change from the top side by side
- [`[aee31a0c]`](https://github.com/GaborTorma/git-graph/commit/aee31a0c03cc8029ca0d99d02c8dac81d90cb79b) · fix(diff): show a pure rewrap as unchanged lines
- [`[f8cd43c7]`](https://github.com/GaborTorma/git-graph/commit/f8cd43c7e1a8147c29510e672d779749e1479429) · fix(diff): show a moved-only line of a one-sided change as unchanged
- [`[f5050854]`](https://github.com/GaborTorma/git-graph/commit/f5050854655a701e7fd36ed081fa640c0c80f4f6) · fix(diff): hide rewrap-only blocks in the markdown view
- [`[c4b4f271]`](https://github.com/GaborTorma/git-graph/commit/c4b4f271ac5c0cc3c164035d8372042aebef80a5) · simplify(diff): line up one-sided runs through the general pairing path
- [`[7f3c4122]`](https://github.com/GaborTorma/git-graph/commit/7f3c412215f7f370d2f2503d52befb7457871b3a) · simplify(diff): compute each hunk's one-sided lines once
- [`[c1e78a21]`](https://github.com/GaborTorma/git-graph/commit/c1e78a21e7990e253fa773452ea050734adef561) · simplify(diff): build the markdown partner lookup once
- [`[805058d3]`](https://github.com/GaborTorma/git-graph/commit/805058d3b903c92d02fbeabbbd58896e6ccb593c) · simplify(diff): look up a line's markdown block in a map
- [`[7420409b]`](https://github.com/GaborTorma/git-graph/commit/7420409b6459c614cb0c2b25b55df14662b11b3e) · simplify(diff): decide each line's look once, from an explicit state
- [`[b622dd51]`](https://github.com/GaborTorma/git-graph/commit/b622dd51452746bfa6c49d57730b47c4233f216b) · simplify(diff): order markdown change lines once instead of moving blocks
- [`[3f4365f2]`](https://github.com/GaborTorma/git-graph/commit/3f4365f2f2219183506c6d2ca5ed0c4a3af9dd72) · simplify(diff): skip the row-height sync while the side-by-side is hidden
- [`[8629abcf]`](https://github.com/GaborTorma/git-graph/commit/8629abcf96f00e0abf356060d88ce2b36f7b159e) · simplify(diff): share the row view of markdown code blocks and tables
- [`[0386cd66]`](https://github.com/GaborTorma/git-graph/commit/0386cd662a332cfa8bca9647efa55a99cc4c67f4) · simplify(diff): tokenize each prose line once
- [`[c04b7c45]`](https://github.com/GaborTorma/git-graph/commit/c04b7c45643742a78a29b3fca93bc7af7ac3d9cf) · simplify(test): share the page tests' fixture commits and readers
- [`[b9d56d19]`](https://github.com/GaborTorma/git-graph/commit/b9d56d1928efc757bfce90e6912bab6936f76d8f) · simplify(test): read prose diff lines and their marks through helpers
- [`[62d7ee36]`](https://github.com/GaborTorma/git-graph/commit/62d7ee36aed454469f2a21e0736d69a1308348b7) · simplify(diff): build each markdown block's views once
- [`[93869eb9]`](https://github.com/GaborTorma/git-graph/commit/93869eb9fd8b114e404ee10fe9655f9119888cdf) · simplify(diff): let the server decide each line's look and the markdown order
