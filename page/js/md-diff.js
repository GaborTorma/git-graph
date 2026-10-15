/* ── Markdown-diff ───────────────────────────────────────────────────────────
   A `.md` fájl diffje renderelve. A teljes fájl (`full`) összefésült sorait
   (változatlan + törölt + hozzáadott) blokkokra bontjuk; egy blokk változott,
   ha van benne törölt vagy hozzáadott sor. A csak hozzáadott blokk zöld, a csak
   törölt piros; a vegyes (bekezdés, címsor, listaelem, idézet) előbb a régi
   változatával pirosan, alatta az újjal zölden, a cserélt szavak kiemelve. A
   táblázat és a kódblokk soronként színezett. A változatlan blokkokból csak a
   változás körüli (`MD_CONTEXT`) és az előtte álló legközelebbi címsor
   látszik, a többi `···`. Széles nézetben side-by-side (balra a régi, jobbra
   az új változat). A kapcsoló (`mdRaw`) a nyers diffre vált, a lap
   megjegyzi. Ha a két változat blokkszerkezete eltér (pl. új kódkerítés), a
   renderelés pontatlan lehet — arra való a nyers nézet. A ```mermaid blokk
   diagramként jelenik meg (`mermaid.js`): a változottnak a régi és az új
   változata, bennük a változott elemek pirosan, illetve zölden; amíg nincs
   kirajzolva, vagy ha hibás, a kódnézet látszik. */
import { KIND, alignRows, annotate, kindOf, oneSide, partnerOf, untouched } from './diff-html.js';
import { LANGS, highlight } from './syntax.js';
import { esc, ghLink } from './util.js';

const MD_CONTEXT = 1;          // blokk (a táblázatban sor)
const MD_CODE_CONTEXT = 3;     // a kódblokkban sor, mint a git diffjében

const MD_FENCE = /^\s{0,3}(`{3,}|~{3,})\s*([\w+#.-]*)/;
const MD_HEAD = /^\s{0,3}(#{1,6})(?:\s+|$)/;
const MD_SETEXT = /^\s{0,3}(=+|-+)\s*$/;
const MD_HR = /^\s{0,3}([-*_])(?:\s*\1){2,}\s*$/;
const MD_LI = /^(\s*)([-*+]|\d{1,9}[.)])\s+/;
const MD_QUOTE = /^\s{0,3}>\s?/;
const MD_TABLE = /^\s*\|/;
const MD_TABLE_SEP = /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/;
const MD_HTML = /^\s{0,3}<[!/a-zA-Z]/;

/* Az összefésült sorok blokkjai: { type, lines, … }. Az üres sor blokkhatár,
   magában nem blokk (az üres sorok változása így nem látszik). A hozzáadott
   sor, ha a párja (`partnerOf`) egy azonos fajta, még hozzáadott sor nélküli
   blokk (bármelyik) sora, nem nyit újat (pl. listaelem, címsor, bekezdés,
   táblázatsor; kódblokk igen): a párja blokkjába kerül, így a két változat
   egy helyen látszik — akkor is, ha a git a párt egy törölt bekezdés mögé
   tette (a táblázat utolsó sora és utána egy kivett bekezdés). */
function mdBlocks(lines) {
  const blocks = [], blockOf = new Map();
  let cur = null;
  const add = (b, l) => { b.lines.push(l); blockOf.set(l, b); };
  const start = (type, l, extra) => {
    const own = l.t === '+' && blockOf.get(partnerOf(l));
    if (own?.type === type && type !== 'code' && !own.lines.some(x => x.t === '+')) { add(own, l); cur = own; return; }
    cur = { type, lines: [], ...extra };
    blocks.push(cur);
    add(cur, l);
  };
  lines.forEach((l, i) => {
    const s = l.s;
    if (cur?.type === 'code' && cur.fence) {          // kódblokk belseje: a záró kerítésig
      add(cur, l);
      const t = s.trim();
      if (t.startsWith(cur.fence) && /^([`~]+|-{3,})$/.test(t)) cur = null;
      return;
    }
    if (!s.trim()) { cur = null; return; }
    // YAML front matter (pl. SKILL.md): kódként, különben a záró `---` címsort csinálna
    if (i === 0 && s === '---') { start('code', l, { fence: '---', lang: '' }); return; }
    const fence = MD_FENCE.exec(s);
    if (fence) {
      const info = fence[2].toLowerCase();
      start('code', l, { fence: fence[1], lang: LANGS[info] || '', mermaid: info === 'mermaid' });
      return;
    }
    if (cur?.type === 'p' && MD_SETEXT.test(s)) {    // aláhúzott címsor
      cur.type = 'h';
      cur.level = s.trim()[0] === '=' ? 1 : 2;
      cur.setext = true;
      add(cur, l);
      cur = null;
      return;
    }
    const head = MD_HEAD.exec(s);
    if (head) { start('h', l, { level: head[1].length }); cur = null; return; }
    if (MD_HR.test(s)) { start('hr', l); cur = null; return; }
    if (MD_TABLE.test(s)) { if (cur?.type === 'table') add(cur, l); else start('table', l); return; }
    if (MD_QUOTE.test(s)) { if (cur?.type === 'quote') add(cur, l); else start('quote', l); return; }
    const li = MD_LI.exec(s);
    if (li) { start('li', l, { indent: li[1].length }); return; }
    if (MD_HTML.test(s) && cur?.type !== 'p' && cur?.type !== 'li') {   // HTML-blokk: forrásként
      if (cur?.type === 'code') add(cur, l); else start('code', l, { lang: 'html' });
      return;
    }
    if (cur && ['p', 'li', 'quote', 'code'].includes(cur.type)) add(cur, l);
    else start('p', l);
  });
  return blocks;
}

