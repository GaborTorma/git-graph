## [0.18.0] - 2026-11-07

### 🚀 Features

- *(page)* Egyesített fejléc — ghost gombok, remote-ok az ágválasztóban, lenyíló keresés
- *(page)* Az ágválasztó gombja 500 px-ig nevekkel, a keresés teteje az app beágyazott keresője
- *(page)* A fejléc gombjai 28 px-esek, a szűrt keresés lenyomott háttérrel
- *(page)* Kijelölt ágnál lenyomott ágválasztó, Esc a keresett szöveget törli
- *(page)* Az ágválasztó x-e kijelölésnél a nyíl helyén
- *(page)* Az ágválasztó szűrőmezője ikon nélkül, 36 px, mint az app beágyazott keresője
- *(page)* Gyűrűs merge-pont és összecsukható beolvasztott commitok
- *(page)* Merge-sor — kétrészes hover, „+N” és nyíl a pötty mellett, lenyílás
- *(page)* A ref alatti beolvasztott lánc is összecsukódik, animált felcsukódás
- *(page)* Összecsukáskor a nyíl a helyén fordul, a szám balról jobbra nő
- *(page)* A szám a felcsukódással együtt nő, a nyíl kibontáskor is fordul
- *(page)* Kibontáskor a szám összemegy, a nyíl nem villan
- *(page)* A merge száma színátmenettel jelenik meg és tűnik el

### 🐛 Bug Fixes

- *(publish)* Publikálás a claude-artifacts eszközeivel, olvasható ~/.git-graph-ból
- *(skills)* Az Artifact-skillek a claude-artifacts eszközeivel
- *(page)* A betöltő <!DOCTYPE html>-lel kezdődik
- *(mod)* A lap megnyitása és a betöltő frissítése a claude-artifacts eszközeivel
- *(page)* A kártya nyitó és csukó animációi egy képkockában indulnak
- *(page)* Az egymás melletti WIP-diff nyugalomban nem rajzol újra minden képkockában
- *(page)* Az ágválasztó x-e függőlegesen középen, mint a keresésé
- *(page)* A lap indulásakor az IntersectionObserver kezdeti jelzése nem vágja el a hiba utáni szünetet
- *(page)* A szomszédos sorba futó szaggatott merge-él ívben fordul, nem derékszögben
- *(page)* A szaggatott merge-él olyan vastag, mint a fő vonal

### 📚 Documentation

- *(header)* A fejléc funkcióoldala — ágválasztó remote-kapcsolókkal, lenyíló keresés; a subtree-remote R-3 és a képek
- *(claude)* Kész lapváltozás után a --dev-install az AI dolga, a lap megnézése nem Teendő
- *(merge-collapse)* Funkcióoldal a merge-ek összecsukásáról, frissített képek
- *(merge-collapse)* A szaggatott él 2 px vastag, és a szomszédos sorba is ívben fordul

### ⚡ Performance

- *(graph)* Graph_data 220 helyett 100 ms alatt egy kis repón

### 🧪 Testing

- Unit-tesztek 9 s alatt, a lap tesztjei 60 s alatt
- *(page)* A lap tesztjei fix várakozás helyett feltételre várnak
- *(files)* A test_speed CPU-időt mér a falióra helyett

### ◀️ Revert

- Memory: a lap megnézése sem Teendő
- Memory: kész lapváltozás után a --dev-install-t az AI futtatja
## [0.17.0] - 2026-11-04

### 🚀 Features

- *(refs)* Független történet jele a közös ős nélküli ág chipjén
- *(graph)* A tükör-commitok halványak, és a forrásukhoz kötve látszanak
- *(filters)* Remote szerinti szűrő a „Remote ágak” kapcsoló mellett
- *(md-diff)* Ikonos listában az ikon a felsorolásjel
- *(page)* A lap az app design-systemjével (CDS) — színek, méretek, sávok, chipek, lenyitás
- *(page)* A markdown- és az SVG-diff nézetváltója kétgombos szegmens
- *(page)* Kétszintű tooltip, a natív title helyett mindenhol
- *(page)* Az avatar nélküli szerző monogramja szerzőnként színes
- *(page)* A keresés találata kiemelve a subjectben
- *(page)* A lap az app jelenlegi témájával — fizzy-lake színek, Anthropicons-ikonok, app-chip
- *(page)* Anthropic Sans és Mono a lapon, az app vastagságaival
- *(page)* A kontrollok az app komponensei szerint — gomb, mező, kapcsoló, menü, link, kbd
- *(page)* Az ágválasztó a lap magasságának ~80 %-áig nyúlhat le
- *(page)* Az ikonok a legújabb Anthropicons-fontból — felhős branch ikon, lenyíló nyíl
- *(page)* A lenyílók és a fogaskerék az app Select-je — mező-gomb, 12 px-es tételek
- *(page)* A lenyitás a hoverből nyílik — a teljes kártya hover-színű, a közepéről halványul
- *(page)* A kártya keret, árnyék és tartalom szerint nyílik és csukódik — a fájl is, mint a commit
- *(server)* A teljes nézet fája, a tartalomkeresés és a WIP sor író toolja
- *(page)* Commit/WIP teljes nézet fájlfával, CodeMirror-diff és a WIP sor szerkesztése
- *(page)* Szerkesztés tiszta worktree-ben a HEAD-commitból, a teljes nézet nyitott commit nélkül
- *(page)* A markdown forrása szerkeszthető a nyers nézetben
- *(page)* A teljes nézet alatt is látszó, vékonyabb lábléc a fájl útjával, diff-szűrő a „Minden fájl” helyett
- *(page)* A teljes nézet az eszközsor alatt, kijelölt fájl nélkül a gráffal
- *(page)* Fájllista sidebarban, teljes képernyő a fájl fejlécéből, beállítások a láblécben
- *(page)* A HEAD-commit diffje a lemez szövegével, a WIP eltérései kék / narancs rétegben
- *(page)* WIP-réteg egymás mellett is kettéosztott résekkel, és régebbi commitban is, ha a fájl azóta nem változott
- *(page)* Teljes képernyő a lap tetejétől, fájlkeresővel és commitlistával; a WIP sor kék / narancs
- *(page)* Teljes képernyő fejléce a HEAD-chippel és a fájllal, ágszűrt commitlista, mentés után a commiton marad
- *(page)* Teljes képernyőn a szerkesztő kitölti a magasságot, a fejlécben a fájl számai
- *(page)* Commit nélkül a sidebar fája színezés nélküli, a diff-szűrője a HEAD-commitot nyitja le
- *(page)* A WIP sor végén a +/− szám kék / narancs
- *(page)* A teljes képernyő X-e helyett a kilépés ikonja (Collapse)
- *(page)* A nem szerkeszthető kódnézeten nyíl a kurzor
- *(page)* Teljes képernyő commit nélkül a sidebarból; a kijelölt commit WIP nélkül levehető
- *(page)* Teljes képernyőn a fejléc újra teljes szélességű, a fa keresője kompakt a fa fölött

