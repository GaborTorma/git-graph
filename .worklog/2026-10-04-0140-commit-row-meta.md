# A commit-sor vége: idő, avatar, diff

A commit-sor vége `idő (avatar) [fájl | + | −]` lett: a szerző neve helyett
avatar vagy monogram (a név tooltipben), mellette egy fix széles, színes
diff-címke a fájlok számával és a hozzáadott / törölt sorokkal (99 fölött
`99⁺`, 999 fölött `1k`, a pontos számok tooltipben). A hash lekerült a
sorról: a kinyitott commit fejében másolható, és a keresés is megtalálja.

A sor a szövegoszlop szélességétől függően fix határokkal vált: 480 px
fölött egysoros, alatta kétsoros (lent a blokk), a lista 320 px-es
szövegoszlop alatt nem szűkül tovább. A badge-es sor mérve kétsoros, ha a
tárgy szorulna; ha a blokk a badge-ek mellé sem fér, egészben a harmadik
sorba kerül — eleme nem tűnik el. A tooltip egyetlen fix buborék a lap
fölött, így a lista széle és a ragadós fejléc sem vágja le.

Sok iteráció után dőlt el (soronkénti mérés, ki-be kapcsoló diff, badge-
szerű keret — ezek visszakerültek); a végső változatban a fix határok és az
átlátszatlan cellák maradtak. Egy `/simplify` kör a sorokba ágyazott
avatar-képeket egyetlen stíluslapba tette, és több ismételt munkát kivett.

