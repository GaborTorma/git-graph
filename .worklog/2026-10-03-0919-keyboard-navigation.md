# Billentyűzetes navigáció

A lista billentyűzetről is bejárható: fel-le a commitok között, jobbra a
commit kinyitása és a fájljaira lépés, a fájlokon jobbra-balra kinyitás és
csukás, a kinyitott fájlban a módosított blokkok között; balra visszafelé
ugyanez. Shift+nyíl csak görget, a kijelölés marad; a ⌘↑/↓ a szülőre és a
gyerekre ugrik, a H a HEAD-re.

A kijelölés fókusz alapú (látható keret), így a böngésző és a képernyőolvasó
is követi. Fájl csukásakor, ha az egész commit elfér, a nézet úgy igazodik,
hogy az egész commit látsszon.

- [`[d13d2264]`](https://github.com/GaborTorma/git-graph/commit/d13d2264b5ecaf45413f1781dc57fdda57ac4feb) · feat(page): navigate commits from the keyboard
- [`[1f7378b8]`](https://github.com/GaborTorma/git-graph/commit/1f7378b860a5409a0832b9517472dddaa3de8d4b) · feat(page): move a selection with the arrows, open and enter with right
- [`[5b9d9a54]`](https://github.com/GaborTorma/git-graph/commit/5b9d9a5414518c2ed9eed5e46d12dd47aea53e7a) · feat(page): step through the changed blocks of an open file with the arrows
- [`[e03a9945]`](https://github.com/GaborTorma/git-graph/commit/e03a99454d9275b6bf8872a568c3cd432c9a04a6) · feat(page): jump into the first changed block when a file is opened
- [`[479d25d4]`](https://github.com/GaborTorma/git-graph/commit/479d25d4d752af28f3d80d773c01a6db76c37d77) · feat(page): enter the first block of an already open file with right
- [`[7db3958e]`](https://github.com/GaborTorma/git-graph/commit/7db3958ebde086a64523f959dffb696ae20960f1) · feat(page): close the whole file with left from a changed block
- [`[7ee4dedd]`](https://github.com/GaborTorma/git-graph/commit/7ee4dedd4e9e527573ec2ae61c96a744b41d780b) · feat(page): step to the next block with right as well
- [`[2cc5a137]`](https://github.com/GaborTorma/git-graph/commit/2cc5a13722a721d2f9236187012be49db5a6ea4a) · feat(page): leave the file list upwards to the commit and downwards to the next commit
- [`[6ffc6677]`](https://github.com/GaborTorma/git-graph/commit/6ffc667773fb6275236d8faf6cf95de65817616d) · fix(page): stay on the last block instead of leaving to the next commit
- [`[b156fb0e]`](https://github.com/GaborTorma/git-graph/commit/b156fb0eeda20a4449ba1946dc732d9b97401a3e) · feat(page): scroll the view with Shift+arrows while keeping the selection
- [`[49e5e9ff]`](https://github.com/GaborTorma/git-graph/commit/49e5e9ff3027b91a044187cdf48cedfb87acee84) · feat(page): show the whole commit after closing a file when it fits
