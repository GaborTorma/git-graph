# A lap a Claude app nyelvén

A lap új külsőt kapott, a Claude desktop app mintájára: meleg paletta,
Anthropic Sans / Mono betűk (ahol nincs, a rendszeré), Claude Light / Dark
kódszínek, és az app kontrolljai — lenyíló menü az ágválasztóhoz és a
témához natív `<select>` helyett, kapcsolók, inline vonalas ikonok. A lista
egysoros, táblázatfej nélküli; a kinyitott commit fejében avatar, szülő- és
commit-chip (a hash másolható), a fájlok előtt fájltípus-ikon.

Eddig a lap a VS Code Git Graph külsejét vitte át, ami az appban idegennek
hatott: kék macOS-menü, más betűk, más kontrollok.

A fejléc a szélességhez igazodik: 1–3 sorban, a kapcsolók felirata helyett
ikon, ha a felirat egy újabb sort nyitna; több sorban az ágválasztó és a
kereső kitölti a sorát. A témaválasztó a láblécbe került (appszintű
beállítás, nem a lista szűrője), az „Automatikus” mód a Claude app témáját
követi. A badge-ek és a diff-címke átlátszatlanok, hogy a kiemelt sor
háttere ne üssön át rajtuk; a túl hosszú szerzőnév keskeny panelen az
avatar tooltipjébe kerül. A GitLens külsejét szándékosan nem vettük át.

- [`[30acd622]`](https://github.com/GaborTorma/git-graph/commit/30acd6222a93a9d2b8214fd3b4753c01f7d0175d) · feat(page): redesign the page in the Claude app's look
- [`[5d28706a]`](https://github.com/GaborTorma/git-graph/commit/5d28706ac838927d7dfe7172bbae85e5adbb7e4a) · fix(page): keep the commit hash as plain text and the GitHub icon neutral
- [`[d78b963f]`](https://github.com/GaborTorma/git-graph/commit/d78b963fb5954330f94184b205e88bda07d54d45) · feat(page): replace the native branch select with a menu in the app's style
- [`[38a0bbca]`](https://github.com/GaborTorma/git-graph/commit/38a0bbca614a160c498ebda30f28fd79842e72d6) · feat(page): turn the theme switcher into a dropdown menu
- [`[79d61e5b]`](https://github.com/GaborTorma/git-graph/commit/79d61e5bf6abd72bf17aac494a9a6343b66ccdb3) · feat(page): swap the filter switch labels for icons when space is tight
- [`[c2b30ab4]`](https://github.com/GaborTorma/git-graph/commit/c2b30ab4597a3449fe726ac377cf14b48bddd267) · style(page): keep the expanded commit's subject at normal weight
- [`[6cbdd835]`](https://github.com/GaborTorma/git-graph/commit/6cbdd8359a13563809698390916ee78f8fcdcd9c) · fix(page): colour each graph line by the lane it runs in
- [`[d3bc00ba]`](https://github.com/GaborTorma/git-graph/commit/d3bc00bae6adbb053c2ea407debb70eab81acd73) · fix(page): keep the search field width steady on focus
- [`[0b87398c]`](https://github.com/GaborTorma/git-graph/commit/0b87398c64d1acd77543c9bc0f953d5579de4b4d) · feat(page): lay out the header by its row count
- [`[3cf855cf]`](https://github.com/GaborTorma/git-graph/commit/3cf855cf637d33e67c754c8f038d00f7c5597646) · fix(page): refit the header when the selected branch changes
- [`[4b56487b]`](https://github.com/GaborTorma/git-graph/commit/4b56487b45e430f4fa8ce2bacdba0c0b1758c303) · feat(page): move the theme picker into the footer
- [`[1c2fdee1]`](https://github.com/GaborTorma/git-graph/commit/1c2fdee1a29027ea729182fbbd83ef733dc3132d) · fix(page): follow the Claude app theme in automatic mode
- [`[da2c3dde]`](https://github.com/GaborTorma/git-graph/commit/da2c3dde068caa90e64db808877c51f396ce9035) · style(page): make the row diff tag cells opaque
- [`[46fa2b41]`](https://github.com/GaborTorma/git-graph/commit/46fa2b410d0d4aac76a271a0592867eb9012b6a7) · style(page): make the branch, remote and tag badges opaque
- [`[b0d1916b]`](https://github.com/GaborTorma/git-graph/commit/b0d1916b639a891f1e31cdeeb505853fe040ef63) · style(page): start wrapped commit header chips at the left
- [`[c1384bd9]`](https://github.com/GaborTorma/git-graph/commit/c1384bd952de4c974b11dc1aa13831aa8a278c04) · feat(page): hide a long author name in the commit header when it does not fit