- [`[c98465b4]`](https://github.com/GaborTorma/git-graph/commit/c98465b4c32086144966f27b91b2a138823db13c) · feat(page): show the commit's total changes before the author
- [`[bbe9f23f]`](https://github.com/GaborTorma/git-graph/commit/bbe9f23fdd22b9556de2e5df8ae8d2261f48c406) · feat(page): switch a squeezed commit row to two lines
- [`[6480b9d3]`](https://github.com/GaborTorma/git-graph/commit/6480b9d36bd606d25a25e2056b3f4fe3a139acbd) · fix(page): move the meta block below the subject in a squeezed row
- [`[70a23ac5]`](https://github.com/GaborTorma/git-graph/commit/70a23ac5caf479b9584f1aefc08043c89be80599) · style(page): right-align the badges in a multi-line row
- [`[41c1ea02]`](https://github.com/GaborTorma/git-graph/commit/41c1ea02095601d9aec9ea2b8a8bdf2f8fa4efdd) · fix(page): keep a squeezed row with badges at two lines
- [`[04a674ce]`](https://github.com/GaborTorma/git-graph/commit/04a674ce7162269a30f973e65dbefa4637f897ac) · fix(page): tighten the row meta and fit it beside the badges
- [`[51ef76ec]`](https://github.com/GaborTorma/git-graph/commit/51ef76ec73a7bc30e448b36407b2354142e2aadc) · fix(page): drop the author when it would overlap the diff in a two-line row
- [`[0725a4af]`](https://github.com/GaborTorma/git-graph/commit/0725a4afb5cefc23a819611166a4bf66b8f9ba60) · fix(page): put the badges on the second line of a two-line row
- [`[eb69389d]`](https://github.com/GaborTorma/git-graph/commit/eb69389d4835f43e4c723b2961b6ff0f8ba1191a) · fix(page): drop the diff from a one-line row when it clips the subject
- [`[77331a5a]`](https://github.com/GaborTorma/git-graph/commit/77331a5ab6178edfcc42a27f8bc2e3ca77f19421) · style(page): show the row diff as colored tags after the hash
- [`[8820be46]`](https://github.com/GaborTorma/git-graph/commit/8820be4651e43064949f1f623445273a12f66d83) · style(page): shrink the row diff tags to a fixed width
- [`[bee5d8e3]`](https://github.com/GaborTorma/git-graph/commit/bee5d8e3406b46abab4abccdc643f0d4c8a7852b) · feat(page): show the author as an avatar or initials on the commit row
- [`[c9901cfa]`](https://github.com/GaborTorma/git-graph/commit/c9901cfafcc057aca955bbf1c9c86c2ff7013155) · fix(page): keep the row diff after the hash and show it on all rows or none
- [`[2d02e872]`](https://github.com/GaborTorma/git-graph/commit/2d02e872559d3141c0cbfc9bb46e64b4a36a0a40) · fix(page): keep the diff on multi-line rows and switch to two lines sooner
- [`[c1ff5f49]`](https://github.com/GaborTorma/git-graph/commit/c1ff5f49031cc9f17369f8a467aad9d189e817d5) · style(page): put the avatar between time and hash, right-align the diff
- [`[b5a8120d]`](https://github.com/GaborTorma/git-graph/commit/b5a8120d5f384d41a6b940f598c739ca62e20a07) · fix(page): hide the row meta by priority time, avatar, diff, hash
- [`[bf04613b]`](https://github.com/GaborTorma/git-graph/commit/bf04613b4311ff0e4bb11254385da6178c55c9bc) · style(page): narrow the row diff to three digits per side
- [`[c810264d]`](https://github.com/GaborTorma/git-graph/commit/c810264ddd23687c9e7ad9c1f498782315ade130) · style(page): split the row diff tag by digit count, drop zero sides
- [`[d63ccd63]`](https://github.com/GaborTorma/git-graph/commit/d63ccd637f7365932dfaf1c98859e2e3f79e31ef) · style(page): right-align both halves of the row diff tag
- [`[df767a68]`](https://github.com/GaborTorma/git-graph/commit/df767a684fa589cbc7055bea2fcc2b8cd334043d) · style(page): split the row diff tag in fixed halves, show zeros again
- [`[527c4b9e]`](https://github.com/GaborTorma/git-graph/commit/527c4b9eda5705a6dc57c95a771302cf9ddd14f2) · feat(page): add the file count to the row diff tag and drop the row hash
- [`[45f060df]`](https://github.com/GaborTorma/git-graph/commit/45f060dfb0f601d3c94fd0550c373d5f65530542) · style(page): keep the 99+ plus inside the tag and at regular weight
- [`[63a09ad4]`](https://github.com/GaborTorma/git-graph/commit/63a09ad40335e9c14e0a4c5d11aa840bd6916d17) · feat(page): bring the hash back to the commit row
- [`[fea81828]`](https://github.com/GaborTorma/git-graph/commit/fea81828356fa02177d894f36e07442ff37946f9) · style(page): move the hash to the end of the commit row
- [`[15a97b83]`](https://github.com/GaborTorma/git-graph/commit/15a97b8311fad41976599246d17bf078f4de7aaf) · style(page): give the row diff tag the badge height and outline
- [`[746be608]`](https://github.com/GaborTorma/git-graph/commit/746be608502de59ce19a442150990546dbd9ff2f) · Revert "style(page): give the row diff tag the badge height and outline"
- [`[81e0ccb9]`](https://github.com/GaborTorma/git-graph/commit/81e0ccb9f94f932391a92f6a5dbebb98d0b12ec0) · Revert "style(page): move the hash to the end of the commit row"
- [`[74d5ffbb]`](https://github.com/GaborTorma/git-graph/commit/74d5ffbbdb03f424f74a106269bb243a6d5fac0d) · Reapply "style(page): move the hash to the end of the commit row"
- [`[2f937902]`](https://github.com/GaborTorma/git-graph/commit/2f937902669ff7dbb885b551ee79c6b1cd4ec1f3) · feat(page): show the row diff details in a hover tooltip
- [`[172af0be]`](https://github.com/GaborTorma/git-graph/commit/172af0beee536af8ea01df76ff3c319e8bde10a1) · style(page): tone down the row tooltips
- [`[7ec1bf23]`](https://github.com/GaborTorma/git-graph/commit/7ec1bf233c1465f8c56792d5d5c4f1507b59d20d) · style(page): separate the file count with a comma in the diff tooltip
- [`[e34842f3]`](https://github.com/GaborTorma/git-graph/commit/e34842f3b75b99030d8fedf2e7d25bafd5659942) · fix(page): keep the row tooltips from opening a horizontal scroll
- [`[cab52746]`](https://github.com/GaborTorma/git-graph/commit/cab52746b512727de87d2796774b47ad569379ef) · fix(page): show the row tooltips inside the row, left of the element
- [`[9e19b7e1]`](https://github.com/GaborTorma/git-graph/commit/9e19b7e1861d1fb351bb59698a79cf51a6213641) · fix(page): lift the hovered row so its tooltip stays above the neighbours
- [`[62f22ab1]`](https://github.com/GaborTorma/git-graph/commit/62f22ab162f54bde885a2b7460b3f9697abc28e9) · fix(page): render the row tooltips as one fixed bubble above everything
- [`[3ce50c14]`](https://github.com/GaborTorma/git-graph/commit/3ce50c14eeec603abf480d788532d95da9e650b3) · feat(page): lay out commit rows by fixed text column widths
- [`[589d85d4]`](https://github.com/GaborTorma/git-graph/commit/589d85d4ca80e06f639e17e678a41ec3f19e6c01) · style(page): never show the hash on a two-line row
- [`[efa26c55]`](https://github.com/GaborTorma/git-graph/commit/efa26c554997a47d9a0a0660ea465faf8db56e2f) · fix(page): let a badge row drop its hash before going two-line
- [`[674824c1]`](https://github.com/GaborTorma/git-graph/commit/674824c1f2203aaf226db83766ab982ffd14196a) · feat(page): drop the hash from the commit row
- [`[1104de6c]`](https://github.com/GaborTorma/git-graph/commit/1104de6c2b1d1b7a26ab9fced634121eb09e6518) · feat(page): move the row meta to a third line instead of dropping parts
- [`[4f5af348]`](https://github.com/GaborTorma/git-graph/commit/4f5af348af0e4e587fc669e9b6398a5a46614fcd) · style(page): give two- and three-line rows two more pixels
- [`[5003cb27]`](https://github.com/GaborTorma/git-graph/commit/5003cb27f367fdf074f58e760c401d4e8ed74c19) · style(page): give two- and three-line rows one more pixel
- [`[b20c04d7]`](https://github.com/GaborTorma/git-graph/commit/b20c04d72fca4b3b297a6e72535afc65c778ba04) · refactor(page): trim repeated work and leftovers from the redesign
- [`[e351b664]`](https://github.com/GaborTorma/git-graph/commit/e351b664961709378e673c01ccf98cc82642a801) · style(page): pad the bottom of two- and three-line rows
