/* A lap közös állapota: a betöltő kontextusa, az adat, a szűrt lista, a kinyitott
   commit. Az ES-modul exportja kívülről csak olvasható: írni a setterekkel lehet. */

/* A betöltő (az Artifact publikált lapja) adja: a repó slugja és neve, az MCP
   kliens. Az adatot a lap a Claude app host-hídján át a gépen futó
   `git-graph --mcp`-ből kéri (a SLUG repóét); induláskor csak az üres váz van. */
export const CTX = globalThis.GIT_GRAPH;
export const SLUG = CTX.slug;
export const MCP_SERVER = CTX.server;
export let DATA = { commits: [], edges: [], stats: {}, branches: [], avatars: {},
  meta: { repo: CTX.repo, repoUrl: '', head: '', totalCommits: 0, shown: 0, dirty: 0,
          generated: '', worktrees: [] } };
export const setData = d => { DATA = d; };

export let expanded = null;      // a kinyitott commit sha-ja
export const setExpanded = sha => { expanded = sha; };

export let visible = DATA.commits; // szűrés utáni lista
export const setVisible = list => { visible = list; };

/* Az ágszűrő által megtartott commitok (null: nincs ágszűrés) — a fejléc chipje ebből tudja,
   hogy a saját HEAD kiesett-e. */
export let branchKeep = null;
export const setBranchKeep = keep => { branchKeep = keep; };
