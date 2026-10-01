# Publikálás a sessionből, launchd és Browser panel nélkül

Az Artifactot mostantól a futó Claude session publikálja, nem egy háttérben
indított headless `claude -p`. Ha az Artifact hiányzik vagy elavult, a
SessionStart hook megadja a sessionnek a lépéseket: `read`, `publish` a
`host:git-graph` capability-vel, végül `gg --published <URL>`, ami visszaírja az
URL-t és a lap hashét. A launchd agent (`gg --serve`) és vele a Browser panel-út
(`--serve`, `--launch-config`, `ggl`, a sablon `http` módja) megszűnt; a plugin
eltávolítását az app által indított `gg --mcp` figyeli. Az új verzió a hookjával
leszereli a régi agentet. Verzió: 0.3.0.

A headless út azért kellett, hogy session nélkül is lehessen Artifactot írni, de
ez volt a kód legtörékenyebb része (zárt kapuval induló Artifact tool,
stream-json interrupt, `--mcp-config`, a `claude` keresése a launchd PATH-ján).
Mérve kiderült, hogy erre nincs szükség: egy Code-tab session szerver nélkül is
deklarálhatja a `host:git-graph`-ot, az Artifact tool az első körben megvan
(Desktopban és terminál-CLI-ben is), és a sessionből publikált lap az appban él.
A lap kódja ráadásul csak plugin-frissítéssel változik, ami úgyis csak új
sessionnel lép életbe — és akkor először épp a hook fut. A Browser panel ugyanott
(az appban, a tulajdonosnak) volt elérhető, mint az Artifact, így nem adott
hozzá semmit.

A `--published` lépésben `gg` áll abszolút út helyett: a plugin `bin/`-je a Bash
PATH-ján van, és egy `Bash(gg:*)` engedély lefedi. Headless (`-p`, SDK)
sessionben a hook nem kér publikálást. A #5 issue (a háttérszerver neve és ikonja
a macOS-ben) ezzel tárgytalan lett, elvetve.

Nyitva maradt: a gépen a régi agent publikálását a `~/.git-graph/no-auto-publish`
állítja le, amíg az új verzió ki nem kerül; az új hook is tiszteli ezt a fájlt,
ezért a frissítés után törölni kell. Az app által indított `gg --mcp` a
leszereléskor a saját configbejegyzését törli a futó app alól — hogy az app ezt
felülírja-e, nincs kimérve.

- [`[333c5993]`](https://github.com/GaborTorma/git-graph/commit/333c599304f05687176a0d5b083d11db4e5fba6e) · feat!: publish artifacts from the session per worktree and drop the launchd server
