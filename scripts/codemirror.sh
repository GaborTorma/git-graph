#!/bin/sh
# A lap kódszerkesztője: a CodeMirror 6 egyfájlos buildje (`page/vendor/codemirror.min.js`) és a
# licencek. Minden kóddiffet ez rajzol (`page/js/cm.js`): a `@codemirror/merge` (egymás alatt
# `unifiedMergeView`, szélesen `MergeView`), a szintaxis Lezerrel (py, js/ts/jsx/tsx, json, css,
# html, md, yaml, toml — `lezer-toml`, sh — `@fig/lezer-bash`), a swift a `legacy-modes` módjával.
# Az esbuild egy IIFE-t fog (`globalThis.CM`); a lap lustán kéri (`page_code` `part:
# "codemirror"`), blobból futtatja, mint a Mermaidot (.claude/memory/mermaid-build.md). A buildnek
# a host-híd mérethatára alatt kell maradnia (.claude/memory/host-bridge-response-size.md).
# Kézzel, frissítéskor.
set -eu
ESBUILD=0.25.10
PKGS="@codemirror/state@6.7.6 @codemirror/view@6.43.15 @codemirror/merge@6.12.3
  @codemirror/language@6.13.1 @codemirror/commands@6.11.1 @codemirror/search@6.7.2
  @codemirror/legacy-modes@6.5.5 @codemirror/lang-python@6.2.1 @codemirror/lang-javascript@6.2.5
  @codemirror/lang-json@6.0.2 @codemirror/lang-css@6.3.1 @codemirror/lang-html@6.4.12
  @codemirror/lang-markdown@6.5.2 @codemirror/lang-yaml@6.1.3 @lezer/highlight@1.2.5
  lezer-toml@1.0.0 @fig/lezer-bash@1.2.5"
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cd "$TMP"
printf '{"name":"codemirror-build","private":true}' > package.json
# shellcheck disable=SC2086
pnpm add --silent --ignore-scripts $PKGS "esbuild@$ESBUILD"
cat > entry.js <<'EOF'
import { ChangeSet, Compartment, EditorSelection, EditorState, RangeSet, StateEffect, StateField, Text } from '@codemirror/state';
import { Decoration, EditorView, GutterMarker, ViewPlugin, WidgetType, drawSelection, gutterLineClass, gutterWidgetClass, keymap,
         lineNumbers } from '@codemirror/view';
import { Chunk, MergeView, diff, getChunks, getOriginalDoc, originalDocChangeEffect, rejectChunk,
         uncollapseUnchanged, unifiedMergeView, updateOriginalDoc } from '@codemirror/merge';
import { HighlightStyle, LRLanguage, LanguageSupport, StreamLanguage, syntaxHighlighting } from '@codemirror/language';
import { defaultKeymap, history, historyKeymap, indentWithTab, redo, undo } from '@codemirror/commands';
import { openSearchPanel, search, searchKeymap } from '@codemirror/search';
import { tags } from '@lezer/highlight';
import { python } from '@codemirror/lang-python';
import { javascript } from '@codemirror/lang-javascript';
import { json } from '@codemirror/lang-json';
import { css } from '@codemirror/lang-css';
import { html } from '@codemirror/lang-html';
import { markdown } from '@codemirror/lang-markdown';
import { yaml } from '@codemirror/lang-yaml';
import { parser as tomlParser } from 'lezer-toml';
import { parser as bashParser } from '@fig/lezer-bash';
import { swift } from '@codemirror/legacy-modes/mode/swift';

const lr = (name, parser) => new LanguageSupport(LRLanguage.define({ name, parser }));
// A nyelv a lap rövid nevéből (`cm.js`, `LANG`); ismeretlen névre null: sima szöveg.
const LANGS = {
  py: () => python(), js: () => javascript(), jsx: () => javascript({ jsx: true }),
  ts: () => javascript({ typescript: true }), tsx: () => javascript({ jsx: true, typescript: true }),
  json: () => json(), css: () => css(), html: () => html(), md: () => markdown(), yaml: () => yaml(),
  toml: () => lr('toml', tomlParser), sh: () => lr('sh', bashParser),
  swift: () => new LanguageSupport(StreamLanguage.define(swift)),
};
globalThis.CM = {
  ChangeSet, Compartment, EditorSelection, EditorState, RangeSet, StateEffect, StateField, Text,
  Decoration, EditorView, GutterMarker, ViewPlugin, WidgetType, drawSelection, gutterLineClass, gutterWidgetClass,
  keymap, lineNumbers,
  Chunk, MergeView, diff, getChunks, getOriginalDoc, originalDocChangeEffect, rejectChunk,
  uncollapseUnchanged, unifiedMergeView, updateOriginalDoc,
  HighlightStyle, syntaxHighlighting, tags,
  defaultKeymap, history, historyKeymap, indentWithTab, redo, undo,
  openSearchPanel, search, searchKeymap,
  lang: name => LANGS[name]?.() ?? null,
};
EOF
node_modules/.bin/esbuild entry.js --bundle --format=iife --minify --target=es2020 --legal-comments=none \
  --log-level=warning --outfile="$ROOT/page/vendor/codemirror.min.js"
N=node_modules/.pnpm
{
  echo "CodeMirror 6 (@codemirror/*, @lezer/*) — MIT"; echo
  cat node_modules/@codemirror/state/LICENSE; echo; echo "----"
  echo "lezer-toml — MIT"; echo
  cat node_modules/lezer-toml/LICENSE; echo; echo "----"
  echo "@fig/lezer-bash — MIT"; echo
  cat $N/@fig+lezer-bash@*/node_modules/@fig/lezer-bash/LICENSE 2>/dev/null \
    || echo "Copyright (c) Hercules Labs Inc. (Fig) — MIT, a csomag package.json-ja szerint"; echo; echo "----"
  echo "style-mod, w3c-keyname, crelt — MIT (Marijn Haverbeke)"
} > "$ROOT/page/vendor/codemirror.LICENSE"
