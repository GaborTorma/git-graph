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
