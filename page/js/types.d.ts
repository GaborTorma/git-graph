/* A lap típusai a `tsc --checkJs`-hez (page/tsconfig.json) — a lapra nem kerül, a `page_code`
   csak a `.js` modulokat adja. A `graph_data`, a `changes` és a `file_diff` alakja a
   Python-oldalé (git_graph/graph.py, watch.py, diff.py): ha ott változik, itt is. */

/** Egy ref a commit mellett (`parse_refs`). */
interface Ref {
  kind: 'head' | 'detached' | 'branch' | 'remote' | 'tag';
  name: string;
  worktree?: string;
  default?: boolean;
}

/** Egy commit, vagy egy worktree commitolatlan ál-sora (`uncommitted`). */
interface Commit {
  sha: string;
  short: string;
  parents: string[];
  author: string;
  email: string;
  date: string;
  committed?: string;
  refs: Ref[];
  subject: string;
  body: string;
  lane: number;
  pushed?: boolean;
  stubs?: { lane: number; worktree: string }[];
  uncommitted?: boolean;
  worktree?: string;
  changed?: number;
}

/** Él a gráfban: a sorok a `commits` indexei. */
interface Edge {
  fromRow: number;
  fromLane: number;
  toRow: number;
  toLane: number;
  merge: boolean;
}

interface FileStat {
  path: string;
  add: number;
  del: number;
  bin: boolean;
  status?: string;
  anchor?: string;
  icon?: string;
  dirFrom?: number;
}

interface Stat {
  files: FileStat[];
  add: number;
  del: number;
}

interface Branch {
  name: string;
  sha: string;
  date: string;
  remote?: boolean;
  upstream?: string;
  track?: string;
  current?: boolean;
  worktree?: string | null;
  owner?: string | null;
}

interface Worktree {
  slug: string;
  name: string;
  path: string;
  branch: string;
  head: string;
  main: boolean;
  dirty: number;
  /** leválasztott HEAD-nél: az ág, amin a Claude app szerint a worktree állt */
  appBranch?: string;
  /** leválasztott HEAD-nél: a HEAD-commit előtte / mögötte az alapághoz */
  base?: [number, number];
}

interface Meta {
  repo: string;
  repoUrl: string;
  head: string;
  totalCommits: number;
  shown: number;
  dirty: number;
  generated: string;
  worktrees: Worktree[];
  remotes: string[];
  /** ág → előtte / mögötte: a remote párjához (`up`), az alapághoz (`base`), és a remote
      ágnál a helyi párjához (`local`) — `branch_tracks` */
  tracks: Record<string, { up?: [number, number]; base?: [number, number]; local?: [number, number] }>;
  base: string;
}

/** A `graph_data` tool válasza. */
interface GraphData {
  commits: Commit[];
  edges: Edge[];
  stats: Record<string, Stat>;
  branches: Branch[];
  meta: Meta;
  /** e-mail → data URI */
  avatars: Record<string, string>;
  /** ikonnév → SVG */
  fileIcons: Record<string, string>;
}

/** A `changes` tool válasza (long-poll). */
interface Changes {
  since: string;
  state: string;
  focus: { worktree: string | null; known: boolean } | null;
  version: string;
  installed: string | null;
}

/** A Claude app host-hídjának MCP-kliense (`window.claude.use('mcp')`). */
interface McpClient {
  callTool(server: string, tool: string, args: object,
           opts?: { cache?: boolean; signal?: AbortSignal }): Promise<{ payload: unknown }>;
}

/** A betöltő (page/loader.html) kontextusa. */
interface GitGraphContext {
  slug: string;
  repo: string;
  server: string;
  api: number;
  mcp: McpClient;
}

declare var GIT_GRAPH: GitGraphContext;

/* A lap DOM-ja HTML-elemekből áll (az SVG-t a gráf szövegként írja): a lekérdezések
   alapból HTMLElement-et adnak, nem Element-et. */
interface ParentNode {
  querySelector<K extends keyof HTMLElementTagNameMap>(selectors: K): HTMLElementTagNameMap[K] | null;
  querySelector<E extends HTMLElement = HTMLElement>(selectors: string): E | null;
  querySelectorAll<K extends keyof HTMLElementTagNameMap>(selectors: K): NodeListOf<HTMLElementTagNameMap[K]>;
  querySelectorAll<E extends HTMLElement = HTMLElement>(selectors: string): NodeListOf<E>;
}
interface Element {
  closest<E extends HTMLElement = HTMLElement>(selectors: string): E | null;
}