/* A szó-kiemelés (`hl`) helyei jelölőkarakterekként a szövegbe: az inline
   renderelést túlélik, a végén `mdMarks` cseréli őket `<mark>`-ra. */
const MARK_ON = '', MARK_OFF = '', MARK_RE = /[]/g;
function marked(l) {
  let s = l.s;
  for (const [a, b] of [...(l.hl || [])].sort((x, y) => y[0] - x[0])) {
    s = s.slice(0, a) + MARK_ON + s.slice(a, b) + MARK_OFF + s.slice(b);
  }
  // Két formázójel (`**`, `__`, `~~`, `` ` ``) közé eső jelölő a futam elé kerül, hogy a jelpár összeálljon.
  let prev;
  do { prev = s; s = s.replace(/([*_~`])([]+)(?=[*_~`])/g, '$2$1'); } while (s !== prev);
  return s;
}
function mdMarks(html) {
  if (!html.includes(MARK_ON)) return html;
  const tpl = document.createElement('template');
  tpl.innerHTML = html;
  const walker = document.createTreeWalker(tpl.content, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  let on = false;
  for (const n of nodes) {
    if (!on && !n.data.includes(MARK_ON)) continue;
    const frag = document.createDocumentFragment();
    for (const part of n.data.split(/([])/)) {
      if (part === MARK_ON) on = true;
      else if (part === MARK_OFF) on = false;
      else if (part) frag.append(on ? Object.assign(document.createElement('mark'), { textContent: part }) : part);
    }
    n.replaceWith(frag);
  }
  return tpl.innerHTML;
}

/* Inline formázás: kód, link, kép (csak az alt szövege — a CSP külső képet nem
   enged), félkövér, dőlt, áthúzott. A kész elemek (`keep`) helyőrzőként várnak,
   hogy a későbbi cserék (pl. `_` egy URL-ben) ne nyúljanak beléjük. */
function mdInline(s) {
  const keep = [];
  const hold = html => `${keep.push(html) - 1}`;
  const link = (text, url) => {
    const href = url.replace(MARK_RE, '');
    // a `ghLink` két fele közé: a link szövege a többi cserén is átmegy (pl. **félkövér**)
    const [open, close] = /^https?:\/\//.test(href) ? ghLink(href, '\0').split('\0')
      : ['<span class="md-link">', '</span>'];
    return hold(open) + text + hold(close);
  };
  let out = '', last = 0;
  for (const m of s.matchAll(/(`+)([\s\S]+?)\1(?!`)/g)) {        // több sorra is átnyúlhat
    out += esc(s.slice(last, m.index)) + hold(`<code>${esc(m[2].replace(/\n/g, ' '))}</code>`);
    last = m.index + m[0].length;
  }
  out += esc(s.slice(last));
  return out
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, (_, alt) => hold(`<span class="md-img">${alt}</span>`))
    .replace(/\[([^\]]+)\]\(([^)\s]+)(?:\s+&quot;[^)]*&quot;)?\)/g, (_, text, url) => link(text, url))
    .replace(/&lt;(https?:\/\/[^\s&]+)&gt;/g, (_, url) => link(url, url))
    .replace(/(\*\*|__)(?=\S)(.+?)(?<=\S)\1/g, '<strong>$2</strong>')
    .replace(/(^|[^\w*])([*_])(?=[^\s*_])(.+?)(?<=[^\s*_])\2(?![\w*])/g, '$1<em>$3</em>')
    .replace(/~~(?=\S)(.+?)(?<=\S)~~/g, '<s>$1</s>')
    .replace(/ {2,}\n|\\\n/g, '<br>')
    .replace(/(\d+)/g, (_, i) => keep[i]);
}

