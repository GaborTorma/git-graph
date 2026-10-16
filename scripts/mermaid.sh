#!/bin/sh
# A lap Mermaidja: karcsú egyfájlos build (`page/vendor/mermaid.min.js`) és a licencek.
# A hivatalos `dist/mermaid.min.js` (12.x: 5,5 MB) nem fér át a host-hídon (a határ
# 3,67 és 5,08 MB között — mérve, docs/artifact-findings.md). Az esbuild a Mermaid
# ES-moduljaiból fog egy IIFE-t (`globalThis.mermaid`), a nehéz, ritkán kellő
# függőségek helyén csonkkal: `cytoscape` (mindmap, architecture), `katex` (képlet a
# feliratban), `@mermaid-js/parser` (pie, gitGraph, packet, radar, treemap). Az így
# kimaradó diagram hibát dob, a lap a kódnézetet mutatja. Az ELK (a 12-ben beépített,
# alapértelmezett elrendezés) benne marad. Kézzel, frissítéskor.
set -eu
MERMAID=12.2.0
ESBUILD=0.25.10
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cd "$TMP"
printf '{"name":"mermaid-build","private":true}' > package.json
pnpm add --silent --ignore-scripts "mermaid@$MERMAID" "esbuild@$ESBUILD"
printf "import mermaid from 'mermaid';\nglobalThis.mermaid = mermaid;\n" > entry.js
cat > build.mjs <<'EOF'
import { build } from 'esbuild';
const STUB = /^(cytoscape|cytoscape-.*|katex|@mermaid-js\/parser)$/;
const stub = { name: 'stub', setup(b) {
  b.onResolve({ filter: STUB }, a => ({ path: a.path, namespace: 'stub' }));
  b.onLoad({ filter: /.*/, namespace: 'stub' }, a => ({ loader: 'js', contents:
    `module.exports = new Proxy({}, { get: (_, k) => k === '__esModule' ? true : () => {
       throw new Error(${JSON.stringify(`ezt a diagramot a lap Mermaidja nem ismeri (${a.path})`)}); } });` }));
} };
await build({ entryPoints: ['entry.js'], bundle: true, format: 'iife', minify: true, target: 'es2020',
              legalComments: 'none', outfile: process.argv[2], plugins: [stub], logLevel: 'warning' });
EOF
node build.mjs "$ROOT/page/vendor/mermaid.min.js"
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
