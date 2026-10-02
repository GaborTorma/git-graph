# A futó szerver frissíti magát

Egy plugin-frissítés után a Claude appban futó git-graph percen belül magától
átáll az új verzióra, a lap pedig újratölt — app-újraindítás, új session és
újrapublikálás nélkül.

Eddig az app a régi szervert futtatta tovább, és a hook csak az app indulása
után cserélte a stabil másolatot, így minden kiadás után kétszer kellett
újraindítani az appot. A láblécben megjelenő verzió (v0.8.0) ezt láthatóvá
tette, de nem oldotta meg.

A szerver figyelőszála eddig is percenként olvasta a Claude Code
nyilvántartását a leszereléshez; most azt is észreveszi, ha ott újabb verzió
áll, mint ami fut. Ilyenkor a plugin mappájából maga átmásolja a scriptet és a
manifestet, és két kérés között `os.execv`-vel újraindul ugyanazokon a
stdio-csöveken. Hogy kérés ne vesszen el, a bemenet olvasása puffereletlen
lett, saját sorpufferrel: csak üres pufferrel indul újra, a csőben maradt
kérést az új folyamat olvassa. Kamu `HOME`-mal mérve a csere körüli 12
kérésből mind a 12-re jött válasz. Azt nem vállaltuk, hogy a szerver maga
figyelje a GitHub-kiadást és futtassa a `claude plugin update`-et — azt a
`/release` helyi frissítése teszi meg.

Nyitva maradt: a lap `location.reload()`-ja az Artifact keretében nincs
kimérve; ha nem megy, a lábléc akkor is az új verziót mutatja, csak kézzel
kell újratölteni. Ennek a kiadásnak a bevezetéséhez még egy app-újraindítás
kell, mert a most futó szerver még nem tudja frissíteni magát.

- [`[bbd00769]`](https://github.com/GaborTorma/git-graph/commit/bbd0076990a660d440085cd63b24afe87c1f7da5) · feat(mcp): update the running server in place after a plugin update