// egyforma sorokból álló blokk jele (' add' / ' del' / ''), vegyesé null
const linesKind = ls => (ls.every(l => l.t === ls[0].t) ? KIND[ls[0].t] : null);

/* A sor `[start, end)` szakasza; a szó-kiemelés (`hl`) vele tolódik, különben a
   levágott jel (`- `, `#`, `>`, behúzás) hosszával elcsúszna. */
function cut(l, start, end = l.s.length) {
  const hl = (l.hl || []).map(([a, b]) => [Math.max(a, start) - start, Math.min(b, end) - start])
    .filter(([a, b]) => b > a);
  return { ...l, s: l.s.slice(start, end), hl };
}
const lead = (l, re) => cut(l, re.exec(l.s)?.[0].length || 0);
const trimmed = l => cut(l, l.s.length - l.s.trimStart().length, l.s.trimEnd().length);

/* Egy változat (a blokk sorainak egy része) renderelve, szöveges blokkra. */
function mdText(b, ls) {
  const text = n => mdInline(n.map(marked).join('\n'));
  if (b.type === 'h') {
    const src = b.setext ? ls.filter(l => !MD_SETEXT.test(l.s)) : ls;
    const t = src.map(l => { const h = lead(l, MD_HEAD); return cut(h, 0, h.s.replace(/\s+#+\s*$/, '').length); });
    return `<div class="md-h md-h${b.level}">${text(t)}</div>`;
  }
  if (b.type === 'quote') return `<blockquote>${text(ls.map(l => lead(l, MD_QUOTE)))}</blockquote>`;
  if (b.type === 'li') {
    const m = MD_LI.exec(ls[0].s);
    const mark = !m ? '' : /\d/.test(m[2]) ? esc(m[2]) : '•';
    const t = ls.map((l, i) => (i === 0 && m ? lead(l, MD_LI) : trimmed(l)));
    return `<div class="md-li" style="--md-ind:${b.indent || 0}"><span class="md-mk">${mark}</span>`
      + `<span>${text(t)}</span></div>`;
  }
  return `<p>${text(ls)}</p>`;
}

/* Összecsukás (blokk, táblázatsor, kódsor): ami változott, és a `ctx` távolságú
   szomszédai látszanak; `runsOf` a látszó és a kimaradó futamokat adja, a
   kimaradók helyére egy-egy `···` kerül. */
function near(changed, ctx) {
  const keep = changed.map(() => false);
  changed.forEach((c, i) => {
    if (c) for (let j = Math.max(0, i - ctx); j <= Math.min(changed.length - 1, i + ctx); j++) keep[j] = true;
  });
  return keep;
}
function runsOf(keep) {
  const runs = [];
  keep.forEach((k, i) => {
    const last = runs.at(-1);
    if (last?.keep === k) last.to = i + 1;
    else runs.push({ from: i, to: i + 1, keep: k });
  });
  return runs;
}

/* Egy blokk: kódblokk és táblázat soronként színezve, a többi változatonként
   (`textBlockHtml`). `side` ('-' / '+'): a side-by-side egyik oldala, az üres
   oldal helyőrző; nélküle az egymás alatti nézet (`oneSide`). A kódblokk és a
   táblázat sorai a két oldalon párban (`alignRows`), hogy egymás mellett ugyanazok a sorok látszódjanak. */
// side-by-side sor, ami tényleg változott (az újratördelt sor változatlan jelű, `styles`)
const realChange = r => !r.ctx && [r.a, r.b].some(l => l && l.t !== ' ');

function mdBlockHtml(b, side) {
  if (b.type !== 'code' && b.type !== 'table') return textBlockHtml(b, side);
  if (b.type === 'code') {
    // a kerítés sorai nem látszanak (a záró hiányozhat: a fájl vége vagy a levágás)
    const closed = b.fence && b.lines.length > 1 && b.lines.at(-1).s.trim().startsWith(b.fence);
    // a változásnak csak az érintett oldala, mint a nyers diffben (`oneSide`);
    // side-by-side-ban a két oldal párban, a hiányzó sor helyőrző
    const lines = b.fence ? b.lines.slice(1, closed ? -1 : undefined) : b.lines;
    const rows = side ? alignRows(lines) : null;
    const body = side ? rows.map(r => (side === '-' ? r.a : r.b)) : oneSide(lines);
    // Mint a nyers diffben: a változott sorok körül `MD_CODE_CONTEXT` sor, a
    // változatlan kódblokkból (környezetként) az eleje.
    const changed = side ? rows.map(realChange) : body.map(l => l.t !== ' ');
    const keep = changed.includes(true) ? near(changed, MD_CODE_CONTEXT) : body.map((_, i) => i < MD_CODE_CONTEXT);
    const code = '<pre class="md-code mono">' + runsOf(keep).map(r => (r.keep
      ? body.slice(r.from, r.to).map(l => (l
        ? `<div class="md-cl${kindOf(l)}">${highlight(l.s, l.hl, b.lang) || ' '}</div>`
        : '<div class="md-cl md-none"> </div>')).join('')
      : `<div class="md-cl md-skip" title="${r.to - r.from} változatlan sor">···</div>`)).join('') + '</pre>';
    // a diagram side-by-side-ban is egyszer, a teljes szélességen (`mdDiffHtml`)
    return b.mermaid && !side ? mermaidHtml(mermaidVersions(lines), code) : code;
  }
  if (b.type === 'table') {
    // A fejléc mindig, a többi sorból csak a változott és a szomszédai (a többi `···`):
    // egy nagy táblázat (pl. a repó térképe) egy sor miatt ne nyíljon ki egészben.
    const pairs = side ? alignRows(b.lines).filter(r => !MD_TABLE_SEP.test((r.a || r.b).s)) : null;
    const rows = side ? pairs.map(r => (side === '-' ? r.a : r.b)) : oneSide(b.lines).filter(l => !MD_TABLE_SEP.test(l.s));
    const keep = near(side ? pairs.map((r, i) => i > 0 && realChange(r)) : rows.map((l, i) => i > 0 && l.t !== ' '), MD_CONTEXT);
    keep[0] = true;
    const cells = l => marked(l).trim().replace(/^\|/, '').replace(/\|$/, '').split(/(?<!\\)\|/);
    const width = cells(rows.find(Boolean)).length;
    const row = (l, i) => {
      if (!l) return `<tr class="md-none"><td colspan="${width}"> </td></tr>`;
      const cell = i ? 'td' : 'th';
      return `<tr class="${kindOf(l).trim()}">`
        + cells(l).map(c => `<${cell}>${mdInline(c.trim())}</${cell}>`).join('') + '</tr>';
    };
    return '<div class="md-table"><table>' + runsOf(keep).map(r => (r.keep
      ? rows.slice(r.from, r.to).map((l, i) => row(l, r.from + i)).join('')
      : `<tr class="md-skip"><td colspan="${width}" title="${r.to - r.from} változatlan sor">···</td></tr>`))
      .join('') + '</table></div>';
  }
  return '';
}

/* Egy blokk melyik oldalán változott szó: [régi, új]. Ha csak az egyiken, a másik
   benne van ebben (csak beszúrás / csak törlés): elég az egyik változat, semleges
   háttérrel, a kiemelt szavaival. A szöveges és a diagram-blokk ezzel dönt. */
const sides = ls => [!untouched(ls, '-'), !untouched(ls, '+')];

/* Szöveges blokk (bekezdés, listaelem, címsor, idézet, vonal): a renderelt
   egység a blokk, nem a forrássor, ezért blokkszinten dől el, mi látszik. Ha a
   blokkban csak beszúrás van (`sides`), elég az új változat a kiemelt szavaival,
   semleges háttérrel (`only`); csak törlésnél a régi; különben mindkettő. A
   vegyes blokkban az egészében törölt / új sor (`whole`) egészében kiemelt. `side`: a side-by-side egyik
   oldala — az érintetlen oldal változatlanként, a hiányzó helyőrző. */
function textBlockHtml(b, side) {
  const kind = linesKind(b.lines);
  const whole = l => (kind === null && l.w === 'whole'
    ? { ...l, hl: [[l.s.length - l.s.trimStart().length, l.s.trimEnd().length]] } : l);
  const del = b.lines.filter(l => l.t !== '+').map(whole), add = b.lines.filter(l => l.t !== '-').map(whole);
  const [hasDel, hasAdd] = sides(b.lines);
  const html = (cls, ls) => `<div class="md-blk${cls}">${b.type === 'hr' ? '<hr>' : mdText(b, ls)}</div>`;
  const delCls = !hasDel ? '' : hasAdd ? ' del' : ' del only';
  const addCls = !hasAdd ? '' : hasDel ? ' add' : ' add only';
  if (side) {
    const ls = side === '-' ? del : add;
    if (!ls.length) return '<div class="md-blk md-none"></div>';
    return html(kind ?? (side === '-' ? delCls : addCls), ls);
  }
  if (kind !== null) return html(kind, b.lines);
  if (!hasDel) return html(addCls, add);
  if (!hasAdd) return html(delCls, del);
  return html(delCls, del) + html(addCls, add);
}

/* Mermaid-blokk: a kódnézet (tartalék) és a kirajzolandó változatok (`data-mmd`:
   forrás, a diff színe, a kiemelt szövegek — `marks` —, az egyetlen változat
   összevetési alapja — `base` —, és hogy egészében új / törölt-e — `whole`), a
   `renderMermaid` rajzolja ki. Változatlanul a mostani; egészében új vagy törölt
   blokknál az az egy; ha a változás csak beszúrás vagy csak törlés
   (`sides`), mint a szövegnél, a teljesebb változat a kiemelt szövegeivel;
   különben a régi és az új. */
function mermaidVersions(lines) {
  const without = t => lines.filter(l => l.t !== t).map(l => l.s).join('\n');
  const old = without('+'), now = without('-');
  const flow = [old, now].some(src => /^\s*(?:flowchart|graph)\b/m.test(src));
  const marks = t => lines.filter(l => l.t === t)
    .flatMap(l => (l.hl || []).filter(([a]) => !flow || inLabel(l.s, a)).map(([a, b]) => l.s.slice(a, b)));
  const [hasDel, hasAdd] = sides(lines);
  const versions = lines.every(l => l.t === ' ') ? [{ src: now, kind: '' }]
    : !now.trim() ? [{ src: old, kind: KIND['-'], whole: true }]
    : !old.trim() ? [{ src: now, kind: KIND['+'], whole: true }]
    : !hasAdd ? [{ src: old, kind: KIND['-'], marks: marks('-'), base: now }]
    : !hasDel ? [{ src: now, kind: KIND['+'], marks: marks('+'), base: old }]
    : [{ src: old, kind: KIND['-'], marks: marks('-') }, { src: now, kind: KIND['+'], marks: marks('+') }];
  return versions;
}
/* A flowchart sorában csak a felirat látszik a rajzon (`["…"]`, `{…}`, `(…)`, `|…|`,
   idézőjel); a csomópont-azonosító (`D`, `T`) nem. Egy él új célpontja így nem emel ki
   egy betűt egy idegen feliratban — az él maga színes (`markChanges`). */
function inLabel(s, at) {
  let quote = false, depth = 0, pipe = false;
  for (const c of s.slice(0, at)) {
    if (c === '"') quote = !quote;
    else if (quote) continue;
    else if ('[({'.includes(c)) depth++;
    else if (')]}'.includes(c)) depth = Math.max(0, depth - 1);
    else if (c === '|' && !depth) pipe = !pipe;
  }
  return quote || depth > 0 || pipe;
}
function mermaidHtml(versions, code) {
  return `<div class="md-mmd" data-mmd="${esc(JSON.stringify(versions))}">${code}<div class="md-mmd-view"></div></div>`;
}

/* A csak hozzáadott blokk helye. A változásban előbb az összes törölt, aztán
   az összes hozzáadott sor jön (egy átrendezett szövegnél sok bekezdésnyi), a
   párosított hozzáadott sorok pedig a párjuk blokkjába kerülnek: a pár nélküli
   új blokk így a törölt rész végére csúszna. Helyette a következő párosított
   blokk elé kerül (a köztes törölt blokkok után); ha nincs ilyen, a helyén marad. */
function placeAdded(blocks, lines) {
  const at = new Map(lines.map((l, i) => [l, i]));
  const blockOf = new Map(blocks.flatMap(b => b.lines.map(l => [l, b])));
  const added = b => b.lines.every(l => l.t === '+');
  const before = new Map();
  for (const b of blocks.filter(added)) {
    for (let i = at.get(b.lines.at(-1)) + 1; i < lines.length && lines[i].t !== ' '; i++) {
      const o = blockOf.get(lines[i]);
      if (lines[i].t === '+' && o && !added(o)) { before.set(o, [...(before.get(o) || []), b]); break; }
    }
  }
  const moved = new Set([...before.values()].flat());
  return blocks.filter(b => !moved.has(b)).flatMap(b => [...(before.get(b) || []), b]);
}

/* A side-by-side sorai: [régi, új] blokkpárok. A legtöbb blokk mindkét oldalon
   ugyanaz (a két változata); a pár nélküli törölt blokkok és az utánuk jövő
   új blokkok (két párosított vagy változatlan blokk közt) egymás mellé
   kerülnek, mint a nyers diffben (`alignRows`); a többlet egyedül. A
   `whole` blokk (diagram) magában marad. */
function splitPairs(list, whole) {
  const only = (b, t) => !whole(b) && b.lines.every(l => l.t === t);
  const out = [];
  for (let i = 0; i < list.length;) {
    if (!only(list[i], '-') && !only(list[i], '+')) { out.push([list[i], list[i]]); i++; continue; }
    let j = i; while (j < list.length && only(list[j], '-')) j++;
    let k = j; while (k < list.length && only(list[k], '+')) k++;
    for (let x = 0; x < Math.max(j - i, k - j); x++) out.push([i + x < j ? list[i + x] : null, j + x < k ? list[j + x] : null]);
    i = k;
  }
  return out;
}

/* A diagram előtti változatlan címsor side-by-side-ban is egyszer, a diagrammal együtt
   a teljes szélességen — különben a másik oszlopban árván maradna. */
const aboveMermaid = (b, next) => b.type === 'h' && next?.mermaid && b.lines.every(l => l.t === ' ');

export function mdDiffHtml(d) {
  if (d.binary) return '<p class="diff-note">Bináris fájl.</p>';
  annotate(d);
  const lines = d.hunks.flatMap(h => h.lines);
  const blocks = placeAdded(mdBlocks(lines), lines);
  // a tiszta újratördelés (`styles`: `same` / `drop`) nem változás
  const shownLines = blocks.map(b => oneSide(b.lines));
  const changed = shownLines.map(ls => ls.some(l => l.t !== ' '));
  if (!changed.includes(true)) {
    return `<p class="diff-note">${d.hunks.length ? 'Csak a tördelés vagy üres sorok változtak.'
      : 'Nincs megjeleníthető változás.'}</p>`;
  }
  const shown = near(changed, MD_CONTEXT);
  let heading = -1;          // a változás előtti legközelebbi címsor is látszik: hol járunk a doksiban
  blocks.forEach((b, i) => {
    if (changed[i] && heading >= 0) shown[heading] = true;
    if (b.type === 'h') heading = i;
  });
  // Egy blokk (hunk) a `···`-ig: fókuszálható, a nyilak blokkról blokkra lépnek.
  // Mint a nyers diffnél: egymás alatti és side-by-side nézet, a szélesség dönt;
  // a side-by-side-ban blokkonként egy sor, balra a régi, jobbra az új változat.
  const view = html => runsOf(shown).map(r => (r.keep
    ? `<div class="hunk md-doc" tabindex="-1">${html(blocks.slice(r.from, r.to))}</div>`
    : `<p class="diff-gap" title="${r.to - r.from} változatlan blokk">···</p>`)).join('');
  const uni = view(list => list.map(b => mdBlockHtml(b)).join(''));
  const kinds = new Set(shownLines.flat().map(l => l.t));
  const next = new Map(blocks.map((b, i) => [b, blocks[i + 1]]));
  const half = (b, side) => (b ? mdBlockHtml(b, side) : '<div class="md-blk md-none"></div>');
  const split = list => splitPairs(list, b => b.mermaid || aboveMermaid(b, next.get(b))).map(([a, b]) => (a === b
    && (a.mermaid || aboveMermaid(a, next.get(a)))
    ? `<div class="md-mmd-row">${mdBlockHtml(a)}</div>`             // a diagram és a címsora a teljes szélességen
    : `<div class="md-row"><div>${half(a, '-')}</div><div>${half(b, '+')}</div></div>`)).join('');
  const out = kinds.has('+') && kinds.has('-')
    ? `<div class="diff-uni">${uni}</div><div class="diff-split">${view(split)}</div>`
    : `<div>${uni}</div>`;
  return mdMarks(out) + (d.truncated ? '<p class="diff-note">… a fájl túl hosszú, a vége le van vágva.</p>' : '');
}

/* A side-by-side két oldalán a párban álló táblázatsorok és kódsorok magassága
   egyforma: a kettő közül a magasabb (a tördelés oldalanként más). Kirajzolás
   után és szélességváltozáskor fut; ha a side-by-side nem látszik (keskeny
   panel), csak visszaáll. */
export function syncRows(root) {
  const pairs = [...root.querySelectorAll('.diff-split .md-row')]
    .map(r => [...r.children].map(c => [...c.querySelectorAll('tr, .md-cl')]))
    .filter(([a, b]) => a.length && a.length === b.length);
  for (const [a, b] of pairs) for (const el of [...a, ...b]) el.style.height = '';
  if (!root.querySelector('.diff-split')?.getClientRects().length) return;
  const heights = pairs.map(([a, b]) => a.map((x, i) =>
    Math.max(x.getBoundingClientRect().height, b[i].getBoundingClientRect().height)));
  pairs.forEach(([a, b], k) => a.forEach((x, i) => { x.style.height = b[i].style.height = `${heights[k][i]}px`; }));
}
