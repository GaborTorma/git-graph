# Napfejlécek és commitonkénti görgetés

A lista napokra bontva jelenik meg, vékony, teljes szélességű elválasztóval
és ragadós napfejléccel: az aktuális nap felirata görgetéskor fent marad, a
következő kitolja. A mai nap fejléce csak görgetve jelenik meg. Az
Uncommitted Changes sor mindig látszik, a lista fölötti fix sávban.

A görgetés commitonként lép: egy kattanás egy commit, animáció nélkül, a sor
a napfejléc alá igazodik. A CSS scroll-snap ezt nem tartotta (egy
kattanással több sort ugrott), az animáció darabosnak tűnt, a simító
egérszoftverek (BetterMouse) lendülete pedig fordulásnál ide-oda
ugráltatta — ezt egy lecsengés-szűrő kezeli.

Ha lefelé haladva a kinyitott commit sora előbukkan, az egész commit (a
lenyitott résszel együtt) a nézetbe kerül.

- [`[abc9dfbf]`](https://github.com/GaborTorma/git-graph/commit/abc9dfbf718f6ffc7a128b598ed7e1130663077a) · feat(page): keep the day header pinned while scrolling, and make it thinner
- [`[e7350437]`](https://github.com/GaborTorma/git-graph/commit/e73504370c478231b3e123ef317fb945b1ce0418) · feat(page): draw the day header as a thin full-width divider
- [`[43983536]`](https://github.com/GaborTorma/git-graph/commit/43983536bd60ad52eee12e2d46a3703c4fccc5e7) · feat(page): show today's header only after scrolling, flush with the top
- [`[af3c79cf]`](https://github.com/GaborTorma/git-graph/commit/af3c79cf78dc20c0d235c73948b5532afb893f44) · fix(page): let the next day header push the previous one out
- [`[540ececf]`](https://github.com/GaborTorma/git-graph/commit/540ececf939bbdbcaf05339f7fff72615a5e2df8) · fix(page): hide the pinned day header as soon as the next one reaches it
- [`[66e7323e]`](https://github.com/GaborTorma/git-graph/commit/66e7323e7497cee966282d22b8f4dfb77c24b51c) · feat(page): put the day label in a chip, and keep only the chip when pinned
- [`[dd40c1ef]`](https://github.com/GaborTorma/git-graph/commit/dd40c1ef9f208f3150f1116729232b4fba7e8b89) · feat(page): scroll one commit per wheel step
- [`[e28bcc24]`](https://github.com/GaborTorma/git-graph/commit/e28bcc241c84a49c06835b43cacb2dc0b97c0d7b) · feat(page): drop the day chip, keep the plain label on the divider
- [`[1c4b78de]`](https://github.com/GaborTorma/git-graph/commit/1c4b78de5117c560f8af62114a931c5c754313ce) · feat(page): keep Uncommitted Changes pinned above the list
- [`[a52ce54b]`](https://github.com/GaborTorma/git-graph/commit/a52ce54b2b8257271282e69696228cfe4b885454) · feat(page): hide the divider line while the day label is pinned
- [`[cbe9317c]`](https://github.com/GaborTorma/git-graph/commit/cbe9317cea63cafb0a8a1c7eb31785cd8b3533b5) · feat(page): animate the per-commit scrolling smoothly
- [`[bfed6053]`](https://github.com/GaborTorma/git-graph/commit/bfed605370117bf2cd10afd71b5d37ced03bdc08) · fix(page): reverse the per-commit scrolling cleanly with smoothing mouse tools
- [`[3cf88277]`](https://github.com/GaborTorma/git-graph/commit/3cf8827737f07077258b4e1dbd2bf2040e55139a) · fix(page): stop the ping-pong on direction change with smoothing mouse tools
- [`[ea16f397]`](https://github.com/GaborTorma/git-graph/commit/ea16f397473713d813b269e9eb2db63991e4c40e) · feat(page): step one commit per wheel event without animation
- [`[570badb3]`](https://github.com/GaborTorma/git-graph/commit/570badb370d12df7bf75b760c67ce96781947032) · feat(page): bring the whole expanded commit into view when scrolling down to it
