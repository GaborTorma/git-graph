#!/bin/sh
# A lap Mermaidja: karcsú egyfájlos build (`page/vendor/mermaid.min.js`) és a licencek.
# A hivatalos `dist/mermaid.min.js` (12.x: 5,5 MB) nem fér át a host-hídon (a határ
# 3,67 és 5,08 MB között — mérve, .claude/memory/host-bridge-response-size.md). Az esbuild a Mermaid
# ES-moduljaiból fog egy IIFE-t (`globalThis.mermaid`), a nehéz, ritkán kellő
# függőségek helyén csonkkal: `cytoscape` (mindmap, architecture), `katex` (képlet a
# feliratban), `@mermaid-js/parser` (pie, gitGraph, packet, radar, treemap). Az így
# kimaradó diagram hibát dob, a lap a kódnézetet mutatja. Az ELK (a 12-ben beépített,
# alapértelmezett elrendezés) benne marad. Egy javítással: az ER-diagramban a vonal az
# entitás mellett `ER_STUB` egységgel tovább fut egyenesen, csak utána fordul. Így a
# kapcsolat jelölője (kör, villa) nem a fordulóra kerül. Az ELK az entitást ennyivel
# magasabbnak látja (fent és lent), a vonal végét utána a valódi dobozig húzzuk. A
# rétegek közti hely (`edgeNodeBetweenLayers`) nem jó erre: a felirat is külön réteg,
# körülötte is nőne. A csomópont margóját az ELK nem veszi figyelembe. Kézzel, frissítéskor.
set -eu
MERMAID=12.2.0
ESBUILD=0.25.10
ER_STUB=30
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cd "$TMP"
printf '{"name":"mermaid-build","private":true}' > package.json
pnpm add --silent --ignore-scripts "mermaid@$MERMAID" "esbuild@$ESBUILD"
printf "import mermaid from 'mermaid';\nglobalThis.mermaid = mermaid;\n" > entry.js
cat > build.mjs <<'EOF'
import { build } from 'esbuild';
import { readFile } from 'node:fs/promises';
const STUB = /^(cytoscape|cytoscape-.*|katex|@mermaid-js\/parser)$/;
const stub = { name: 'stub', setup(b) {
  b.onResolve({ filter: STUB }, a => ({ path: a.path, namespace: 'stub' }));
  b.onLoad({ filter: /.*/, namespace: 'stub' }, a => ({ loader: 'js', contents:
    `module.exports = new Proxy({}, { get: (_, k) => k === '__esModule' ? true : () => {
       throw new Error(${JSON.stringify(`ezt a diagramot a lap Mermaidja nem ismeri (${a.path})`)}); } });` }));
} };
// Az ER-entitás az ELK-nak `m`-mel magasabb fent és lent; az elrendezés után a doboz a valódi
// méretére áll vissza, a vonal fenti / lenti vége a dobozig ér. Ha a Mermaid forrása
// változott, a build elbukik.
const m = Number(process.argv[3]);
const ER_STUBS = `
function erStubs(graph, m) {
  const nodes = graph.children ?? [];
  for (const e of graph.edges ?? []) for (const s of e.sections ?? []) for (const p of [s.startPoint, s.endPoint]) {
    const n = nodes.find(n => p.x > n.x - 0.5 && p.x < n.x + n.width + 0.5
                            && (Math.abs(p.y - n.y) < 0.5 || Math.abs(p.y - n.y - n.height) < 0.5));
    if (n) p.y += Math.abs(p.y - n.y) < 0.5 ? m : -m;
  }
  for (const n of nodes) { n.y += m; n.height -= 2 * m; }
}
`;
const ER_PATCH = [
  ['addVertices(data4Layout.nodes, elkGraph, nodeDb, elkContext);',
   `if (data4Layout.type === "er") for (const n of Object.values(nodeDb)) n.height += 2 * ${m};`],
  ['const graph = await runElkLayout(elk, layoutState.elkGraph, elkContext.log);',
   `if (data4Layout.type === "er") erStubs(graph, ${m});`],
];
const erStub = { name: 'er-stub', setup(b) {
  b.onLoad({ filter: /[\\/]elk-[\w-]+\.mjs$/ }, async a => {
    let src = await readFile(a.path, 'utf8');
    for (const [at, add] of ER_PATCH) {
      if (src.split(at).length !== 2) throw new Error(`${a.path}: nincs benne pontosan egyszer: ${at}`);
      src = src.replace(at, `${at}\n${add}`);
    }
    return { loader: 'js', contents: src + ER_STUBS };
  });
} };
await build({ entryPoints: ['entry.js'], bundle: true, format: 'iife', minify: true, target: 'es2020',
              legalComments: 'none', outfile: process.argv[2], plugins: [stub, erStub], logLevel: 'warning' });
EOF
node build.mjs "$ROOT/page/vendor/mermaid.min.js" "$ER_STUB"
N=node_modules/.pnpm
{
  echo "mermaid $MERMAID — MIT"; echo
  cat node_modules/mermaid/LICENSE; echo; echo "----"
  echo "elkjs — EPL-2.0"; echo
  cat $N/elkjs@*/node_modules/elkjs/LICENSE.md; echo; echo "----"
  echo "d3 (d3-*) — ISC"; echo
  cat $N/d3@7*/node_modules/d3/LICENSE; echo; echo "----"
  echo "dompurify — Apache-2.0 / MPL-2.0"; echo
  cat $N/dompurify@*/node_modules/dompurify/LICENSE
} > "$ROOT/page/vendor/mermaid.LICENSE"
