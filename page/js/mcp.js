/* A gépen futó git-graph hívása a Claude app host-hídján át. */
import { CTX, MCP_SERVER, SLUG } from './state.js';

/* A host sűrű hívásnál visszafog (`rate_limited`, `retryAfterMs`; .claude/memory/host-bridge-long-poll.md):
   ennyiszer próbáljuk újra, a kért várakozással (alapból `RETRY_MS`, legfeljebb `RETRY_MAX_MS`). */
const RETRIES = 3, RETRY_MS = 600, RETRY_MAX_MS = 5000;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

export function mcpSource() {
  const mcp = CTX.mcp;
  const call = async (tool, args, signal) => {
    for (let n = 0; ; n++) {
      try {
        const r = await mcp.callTool(MCP_SERVER, tool, { repo: SLUG, ...args }, signal ? { cache: false, signal } : { cache: false });
        return r.payload;
      } catch (e) {
        if (e?.code !== 'rate_limited' || n >= RETRIES || signal?.aborted) throw e;
        await pause(Math.min(RETRY_MAX_MS, Number(e.retryAfterMs) || RETRY_MS * (n + 1)));
      }
    }
  };
  return { changes: (since, wait, signal) => /** @type {Promise<Changes>} */ (call('changes', { since, wait }, signal)),
           data: () => /** @type {Promise<GraphData>} */ (call('graph_data')),
           diff: (sha, path, full) => call('file_diff', { sha, path, full }),
           // a kép egy oldala (`old` / `new`), külön hívásban; `image`: a markdown-fájl egy képe
           side: (sha, path, side, image) => call('file_diff', { sha, path, side, ...(image == null ? {} : { image }) }),
           // a kódnézet: a fájl adatai (`text`), oldalanként a teljes szöveg (`textSide`)
           text: (sha, path) => call('file_diff', { sha, path, text: true }),
           textSide: (sha, path, side) => call('file_diff', { sha, path, side, text: true }),
           // a teljes nézet fája: a commit (WIP soron a munkakönyvtár) fájljai; `dir`: egy mappa, `grep`: tartalomkeresés
           tree: (sha, opts = {}) => call('file_tree', { sha, ...opts }),
           // az Uncommitted sor fájljának mentése, az ismert lemezállapot (`base`) hashével
           write: (sha, path, text, base) => call('write_file', { sha, path, text, base }),
           codemirror: () => /** @type {Promise<{ js: string }>} */ (call('page_code', { api: CTX.api, part: 'codemirror' })),
           mermaid: () => /** @type {Promise<{ js: string }>} */ (call('page_code', { api: CTX.api, part: 'mermaid' })),
           // a lap betűi (Anthropic Sans: `font`, Mono: `font-mono`) base64-ben: a keretben nincsenek meg (`font.js`)
           font: part => /** @type {Promise<{ woff2: string }>} */ (call('page_code', { api: CTX.api, part })) };
}

/* Végleges hiba: a lap engedélye vagy az app configja hiányzik — újrapróba nem segít, itt
   megáll a pollozás (újratöltés próbálja újra). A többi akkor is elmúlhat, ha nem
   `retryable`: pl. `upstream_error`, ha a nyitott hívás a gép alvása alatt lejárt, és az app
   közben újraindította a szervert. */
export const mcpFatal = e => ['server_not_connected', 'cancelled', 'not_in_manifest'].includes(e?.code);

/* MCP-hibakód → teendő. */
export function mcpProblem(e) {
  switch (e?.code) {
    case 'server_not_connected':
      return 'A lap nem éri el a gépeden futó git-graph-ot. Élő adat csak a Claude appban, a saját '
        + 'gépeden jön — és ott is csak, ha az app configjában benne van (a git-graph plugin teszi be; utána az app újraindítása).';
    case 'cancelled':
      return 'A git-graph szervert nem engedélyezted ehhez a laphoz — töltsd újra, és engedd meg.';
    case 'not_in_manifest':
      return 'A git-graph szervert nem engedélyezted ehhez a laphoz (töltsd újra, és engedd meg), '
        + 'vagy a lap elavult: nyiss egy sessiont a repóban, a hook újrapublikálja.';
    case 'tool_error':
      return 'A git-graph hibát jelzett: ' + e.message;
    default:
      return 'A git-graph nem válaszol (' + (e?.code || e) + ').';
  }
}