### 🐛 Bug Fixes

- *(stats)* A nagy fájllista nem feszíti szét a graph_data választ
- *(diff)* A követetlen symlink diffje a link célja
- *(graph)* A subtree squash-commitja szaggatott ívvel a split-commithoz
- *(gitio)* Eltűnt git bináris után újrakeresés
- *(mermaid)* Az ER-diagram vonala a jelölő után fordul, nem rajta
- *(page)* A tooltip paddingje az app buborékjáé, nem nagyobb
- *(graph)* A tükör forrása az alapág commitja, nem egy mellékág cherry-pickje
- *(page)* A változott Mermaid-elem felirata színes, nem vastagabb
- *(page)* A kézzel választott sötét téma sávszínei is a fizzy-lake értékei
- *(page)* A chip távolságában a nyíl és a száma közt 3 px, mint két ikon közt
- *(page)* Az ikonok az app méretskáláján — a menükben 20 px, a pipa bold, 13–14 px nincs
- *(page)* Az ágválasztó worktree-fejléce nem halvány — kattintható, csak a remote csoporté az
- *(page)* A fejléc HEAD-chipje akkora, mint a sor chipje — 20 px, 12 px-es betű
- *(page)* Az ágválasztó WIP-jele akkora, mint a gráfon (12 px), a pipák oszlopában
- *(page)* Az ágválasztóban a helyi ág párja csak az azonos nevű upstream
- Az ágválasztóban a helyi ág párja az azonos nevű remote ág, a `-u` nélküli push után is
- Csak az azonos nevű upstream számít — más nevűhöz nincs pár és távolság
- *(page)* A lenyitott commit fejlécének is van árnyéka, fent és oldalt — a panelé folytatódik
- *(page)* A pusholatlan alapág jelzése — halvány chipen halvány piros szakasz és piros keret, teli chipen teli piros
- *(page)* A lap újrapróbál, ha a nyitott hívás a gép alvása alatt lejár
- *(avatars)* Átmeneti letöltési hiba nem törli a meglévő képet
- *(page)* Az elvetés ikongomb mindkét nézetben, a szerkesztés kerete nem lóg a tartalomra
- *(page)* Teljes képernyő az eszközsor alatt, ikonja minden fájlon, szürke lenyomott gombok
- *(page)* A HEAD-commit fájlja a panelben az első mentés után is szerkeszthető
- *(page)* Fájlfejléc — GitHub-ikon a fájlnév után, teljes képernyő a jobb szélen, nézetváltó a diff sávjában
- *(page)* A review javításai — hosszú út vágása, üres sidebar tárgy nélkül, fánkénti keresés
- *(page)* Sok szétszórt változásnál a diff nem egy nagy blokk
- *(page)* A panelben szerkesztett fájl teljes képernyőn a módosításokkal, szerkeszthetően nyílik
- *(page)* A visszanyitott HEAD-commit fájl a friss lemezt mutatja
- *(page)* Egymás mellett a bal oldal a szülő, a WIP narancs sorai rajta; kék és narancs szókiemelés és sávjel
- *(page)* A kódnézet kijelölése sárgás, a színezett sorok fölött is látszik
- *(page)* Enter egy sor végén a WIP-rétegben csak az új sort jelöli, a következő sort nem duplázza
- *(page)* A markdown-diff 3-nál rövidebb változatlan futamot nem csuk össze
- *(page)* A lábléc gombjainak hovere erősebb (áttetsző kitöltés)
- *(page)* A kódnézet kijelölése erősebb (világosban 50%), a színes sorok fölött is látszik
- *(page)* A WIP narancs és kék sávjele világosabb, saját árnyalattal (a szám színe marad)
- *(page)* A fából nyitott fájl fejlécében is a saját ikon; szűk fejlécben a HEAD-chip eltűnik
- *(diff)* A HEAD-commit lemez oldala és mentése a saját (előtérben lévő) worktree-é, nem az első egyező
- *(files)* A write_file atomi cserével ír, elbukott írásnál a fájl ép marad
- *(page)* CRLF-es fájlnál a sorvég nem WIP-eltérés (a kódnézet szövege \n-es)
- *(page)* Az elbukott tartalomkeresés hibát mutat a fában, nem a régi találatokat
- *(page)* A kódnézet egy hívással tölt, a host visszafogását (rate_limited) kivárja
- *(page)* Commitváltáskor a megnyitott fájl marad, ha a commit nem is változtatta
- *(page)* Commitváltáskor a nyitott kódnézet helyben frissül, nem töltődik újra
- *(diff)* A fejadattal jövő lemez oldal is `\n`-es (a sorvég-normalizálás kimaradt róla)
- *(page)* A narancs WIP-blokkra eső kijelölés nem látszik, a blokk alatti sor a saját magasságában jelölt
- *(page)* Commit nélkül a commit változása nem színeződik; a szerkesztéskor megjelenő WIP sor kijelölődik
- *(page)* Gépelés közben sincs piros / zöld a WIP-soron; a WIP sorra váltva a fájl nem csukódik össze
- *(page)* A teljes képernyő fejlécében a repó neve és a chip a lap fejlécével egy helyen; mindkét fejléc 44 px
- *(page)* Az üres régi sor nem kerül a narancs WIP-blokkba (mint egymás mellett)
- *(page)* A WIP soron (merge törölt blokk) is kimarad az üres törölt sor, és a kijelölés nem csúszik rá
- *(page)* Ha a kijelölt WIP sor eltűnik, a teljes nézet helyben a worktree állapotára vált
- *(page)* Az üres törölt sor újra látszik; a rá eső kijelölést a blokk takarja
- *(page)* A lemez saját (azonos) szövege nem ütközés; a helyben váltás megtartja a mentés állapotát
- *(avatars)* A szerző képe a nagy commitnál is megjön
- *(page)* A commit bodyja nem törik 72 karakternél, csak a saját sortörésénél

