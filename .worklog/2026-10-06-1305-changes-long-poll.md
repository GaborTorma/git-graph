# Egy nyitott hívás: a lap a változásra vár

A lap mostantól nem kérdez 2 másodpercenként, és nincs külön hívása a session-váltásra sem. Egyetlen `changes`-hívást tart nyitva, a szerver pedig akkor válaszol, ha a repó állapota vagy az előtérben lévő session megváltozott, legkésőbb 50 s után üresen. Egy git-művelet (commit, checkout, ág) ~50 ms-on belül észlelődik, egy fájlszerkesztés legfeljebb ~2 s alatt. Üresjáratban nincs forgalom.

Két párhuzamos mechanizmus futott: a 2 s-os pollozás, és mellette egy nyitva tartott hívás a session-váltásokra. Egyesítve egy hurok maradt: hívás, válasz, változásnál adat, következő hívás. A `since` token (állapot-hash és naplópozíció) miatt a két hívás között jött változás sem vész el. A tool neve `fingerprint` helyett `changes` lett, mert már nem ujjlenyomatot ad, hanem változásig vár.

Átépítés előtt műszerezett dev-példánnyal mértük az appban: a nyitott hívás túléli a keret költözését; rejtett keretben a hívás azonnal elbukik, és a lap időzítői sem futnak, ezért a lap a megjelenéskor hív újra; a megszakítást a host nem adja át a szervernek, így az árva várakozót a határidő zárja. A szál explicit repóval dolgozik, mert a `REPO` globálist közben a fő szál átállíthatja.

Az állapot számolása is gyorsult: ~50 ms helyett ~15 ms egy kis repón, egy 10 ezer fájlos repón 139 helyett 94 ms. Ezt a valódi git bináris hozta (a macOS `/usr/bin/git` csak shim, hívásonként ~6 ms-mal lassabb), a párhuzamos hívások, és a `diff --numstat` elhagyása az ujjlenyomatból. A git `core.fsmonitor`-ja a nagy repón 27 ms-ra vinné, de csak az indexbe írva gyorsít, és az `index.lock` a Fejlesztő saját git-parancsait akasztaná meg, ezért elvetettük.

Az átmeneti `fingerprint` álnév a mérés után kikerült: a lap csak a `changes`-t hívja.

- [`[c5baf9ef]`](https://github.com/GaborTorma/git-graph/commit/c5baf9ef6866964589c61a218a6f386789ac5836) · perf(server): call the real git binary instead of the macOS shim, pass the repo to collect_worktrees
- [`[97eb1200]`](https://github.com/GaborTorma/git-graph/commit/97eb1200929e3bcc3d571288b5bef16740c3e311) · perf(server): one parallel repo state hash without numstat for the change fingerprint
- [`[b89934b4]`](https://github.com/GaborTorma/git-graph/commit/b89934b4ba25a6238df72ae2fb7115c13399d6e8) · feat(server): add the changes long-poll that answers on a repo or session-focus change
- [`[98e38b60]`](https://github.com/GaborTorma/git-graph/commit/98e38b60298ebac534d2f88cd2559b110cd56f61) · feat(page): follow the repo with one open changes call instead of polling and a focus watcher
- [`[b6024bce]`](https://github.com/GaborTorma/git-graph/commit/b6024bce450be3d5e558068d11917c0fc2d04575) · docs: describe the changes long-poll and its measurements
- [`[18f0cedd]`](https://github.com/GaborTorma/git-graph/commit/18f0cedd9b703fcb232897a0a76fc13cd47dff9a) · refactor: drop the fingerprint alias, the page calls changes only
