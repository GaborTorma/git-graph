/* A gépen futó git-graph hívása a Claude app host-hídján át. */
import { CTX, MCP_SERVER, SLUG } from './state.js';

export function mcpSource() {
  const mcp = CTX.mcp;
  const call = (tool, args, signal) => mcp.callTool(MCP_SERVER, tool, { repo: SLUG, ...args },
    signal ? { cache: false, signal } : { cache: false }).then(r => r.payload);
  return { changes: (since, wait, signal) => call('changes', { since, wait }, signal),
           data: () => call('graph_data'),
           diff: (sha, path, full) => call('file_diff', { sha, path, full }) };
}

/* MCP-hibakód → teendő. A nem `retryable` hibák nem múlnak el maguktól:
   ott megáll a pollozás (újratöltés próbálja újra). */
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