### 🚜 Refactor

- *(diff)* A sorvég-normalizálás a szerveren, a lap `\n`-es szöveget kap
- *(page)* A kóddiff WIP-rétege külön modulban (wip.js)

### 📚 Documentation

- *(subtree-remote)* Magyar Gherkin-követelmények, képek és a képernyőkép-script
- *(file-diff)* A lenyitott fájl kártya, mint a commit — README: CDS-megjelenés, azonos nevű upstream, piros jelzés; új képek
- *(full-view)* A fájlfa és a teljes nézet, a kóddiff és a szerkesztés oldala; a fájl-diff frissítése

### 🧪 Testing

- *(page)* A commit nélküli színezés tesztje az automatikus mentés előtt ellenőriz
- *(page)* A Playwright alapértelmezett időkorlátja 5 s
- *(page)* A fájlsor hover-rétegét figyelő rögzíti, nem pollozás

### ◀️ Revert

- Fix: az ágválasztóban a helyi ág párja az azonos nevű remote ág, a `-u` nélküli push után is
## [0.16.0] - 2026-10-21

### 🚀 Features

- *(diff)* Show image files and markdown images as images in the file diff
- *(graph)* Méret a bináris fájlok sorában a `bin` címke helyett
- *(page)* Képek összehasonlítása és nagyítása a fájl-diffben
- *(diff)* A kép oldalanként külön válaszban, 2,95 MB-ig
- *(page)* A képnézegető finomításai a kipróbálás után

### 🐛 Bug Fixes

- *(diff)* Do not mark the indentation of a prose line as a changed word
- *(diff)* Keep a list item that changed level on its own level in the markdown view
- *(graph)* Stash list versenyhelyzete hiba nélkül
- *(page)* Nagyításkor a panel a megnőtt képhez görget

### 📚 Documentation

- *(diff)* Move the file diff to its own page with image requirements R-1–R-4
- Move the measurement log and the gotcha reasons from docs/ into memory
- Drop the CLAUDE.md lines that the rules and the memory index already state

### 🧪 Testing

- *(page)* A lap tesztjei párhuzamosan, osztályonként egy workerben

### ⚙️ Miscellaneous Tasks

- Keep the hand-drawn icon source in design/icons/ instead of docs/
## [0.15.0] - 2026-10-16

### 🚀 Features

- *(page)* Show issue, pull request and release references as chips
- *(skills)* Merge the forget commands into artifact-forget with a scope choice
- *(install)* Treat a plugin loaded from source as a dev instance
- *(page)* Add a settings menu for automatic opening and publishing
- *(page)* Animate opening, closing and resizing of commits and diffs
- *(page)* Render markdown file diffs with highlighted changes
- *(graph)* Show each stash as one row on its base
- *(diff)* Show rendered markdown diffs side by side on wide panels
- *(diff)* Render mermaid diagrams in the markdown diff
- *(diff)* Mark only the changed parts of mermaid diagrams
- *(diff)* Draw mermaid diagrams in the page palette with ELK layout
- *(diff)* Turn flowcharts to the direction that fits the panel
- *(worktrees)* Show staged changes as a separate row under the uncommitted one

### 🐛 Bug Fixes

