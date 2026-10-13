/* ── Szintaxis-színezés ──────────────────────────────────────────────────
   Soronkénti, könnyű tokenizáló a gyakori nyelvcsaládokra: megjegyzés,
   string, kulcsszó, szám, függvényhívás, típus. Többsoros string és
   megjegyzés belseje sima szöveg marad — a diff soronként jön. A szó-kiemelés
   (`hl`, a Python számolja) a tokenek fölött, karakterpontosan fut. */
import { esc } from './util.js';

const KW = {
  py: 'and as assert async await break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return True try while with yield',
  js: 'async await break case catch class const continue default delete do else export extends false finally for from function if import in instanceof let new null of return static super switch this throw true try typeof undefined var void while yield',
  sh: 'case do done elif else esac export fi for function if in local return then until while',
  css: 'important',
};
export const LANGS = {
  py: 'py', js: 'js', mjs: 'js', cjs: 'js', ts: 'js', tsx: 'js', jsx: 'js', json: 'json',
  css: 'css', html: 'html', md: 'md', sh: 'sh', bash: 'sh', zsh: 'sh', toml: 'sh', yml: 'sh', yaml: 'sh',
  swift: 'js', go: 'js', rs: 'js', java: 'js', kt: 'js', c: 'js', h: 'js', cpp: 'js',
};
export function langOf(path) {
  const name = path.split('/').pop();
  const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : '';
  return LANGS[ext] || (name === 'git-graph' ? 'py' : '');
}
const TOKENIZERS = {};
function tokenizer(lang) {
  if (TOKENIZERS[lang]) return TOKENIZERS[lang];
  const comment = { py: '#.*$', sh: '#.*$', js: '//.*$|/\\*.*?(?:\\*/|$)', css: '/\\*.*?(?:\\*/|$)',
                    html: '<!--.*?(?:-->|$)' }[lang];
  const parts = [
    comment && `(?<cm>${comment})`,
    `(?<st>${lang === 'py' ? '[rbfuRBFU]{0,2}' : ''}"(?:[^"\\\\]|\\\\.)*"?|'(?:[^'\\\\]|\\\\.)*'?${lang === 'js' ? '|`(?:[^`\\\\]|\\\\.)*`?' : ''})`,
    KW[lang] && `(?<kw>\\b(?:${KW[lang].split(' ').join('|')})\\b)`,
    '(?<nu>\\b\\d[\\d_.]*(?:e[+-]?\\d+)?\\b|\\b0x[\\da-f]+\\b)',
    lang === 'css' ? '(?<fn>[\\w-]+(?=\\s*:))' : '(?<fn>\\b[A-Za-z_$][\\w$]*(?=\\s*\\())',
    lang !== 'css' && '(?<ty>\\b[A-Z][A-Za-z0-9_]*[a-z][A-Za-z0-9_]*\\b)',
  ].filter(Boolean);
  TOKENIZERS[lang] = new RegExp(parts.join('|'), lang === 'css' ? 'gi' : 'g');
  return TOKENIZERS[lang];
}
const MD_RE = /(?<kw>^#{1,6} .*$)|(?<st>`[^`]*`)|(?<ty>\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/g;
const HTML_RE = /(?<cm><!--.*?(?:-->|$))|(?<kw><\/?[\w-]+|\/?>)|(?<fn>\s[\w:-]+(?==))|(?<st>"[^"]*"?|'[^']*'?)/g;

export function highlight(s, hl, lang) {
  const re = lang === 'md' ? MD_RE : lang === 'html' ? HTML_RE : lang ? tokenizer(lang) : null;
  const cls = new Array(s.length).fill('');
  if (re) {
    re.lastIndex = 0;
    for (const m of s.matchAll(re)) {
      const kind = Object.keys(m.groups).find(k => m.groups[k] !== undefined);
      const start = m.index + (kind === 'fn' && lang === 'html' ? 1 : 0);
      for (let i = start; i < m.index + m[0].length; i++) cls[i] = kind;
    }
  }
  const mark = new Array(s.length).fill(false);
  for (const [a, b] of hl || []) for (let i = a; i < b; i++) mark[i] = true;
  let out = '', i = 0;
  while (i < s.length) {
    let j = i;
    while (j < s.length && cls[j] === cls[i] && mark[j] === mark[i]) j++;
    let seg = esc(s.slice(i, j));
    if (cls[i]) seg = `<span class="s-${cls[i]}">${seg}</span>`;
    if (mark[i]) seg = `<mark>${seg}</mark>`;
    out += seg;
    i = j;
  }
  return out;
}
