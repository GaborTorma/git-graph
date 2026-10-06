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