- *(skills)* Bring up the artifact pane when reopening the graph
- *(mcp)* Announce the tool list change after a self-update restart
- *(loader)* Retry loading the page code once the hidden frame is shown
- *(page)* Keep untracked files in place with their line count
- *(page)* Fit the opened commit on screen with its neighbours
- *(watch)* Carry focus in the since token and recheck it while waiting
- *(lanes)* Place worktree lanes after the lanes live above the fork
- *(diff)* Stop marking rewrapped prose lines as changed
- *(diff)* Show one side when a change only inserts or only deletes words
- *(diff)* Keep prose words in their own line and paragraph
- *(diff)* Pair prose paragraphs so renumbering does not shift the text
- *(diff)* Align table and code rows across the markdown side-by-side
- *(diff)* Keep paired markdown rows the same height side by side
- *(diff)* Stop marking node labels when only an edge target changes
- *(diff)* Mark a single one-sided row even when its neighbours were replaced
- *(wip)* Show an unstaged rename as one renamed file
- *(diff)* Ignore the indentation of a wrapped list line
- *(diff)* Treat a markdown block as one unit when colouring changes
- *(diff)* Put unpaired old and new rows next to each other side by side
- *(diff)* Keep a changed last table row in its table
- *(diff)* Start the side-by-side view below the view toggle
- *(diff)* Keep a leading gap marker beside the view toggle
- *(diff)* Float the markdown view toggle over the diff
- *(diff)* Keep a wholly new line fully coloured in a one-sided change
- *(diff)* Line up a one-sided change from the top side by side
- *(diff)* Show a pure rewrap as unchanged lines
- *(diff)* Show a moved-only line of a one-sided change as unchanged
- *(diff)* Hide rewrap-only blocks in the markdown view
- *(diff)* Highlight a changed mermaid label only in its own node
- *(diff)* Pair list items when new items are inserted between them
- *(diff)* Keep a new list item in place in the markdown view

### 🚜 Refactor

- *(page)* Share the collapse of unchanged markdown blocks, rows and lines
- *(page)* Build markdown links with ghLink
- *(page)* Reuse the raw diff add/del classes in the markdown view
- *(page)* Skip redrawing a refreshed diff that did not change
- *(page)* Move the mdText comment above mdText
- *(page)* Split page.js into ES modules linked by page_code
- *(graph)* Split graph.py into stats, worktrees, branches and lanes modules
- *(graph)* Resolve the stash owner once, on the server
- *(graph)* Parse each commit time once when placing stashes
- *(diff)* Line up one-sided runs through the general pairing path
- *(diff)* Compute each hunk's one-sided lines once
- *(diff)* Build the markdown partner lookup once
- *(diff)* Look up a line's markdown block in a map
- *(wip)* Keep the line counts of a paired rename
- *(diff)* Decide each line's look once, from an explicit state
- *(diff)* Order markdown change lines once instead of moving blocks
- *(diff)* Skip the row-height sync while the side-by-side is hidden
- *(diff)* Share the row view of markdown code blocks and tables
- *(diff)* Tokenize each prose line once
- *(wip)* Reuse the rename candidate's matcher for the line counts
- *(test)* Share the page tests' fixture commits and readers
- *(test)* Read prose diff lines and their marks through helpers
- *(diff)* Build each markdown block's views once
- *(diff)* Let the server decide each line's look and the markdown order

### 📚 Documentation

- *(claude-md)* Drop the version bump rule from the feature commit
- Remove the historical desktop-live, mcp-plan notes and the probe tool
- *(claude)* Trim CLAUDE.md to one-line rules, move the rationale to docs/architecture.md
- *(claude-md)* Keep auto-commit on in this plugin repo
- *(findings)* Record that mermaid runs under the artifact CSP

### 🧪 Testing

- *(page)* Add headless playwright harness for page behaviour

### ⚙️ Miscellaneous Tasks

- *(check)* Move the check commands to .claude/check.toml
- *(settings)* Turn off the server-side auto mode classifier for the project
- Drop the 0.12 entry shim and the pre-0.13 autoPublish fallback
- *(page)* Type-check page/js with tsc --checkJs
## [0.14.0] - 2026-10-10

### 🚀 Features

- *(skills)* Split artifact commands into publish, open, forget and forget-all

### 📚 Documentation

- *(findings)* Record that permission rules do not let a mod publish
- *(worklog)* Artifact commands
## [0.13.0] - 2026-10-09

### 🚀 Features

- *(page)* Color new and deleted files and their new or emptied folders
- *(graph)* List files inside untracked folders in the uncommitted row
- *(page)* Show renamed files with a larger » instead of =>
- *(page)* Show the repo name in title case in the header
- *(plugin)* Open the artifact from a plugin mod instead of the model

### 🐛 Bug Fixes

- *(page)* Fill the upstream cloud on branch chips tracking the default branch
- *(page)* Show the unpushed count on the default branch as a split red chip

### 📚 Documentation

- *(findings)* Record that artifacts see the OS locale, not the app's
- *(findings)* Record how the app gates write tools on the host bridge
- *(claude-md)* Report the dev-install version after each change
- *(worklog)* Mod opens artifact

### ⚡ Performance

- *(install)* Pick up a dev install within 15 seconds

### ⚙️ Miscellaneous Tasks

- Move CLAUDE.md under .claude to pass strict plugin validation
## [0.12.2] - 2026-10-06

### 🐛 Bug Fixes

- *(page)* Align the ahead and behind columns in the branch menu
- *(page)* Give the ahead column its own width in the branch menu

### 📚 Documentation

- Drop the stale launchctl note from the install test recipe
- *(worklog)* Branch menu distance columns
- *(worklog)* Python package split

### 🚜 Refactor

- Split bin/git-graph into the git_graph package with per-module tests
- *(install)* Place the manifest last and share the registry and manifest readers

