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
