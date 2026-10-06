# Egy vonalban állnak a távolságok az ágválasztóban

Az ágválasztó jobb szélén a távolságok most három, egymástól függetlenül méretezett oszlopban állnak. Legbelül minden sor `↑`-ja, mellette a két soros (ág + upstream) blokkok soronkénti `↓`-je, a szélen az egysoros blokkok `↓`-je és a két soros blokkok `↕` jele.

Eddig a kétirányú távolság (`↑1 ↓150`) egyetlen, egyirányú számra méretezett cellába került: kilógott belőle, a menüben vízszintes görgetősáv jelent meg, és a számvégek elcsúsztak. Az első javítás két cellára bontotta, de az `↑` így a `↓` oszlopának 3 jegyű szélességét kapta (`↑   1`). Ezért kapott az `↑` saját oszlopot. Mindhárom oszlop szélességét a lap a saját leghosszabb számából méri, az üres oszlop nulla széles.

A három oszlopot egy ideiglenes `origin/dev-test`-tel ellenőriztük, amely egy committal lemaradt a helyi ághoz képest; a próba után törölve.

- [`[f86699f3]`](https://github.com/GaborTorma/git-graph/commit/f86699f3476a9e2e15deedcf6be93554532415c9) · docs: drop the stale launchctl note from the install test recipe
- [`[acb8feed]`](https://github.com/GaborTorma/git-graph/commit/acb8feed9e44ed82b21f6133a11eee388fcf949f) · fix(page): align the ahead and behind columns in the branch menu
- [`[1c7e1ae8]`](https://github.com/GaborTorma/git-graph/commit/1c7e1ae8fb89bffa4fa5f173a857270766449568) · fix(page): give the ahead column its own width in the branch menu