### 🎨 Styling

- *(page)* Dim the folder part of file paths in the commit panel
## [0.12.1] - 2026-10-06

### 🐛 Bug Fixes

- *(branches)* Keep a branch with the worktree it was switched away from

### 📚 Documentation

- Add the CorelDRAW source of the cloud-and-branch icon

### 💼 Other

- *(lint)* Keep the worktrees under .claude out of the Biome scanner
## [0.12.0] - 2026-10-06

### 🚀 Features

- [**breaking**] Share one artifact per repo across worktrees
- *(page)* Hide the commit count while the footer shows an error
- *(page)* Tell worktree pills apart from branches and show how far ahead they are
- *(page)* Show only real worktrees as pills and branch them off the main line
- *(page)* Put worktree lanes after the main checkout's branches with a faint separator
- *(page)* Dim what is not in the own worktree instead of a manual pick
- *(page)* Fold origin/HEAD into its target and drop the origin/ prefix on remote chips
- *(page)* Name the remotes on synced branch badges when a repo has several
- *(page)* Color branch, HEAD and tag badges by their commit's lane
- Bind a new panel to its session without a prompt
- *(page)* Treat unowned branches as the main checkout's when dimming
- Take the own worktree from the focused session in the Claude app
- *(page)* Ask for the focus right away when the frame moves to another session
- *(page)* Poll densely after a session switch, worktree icon on the pills
- *(page)* Guess the focus from the panel size, confirmed by the app's session file
- *(page)* Show sync state on worktree pills with a filled icon and ↓N
- *(focus)* Take the focused session from the app log, drop the size guess
- *(page)* Show what triggered the last session switch in the live tooltip
- *(focus)* Hold a fingerprint call open until the next session switch
- *(page)* Branch a commitless worktree HEAD off with a stub, group worktree badges
- *(server)* Time uncommitted rows by file mtime, start stub lanes afresh per commit
- *(page)* Other worktrees' WIP rows in the list with chips, fan-out stubs, new worktree icon
- *(page)* Show uncommitted rows as "Nem commitolt változások" with time, author and diff, placed by mtime
- *(server)* Order linked worktrees by creation time
- *(page)* Show how many of the day's rows are above and below its header
- *(page)* Show the day on the pinned uncommitted row when it is not from today
- *(page)* Show each branch's distance from the base branch and its upstream on its chip
- *(page)* Show a remote branch's distance from its local branch last on its chip
- *(page)* Flag unpushed commits on the base branch's local copy
- *(page)* Branch distances on the base branch's remote, uncommitted badges and tooltips
- Group the branch picker by worktree, with local and upstream as one option
- *(page)* Toggle single refs from the branch picker, branch and cloud in separate columns
- *(page)* Select a worktree's branches from its header, mirror the selection on the picker button
- *(page)* Mark a branch synced with its upstream by one cloud-and-branch icon, one icon column
- *(page)* Add a name filter to the branch picker
- *(page)* Match worktree and remote names in the branch filter
- *(page)* Label a detached worktree HEAD and show its distance from the base branch
- *(page)* Jump to the own HEAD commit when the header chip is clicked
- *(page)* Jump to the selection's tip after picking in the branch menu
- *(page)* Dim the header chip when the branch filter hides HEAD, reset the filter on click
- *(server)* Add the changes long-poll that answers on a repo or session-focus change
- *(page)* Follow the repo with one open changes call instead of polling and a focus watcher

### 🐛 Bug Fixes

- *(page)* Move worktree lanes back only above their fork point
- Keep the panel binding across reloads and frame rebuilds
- *(page)* Retry a transient bridge error quietly after a session switch
- *(page)* Wait silently while the frame is hidden, poll on reappearing
- *(page)* Tie a detached worktree to its branch via the app registry, not the name
- *(page)* Open an uncommitted row's panel under its own row in the pinned band
- *(server)* Include the uncommitted files' mtime in the change fingerprint
- *(page)* Show only the uncommitted row of the worktree that has the filtered branch checked out
- *(page)* Hide only remote-only history and remote badges when remote branches are off
- *(page)* Keep dropdown menus inside the window so long lists scroll
- *(page)* Scroll only the branch list, keep the filter and "Minden ág" fixed
- *(page)* Keep live updates running when the focus changes without an arrival signal
- *(page)* Keep the remote switch redrawing when remotes are turned off
- *(page)* Make the header chip a real button so the a11y lint passes
- *(page)* Keep a detached worktree's WIP row under the branch filter and jump to it

### 📚 Documentation

- *(findings)* Measure a shared worktree artifact
- *(findings)* One frame per artifact across sessions, focus from the app's session files
- *(findings)* Measure the app log as the instant session focus signal
- *(findings)* Measure what the frame gets during a session switch
- *(findings)* Measure frame moves within one artifact, held calls and the host rate limit
- *(claude)* Note the worktree stubs
- *(findings)* Find a detached worktree's branch in the Claude app registry
- Describe branch distance segments and uncommitted row placement
- *(worklog)* Shared artifact, session focus, worktrees, uncommitted rows, branch chips, branch picker, header chip
- Describe the changes long-poll and its measurements
- *(worklog)* Changes long-poll, drop migration code

### ⚡ Performance

- *(server)* Call the real git binary instead of the macOS shim, pass the repo to collect_worktrees
- *(server)* One parallel repo state hash without numstat for the change fingerprint

### 🚜 Refactor

