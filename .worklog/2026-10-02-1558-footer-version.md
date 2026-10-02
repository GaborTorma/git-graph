# Verzió a láblécben

A lap láblécében ott a gépen futó git-graph verziója (`… git-graph v0.8.0 · …`).
Ha frissítés után az app még a régi szervert futtatja, a lábléc ezt kiírja a
teendővel együtt: `v0.8.0 fut, v0.8.1 telepítve — indítsd újra a Claude appot`.

Mióta a lap kódja élőben jön, egy frissítés az app újraindításával él — de
kívülről nem látszott, hogy az újraindítás megtörtént-e, és melyik kód fut.
Ma kétszer is kiderült, hogy az első újraindításkor még a régi szerver indul:
a hook csak utána másolja át az újat.

A futó szerver induláskor a mellette lévő manifestből rögzíti a verzióját, a
telepítettet a Claude Code nyilvántartásából olvassa, és mindkettőt a 2
másodpercenként hívott `fingerprint` adja. A hook ezért a stabil másolat mellé
a `plugin.json`-t is odamásolja — másolatként, nem symlinkként: a plugin
verzió-mappája eltűnhet, és egy linkkel a manifest elszakadna a ténylegesen
futó scripttől, épp az elcsúszott helyzetben hazudna. A betöltő nem változott,
ez a kiadás újrapublikálás nélkül él.

- [`[2469c196]`](https://github.com/GaborTorma/git-graph/commit/2469c196203cb3523d31b914228de308fd25968e) · feat(page): show the running and installed version in the footer