- *(server)* Drop the unused per-worktree ahead/behind, share worktree helpers
- *(page)* Index commits once per data load, one remote-switch reader, opt-in checkmarks
- *(page)* Group the branch list by section, move the filter keys out of makeMenu
- Share chip helpers between the header and commit badges, one ahead-behind helper
- Drop the fingerprint alias, the page calls changes only
- Drop the migration code for pre-0.12 per-worktree pages and the 0.10.x server

### 🎨 Styling

- *(page)* Fade foreign graph dots and lines with a solid mixed color
- *(page)* Mark synced branches with a cloud and show remote-only refs as gray chips
- *(page)* Fill the cloud of the remote's default branch
- *(page)* Show branch and tag tooltips in the page's own bubble
- *(page)* Round the tag badge into a full chip
- *(page)* Always put the tag badge last
- *(page)* Put the sync cloud right after the branch icon
- *(page)* Show the worktree icon on the badge of a branch checked out in a worktree
- *(page)* Thicken the worktree icon to match the line icons
- *(page)* Show only the worktree icon on a linked worktree's detached HEAD
- *(page)* Label a linked worktree's detached HEAD with the worktree name
- *(page)* Fold a linked worktree's detached HEAD into the branch at its tip
- *(page)* Fold a detached worktree HEAD only into the branch named after it
- *(page)* Give the branch named after a stubbed worktree the stub's color
- *(page)* Keep the uncommitted dashed line unfaded on foreign branches
- *(page)* Keep the uncommitted dashed lines visible while scrolled
- *(page)* Hide only the own worktree's dashed line while scrolled
- *(page)* Mark the expanded row a shade darker than hover instead of the accent tint
- *(page)* Use the hover background for the expanded row
- *(page)* Outline the expanded row like its panel
- *(page)* Fold the expanded row into its panel card with an unfold animation, no WIP panel header
- *(page)* Color the header branch chip by its lane, worktree icon, dirty ring and ahead count
- *(page)* Fan-shaped lane changes drawn above the straight lanes
- *(page)* Let lane changes run 1 px along the commit's lane before turning
- *(page)* Mark the main checkout's uncommitted row with an empty folder and "main"
- *(page)* Label a detached worktree's uncommitted row with the worktree, not HEAD
- *(page)* Give uncommitted rows a plain worktree badge, not the HEAD outline
- *(page)* Show the branch on uncommitted rows' worktree badges
- *(page)* Let the uncommitted row's worktree badge grow wider than branch chips
- *(page)* Shorten the base branch anomaly tooltip
- *(page)* Drop the uncommitted ring from the header chip
- *(page)* Wrap the uncommitted row's badge like ref badges, folder icon on the main checkout's header chip
- *(page)* Move to three lines when a badge name would be truncated next to the meta block
- *(page)* Bump badge icons to 12 px and header chip icons to 13 px
- *(page)* Drop the cloud and remote distances from chips when remote branches are off
- *(page)* Show the diff tag on empty commits too
- *(page)* Tint the branch picker's icons like their branches, fill only the default branch's cloud
- *(page)* Tighten the branch picker's block lines to 20 px
- *(page)* Color remote badges like their local branch, or their commit's lane
- *(page)* Tint the branch picker's HEAD pill with its branch's color
- *(page)* Show the local–upstream distance once, between the block's two lines
- *(page)* Build the local–upstream mark from stacked up and down arrows
- *(page)* Put the local–upstream mark before the distance column, arrows joined
- *(page)* Put the local–upstream mark last at the row's edge, distances in one column before it
- *(page)* Keep single-line distances at the branch picker's right edge
- *(page)* Lay out the branch picker's distances in two fixed columns of arrow and number cells
- *(page)* Size the distance cells to the longest number, put the detached mark under the WIP ring
- *(page)* Draw the all-branches icon with two lanes
- *(page)* Draw the all-branches icon's nodes as hollow circles, like the branch icon
- *(page)* Enlarge the all-branches icon's hollow nodes so they read as rings at 14 px
- *(page)* Size each distance column to its own longest number, one to four digits
- *(page)* Use the developer's drawing for the cloud-and-branch icon
- *(page)* Draw the cloud-and-branch icon with the set's 1.5 stroke
- *(page)* Drop the construction line from the filled cloud-and-branch icon
- *(page)* Update the outline cloud-and-branch icon to the developer's new drawing
- *(page)* Give synced branch badges the single cloud-and-branch icon
- *(page)* Put the diff tag before the avatar in the commit row
- *(page)* Unify worktree marks on HEAD and WIP badges
- *(page)* Mark a detached HEAD with the chain icon on the bare HEAD badge and the header chip
- *(page)* Give the header chip the same branch icon as the HEAD commit badge
- *(page)* Build the header chip like the HEAD commit badge, remote segments included
- *(page)* Fill the header chip like the own HEAD badge
- *(page)* Name a detached worktree on the header chip, drop "main" from the main checkout's detached badge

### 🧪 Testing

- Cover branch distances from the base branch, upstream and local pair
## [0.11.0] - 2026-10-04

### 🚀 Features

- *(page)* Redesign the page in the Claude app's look
- *(page)* Add commit search and the new palette to the loader
- *(page)* Replace the native branch select with a menu in the app's style
- *(page)* Keep the day header pinned while scrolling, and make it thinner
- *(page)* Draw the day header as a thin full-width divider
- *(page)* Show today's header only after scrolling, flush with the top
- *(page)* Swap the filter switch labels for icons when space is tight
- *(page)* Turn the theme switcher into a dropdown menu
- *(page)* Put the day label in a chip, and keep only the chip when pinned
- *(page)* Scroll one commit per wheel step
- *(page)* Drop the day chip, keep the plain label on the divider
- *(page)* Keep Uncommitted Changes pinned above the list
- *(page)* Hide the divider line while the day label is pinned
- *(page)* Animate the per-commit scrolling smoothly
- *(page)* Step one commit per wheel event without animation
- *(page)* Bring the expanded commit to the top when the search is cleared
- *(page)* Navigate commits from the keyboard
- *(page)* Move a selection with the arrows, open and enter with right
- *(page)* Step through the changed blocks of an open file with the arrows
- *(page)* Jump into the first changed block when a file is opened
- *(page)* Enter the first block of an already open file with right
- *(page)* Close the whole file with left from a changed block
- *(page)* Step to the next block with right as well
- *(page)* Leave the file list upwards to the commit and downwards to the next commit
- *(page)* Scroll the view with Shift+arrows while keeping the selection
- *(page)* Show the whole commit after closing a file when it fits
- *(page)* Show file type icons from catppuccin in the file list
- *(page)* Show the commit's total changes before the author
- *(page)* Switch a squeezed commit row to two lines
- *(page)* Lay out the header by its row count
- *(page)* Add GitHub and issue links to the footer
- *(page)* Add a pull request link and trim the footer labels
- *(page)* Spin the refresh icon while new data loads
- *(page)* Pulse the live dot instead of a spinning icon
- *(page)* Pulse the live dot continuously, red when updates fail
- *(page)* Move the theme picker into the footer
- *(page)* Show the author as an avatar or initials on the commit row
- *(page)* Add the file count to the row diff tag and drop the row hash
- *(page)* Bring the hash back to the commit row
- *(page)* Show the row diff details in a hover tooltip
- *(page)* Lay out commit rows by fixed text column widths
- *(page)* Drop the hash from the commit row
- *(page)* Move the row meta to a third line instead of dropping parts
- *(page)* Hide a long author name in the commit header when it does not fit
- *(page)* Bring the whole expanded commit into view when scrolling down to it

### 🐛 Bug Fixes

- *(data)* Show the files of merge commits against the first parent
- *(page)* Keep the commit hash as plain text and the GitHub icon neutral
- *(page)* Let the next day header push the previous one out
- *(page)* Hide the pinned day header as soon as the next one reaches it
- *(page)* Reverse the per-commit scrolling cleanly with smoothing mouse tools
- *(page)* Stop the ping-pong on direction change with smoothing mouse tools
- *(hook)* Leave a fresh --dev-install in place for twelve hours
- *(page)* Colour each graph line by the lane it runs in
- *(page)* Keep the search field width steady on focus
- *(page)* Let Escape clear the search before closing the commit
- *(page)* Stay on the last block instead of leaving to the next commit
- *(page)* Move the meta block below the subject in a squeezed row
- *(page)* Keep a squeezed row with badges at two lines
- *(page)* Tighten the row meta and fit it beside the badges
- *(page)* Drop the author when it would overlap the diff in a two-line row
- *(page)* Refit the header when the selected branch changes
- *(page)* Unclip and soften the live pulse, link the version to the plugin
- *(page)* Align the live dot with the first lane and shorten the version
- *(page)* Follow the Claude app theme in automatic mode
- *(page)* Put the badges on the second line of a two-line row
- *(page)* Drop the diff from a one-line row when it clips the subject
- *(page)* Keep the row diff after the hash and show it on all rows or none
- *(page)* Keep the diff on multi-line rows and switch to two lines sooner
- *(page)* Hide the row meta by priority time, avatar, diff, hash
- *(page)* Keep the row tooltips from opening a horizontal scroll
- *(page)* Show the row tooltips inside the row, left of the element
- *(page)* Lift the hovered row so its tooltip stays above the neighbours
- *(page)* Render the row tooltips as one fixed bubble above everything
- *(page)* Let a badge row drop its hash before going two-line

### 📚 Documentation

- *(worklog)* Split page files
- *(worklog)* Claude app look, search, keyboard navigation, scrolling, file icons, commit row, live footer, merge files

### 🚜 Refactor

- Move the page code from the script into page/ files
- *(page)* Trim repeated work and leftovers from the redesign

### 🎨 Styling

- *(page)* Keep the expanded commit's subject at normal weight
- *(page)* Right-align the badges in a multi-line row
- *(page)* Show the row diff as colored tags after the hash
- *(page)* Shrink the row diff tags to a fixed width
- *(page)* Put the avatar between time and hash, right-align the diff
- *(page)* Narrow the row diff to three digits per side
- *(page)* Split the row diff tag by digit count, drop zero sides
- *(page)* Right-align both halves of the row diff tag
- *(page)* Split the row diff tag in fixed halves, show zeros again
- *(page)* Soften the file change bars
- *(page)* Keep the 99+ plus inside the tag and at regular weight
- *(page)* Move the hash to the end of the commit row
- *(page)* Give the row diff tag the badge height and outline
- *(page)* Tone down the row tooltips
- *(page)* Separate the file count with a comma in the diff tooltip
- *(page)* Never show the hash on a two-line row
- *(page)* Give two- and three-line rows two more pixels
- *(page)* Give two- and three-line rows one more pixel
- *(page)* Pad the bottom of two- and three-line rows
- *(page)* Make the row diff tag cells opaque
- *(page)* Make the branch, remote and tag badges opaque
- *(page)* Start wrapped commit header chips at the left
## [0.10.0] - 2026-10-02

### 🚀 Features

- *(page)* Highlight the latest commit burst for five minutes

### 🐛 Bug Fixes

- *(hook)* Open the artifact after publishing it

### 📚 Documentation

- *(worklog)* Open after publish, fresh commits
## [0.9.0] - 2026-10-02

### 🚀 Features

- *(mcp)* Update the running server in place after a plugin update

### 📚 Documentation

- *(worklog)* Mcp self update
## [0.8.0] - 2026-10-02

### 🚀 Features

- *(page)* Show the running and installed version in the footer

### 📚 Documentation

- *(worklog)* Footer version
## [0.7.0] - 2026-10-02

### 🚀 Features

- *(page)* Load the page code live from the local mcp server

### 📚 Documentation

- *(findings)* Measure dynamic code execution under the artifact CSP
- *(worklog)* Live page code
## [0.6.2] - 2026-10-02

### 🐛 Bug Fixes

- *(diff)* Align similar lines in the side-by-side view

### 📚 Documentation

- *(worklog)* Side-by-side diff line alignment
## [0.6.1] - 2026-10-02

### 🐛 Bug Fixes

- *(hook)* Write the session log atomically and survive write errors

### 📚 Documentation

- *(worklog)* Session log hardening

## [0.6.0] - 2026-10-02

### 🚀 Features

- *(hook)* Open the artifact only once per session

### 📚 Documentation

- *(worklog)* Artifact open once per session

## [0.5.0] - 2026-10-02

### 📚 Documentation

- *(worklog)* Artifact skill rename

### 🚜 Refactor

- [**breaking**] Rename the git-graph skill to artifact

## [0.4.2] - 2026-10-02

### 🐛 Bug Fixes

- *(ui)* Skip the side-by-side diff when a file only adds or only removes lines

### 📚 Documentation

- *(worklog)* One-sided diff view

## [0.4.1] - 2026-10-01

### 📚 Documentation

- *(worklog)* Drop gg alias

### 🚜 Refactor

- [**breaking**] Drop the gg alias, call git-graph everywhere

## [0.4.0] - 2026-10-01

### 🚀 Features

- [**breaking**] Drop the static snapshot, terminal commands and legacy cleanup
- Name worktree artifacts after their folder

### 📚 Documentation

- *(claude)* Record release versioning and deploy mode
- *(worklog)* Drop static snapshot, worktree artifact names, release deploy mode

## [0.3.0] - 2026-10-01

### 🚀 Features

- Git-graph — Git Graph-szerű commit-gráf bármelyik repóból
- *(serve)* Élő gráf a Claude Desktop Browser paneljében
- *(launch)* Gg --launch-config — a panel névvel indítható
- *(launch)* Lokális launch.json + git-hívások index.lock nélkül
- *(graph)* Uncommitted Changes sor a gráf tetején
- *(graph)* Az uncommitted soron látszik az érintett fájlok száma
- *(launch)* A git-graph bejegyzés mindig a lista elejére kerüljön
- *(hook)* A hook a subdomainos URL-t adja át, ne a query-set
- *(cli)* Ggl alias a launch config írására
- *(ui)* Link issue and PR references in commit messages
- *(ui)* Link pushed commit hashes and file diffs to GitHub
- *(serve)* Open GitHub links in the system browser
- [**breaking**] Auto-publish artifacts from gg --serve and move output out of the repo
- [**breaking**] Serve artifacts live from the local gg --mcp instead of re-publishing data
- *(ui)* Expand file rows into inline diffs
- *(ui)* Show file diffs side by side when the panel is wide enough
- *(hook)* Open the repo's live artifact at session start
- [**breaking**] Ship as a self-installing claude code plugin
- Add /git-graph:remove to delete artifacts before uninstall
- [**breaking**] Publish artifacts from the session per worktree and drop the launchd server

### 🐛 Bug Fixes

- *(serve)* Panelenkénti repó és script-záró escape
- *(ui)* A sor kiemelése ne takarja el a gráf pöttyét
- *(ui)* A pöttyök kövessék a kinyitott panelt; keskeny, ikonos Graph oszlop
- *(publish)* Declare the host:git-graph mcp capability on artifacts
- *(ui)* Restore real anchor links so they open from the artifact
- *(ui)* Name pages and artifacts "Git Graph (<repo>)"
- *(ui)* Show one-sided file diffs only in the unified view

### 📚 Documentation

- Add check commands to CLAUDE.md
- Record that the artifact host: MCP bridge now works
- *(worklog)* Inline file diff
- *(worklog)* Self-installing plugin, ignore parked list
- *(worklog)* One-sided diff view
- *(worklog)* Drop the parked-list entry
- *(findings)* Measure sending page requests to the session
- *(worklog)* Drop legacy migrations, remove skill
- *(worklog)* Session publishing, per-worktree artifacts

### 🚜 Refactor

- [**breaking**] Rename gitgraph script to git-graph
- *(ui)* Build GitHub link URLs on click instead of per-element hrefs
- Drop migrations from the pre-plugin install and old output

### 🎨 Styling

- *(ui)* A Graph fejléc-ikon balra zárva, fejléc-színnel
- *(ui)* Az aktív ág badge-e félkövér
- *(ui)* Az aktív ág badge-e 900-as vastagsággal

### ⚙️ Miscellaneous Tasks

- Ignore claude code worktrees
- Ignore the parked list
