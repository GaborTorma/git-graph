/* ── Mermaid-diagramok a markdown-diffben ──
   A `md-diff.js` a ```mermaid blokkot kódnézetként rajzolja, a kirajzolandó
   változatokkal (`.md-mmd[data-mmd]`); ez cseréli diagramra. A Mermaidot (karcsú
   build, 3,7 MB, `page/vendor/`) csak az első diagramnál kéri a gépen futó
   git-graph-tól (`page_code` `part: 'mermaid'`), és blobból futtatja (az Artifact
   CSP-je engedi — mérve, .claude/memory/mermaid-build.md). A rajz a lap palettáján
   (`base` téma), `neo` stílusban, a Mermaid 12 alapértelmezett ELK-elrendezésével.
   A változott diagram változataiban a változott elemek színesek (`markChanges`), a változott
   szöveg kiemelve (`markText`); a diagramok egymás mellett, ha elférnek. A diagram a lap témáját követi: váltáskor
   újrarajzol. Ha a Mermaid nem tölthető be, vagy a diagram hibás, a kódnézet
   marad, alatta a hibával. */
import { syncRows } from './md-diff.js';
import { esc } from './util.js';

let lib = null;              // a Mermaid betöltésének ígérete; hibánál a következő próba újrakéri
let queue = Promise.resolve();   // a rajzolások sorban: a téma (`initialize`) közös
let seq = 0;
// A Mermaid 16 px-es betűvel rajzol, a lap 13 px-essel: a diagram ennyiszeresre kicsinyítve
// (a felirata így a kódnézetéhez illő ~12 px), a keskeny panelen ennél is kisebbre.
const SCALE = 0.75;
const FRAME = 20;            // a keret belső margója és szegélye (`.md-mmd-fig`)

function load(get) {
  lib ??= get().then(({ js }) => new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = URL.createObjectURL(new Blob([js], { type: 'text/javascript' }));
    s.onload = () => resolve(globalThis.mermaid);
    s.onerror = () => reject(new Error('a Mermaid nem indult el'));
    document.head.append(s);
  })).catch(e => { lib = null; throw e; });
  return lib;
}

const root = document.documentElement;
const darkMedia = matchMedia('(prefers-color-scheme: dark)');
const dark = () => (root.getAttribute('data-theme') || (darkMedia.matches ? 'dark' : 'light')) === 'dark';

/* A Mermaid `base` témája a lap CDS-palettáján (page.css): a csomópont a háttérnél
   világosabb (sötétben sötétebb), a keret és a vonal halk. A `base` téma a
   színekből számol, ezért itt tömör hex áll, nem a lap áttetsző `--border`-e. */
const PALETTE = {
  light: { background: '#ffffff', mainBkg: '#ffffff', primaryColor: '#ffffff', primaryTextColor: '#0b0b0b',
           primaryBorderColor: '#cbcac6', secondaryColor: '#f0f0ef', tertiaryColor: '#e4e4e3',
           lineColor: '#898781', textColor: '#20201f', clusterBkg: '#f0f0ef', clusterBorder: '#dcdcda',
           edgeLabelBackground: '#ffffff', nodeTextColor: '#0b0b0b',
           actorBkg: '#ffffff', actorBorder: '#cbcac6', actorTextColor: '#0b0b0b', signalColor: '#6d6b67',
           signalTextColor: '#20201f', labelBoxBkgColor: '#f0f0ef', labelBoxBorderColor: '#dcdcda',
           loopTextColor: '#6d6b67', activationBkgColor: '#e4e4e3', noteBkgColor: '#f0f0ef' },
  dark: { darkMode: true, background: '#1a1a19', mainBkg: '#272727', primaryColor: '#272727', primaryTextColor: '#f0efec',
          primaryBorderColor: '#4f4f4e', secondaryColor: '#383838', tertiaryColor: '#151515',
          lineColor: '#898781', textColor: '#e1e0d9', clusterBkg: '#151515', clusterBorder: '#383838',
          edgeLabelBackground: '#1a1a19', nodeTextColor: '#f0efec',
          actorBkg: '#272727', actorBorder: '#4f4f4e', actorTextColor: '#f0efec', signalColor: '#a5a49a',
          signalTextColor: '#e1e0d9', labelBoxBkgColor: '#151515', labelBoxBorderColor: '#383838',
          loopTextColor: '#a5a49a', activationBkgColor: '#383838', noteBkgColor: '#383838' },
};
const themeVariables = () => ({ ...PALETTE[dark() ? 'dark' : 'light'],
                                fontFamily: getComputedStyle(root).getPropertyValue('--font-ui').trim() });

function fail(box, e) {
  box.classList.remove('md-mmd-on');
  box.querySelector('.md-mmd-view').innerHTML = `<p class="md-mmd-err">A diagram nem rajzolható ki: ${
    esc(String(e?.message || e?.code || e).trim())}</p>`;
}

/* Az irány a helyhez: a flowchart a forrás tengelyén és elforgatva (TB ↔ LR, BT ↔ RL)
   is kirajzolódik, és az kerül a lapra, amelyik jobban elfér (`fit`). A forrás
   első sora adja az irányt (`flowchart LR`, `graph TD`); a front matter és a `%%`
   komment előtte lehet. Más diagram (szekvencia, state, …) marad, ahogy írták. */
const FLIP = { TB: 'LR', TD: 'LR', BT: 'RL', LR: 'TB', RL: 'BT' };
function turned(src) {
  const lines = src.split('\n');
  let i = lines[0]?.trim() === '---' ? lines.findIndex((l, k) => k > 0 && l.trim() === '---') + 1 : 0;
  while (i < lines.length && (!lines[i].trim() || lines[i].trim().startsWith('%%'))) i++;
  const m = /^(\s*(?:flowchart|graph))(?:[ \t]+(TB|TD|BT|RL|LR))?(?![\w-])/.exec(lines[i] || '');
  if (!m) return null;
  lines[i] = `${m[1]} ${FLIP[m[2] || 'TB']}${lines[i].slice(m[0].length)}`;
  return lines.join('\n');
}

/* A kirajzolt változat természetes mérete (a Mermaid a `max-width`-be és a
   `viewBox`-ba írja). */
function size(svg) {
  const w = parseFloat(/max-width:\s*([\d.]+)px/.exec(svg)?.[1] || '0');
  const box = /viewBox="[-\d.]+ [-\d.]+ ([\d.]+) ([\d.]+)"/.exec(svg);
  return { w: w || parseFloat(box?.[1] || '0'), h: parseFloat(box?.[2] || '0') };
}

/* Mennyire fér el a `figs` a `room` szélességen: előbb az számít, hogy két változat
   egymás mellé kerül-e, aztán a kicsinyítés (minél kevesebb), végül a magasság. */
const GAP = 6;               // a változatok köze (`.md-mmd-view`)
function fit(figs, room) {
  const outer = figs.map(({ w, h }) => ({ w: w * SCALE + FRAME, h: h * SCALE + FRAME }));
  const side = outer.length < 2 || outer.reduce((a, o) => a + o.w, 0) + GAP * (outer.length - 1) <= room;
  const scales = outer.map(o => side && outer.length > 1 ? 1 : Math.min(1, room / o.w));
  const heights = outer.map((o, i) => o.h * scales[i]);
  return [side ? 1 : 0, Math.round(Math.min(...scales) * 100),
          -(side ? Math.max(...heights) : heights.reduce((a, b) => a + b, 0))];
}
const better = (a, b) => { for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] > b[i]; return false; };

const drawn = new WeakMap();   // doboz → a változatok rajzai mindkét irányban, az összevetési alappal

async function draw(boxes, mermaid) {
  mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', suppressErrorRendering: true,
                       theme: 'base', themeVariables: themeVariables(), look: 'neo' });
  for (const box of boxes) {
    if (!box.isConnected) continue;
    try {
      const versions = JSON.parse(box.dataset.mmd), out = [];
      const svgOf = async src => {
        const id = `gg-mmd-${++seq}`;
        try {
          return (await mermaid.render(id, src)).svg;
        } finally {
          document.getElementById('d' + id)?.remove();     // a Mermaid ideiglenes eleme
        }
      };
      const flips = versions.map(v => turned(v.src));
      const flip = flips.every(Boolean);                  // a két változat egy irányban
      for (const [i, v] of versions.entries()) {
        // az egyetlen változat összevetési alapja: csak a változott elemek kereséséhez, nem látszik
        out.push({ as: await svgOf(v.src), flipped: flip ? await svgOf(flips[i]) : '',
                   base: v.base?.trim() ? await svgOf(v.base) : '' });
      }
      drawn.set(box, { versions, out });
      delete box.dataset.mmdDir;
      place(box);
    } catch (e) {
      drawn.delete(box);
      fail(box, e);
    }
  }
}

/* A rajzok közül a helyhez illő irány a lapra: a változott elemek színesek, a keret a
   diagram (kicsinyített) szélességét kapja, a fele legalább ekkorát — két változat így
   egymás mellé kerül, ha elfér, különben egymás alá. Rejtett nézetben (nincs
   szélessége) a forrás iránya marad, amíg meg nem jelenik. */
function place(box) {
  const d = drawn.get(box);
  if (!d) return;
  const room = box.clientWidth - 17;                  // a `.md-mmd-view` bal margója
  let dir = box.dataset.mmdDir || 'as';
  if (room > 0 && d.out.every(o => o.flipped)) {
    const as = fit(d.out.map(o => size(o.as)), room), flipped = fit(d.out.map(o => size(o.flipped)), room);
    dir = better(flipped, as) ? 'flipped' : 'as';
  }
  if (box.dataset.mmdDir === dir && box.classList.contains('md-mmd-on')) return;
  box.dataset.mmdDir = dir;
  const view = box.querySelector('.md-mmd-view');
  view.innerHTML = d.versions.map((v, i) => {
    const kind = (v.kind ? ` md-mmd-${v.kind.trim()}` : '') + (v.whole ? ' md-mmd-whole' : '');
    return `<div class="md-mmd-half"><div class="md-mmd-fig${kind}">${d.out[i][dir]}</div></div>`;
  }).join('');
  const svgs = [...view.querySelectorAll('.md-mmd-fig > svg')];
  svgs.forEach((svg, i) => {
    if (d.out[i].base) {
      const base = document.createElement('div');
      base.innerHTML = d.out[i].base;
      markChanges(svg, base.querySelector('svg'));
    }
    markText(svg, d.versions[i].marks || []);
  });
  if (svgs.length === 2) markChanges(svgs[0], svgs[1]);
  for (const svg of svgs) {
    const width = parseFloat(svg.style.maxWidth);
    if (!width) continue;
    const fig = svg.parentElement, outer = width * SCALE + FRAME;
    fig.style.width = `${outer}px`;
    fig.parentElement.style.minWidth = `min(100%, ${outer}px)`;
  }
  box.classList.add('md-mmd-on');
}

/* Szélességváltáskor (panel, ablak, side-by-side ↔ egymás alatt) a kirajzolt
   diagramok iránya újra: rajzolás nélkül, a meglévő két rajz közül. */
export function refitMermaid(root) {
  for (const box of root.querySelectorAll('.md-mmd-on')) place(box);
}

/* A diagram elemei a változatok összevetéséhez. Az azonosítós elemek (csomópont,
   él: `<render-id>-flowchart-A-0`, `-L_A_B_0`) kulcsa az azonosító a rajzolás
   előtagja és a sorszám nélkül (az egy új csomópont után eltolódik) — tartalma a
   felirata, a vonalé az osztálya is (a vonal fajtája). A többi felirat (élcímke,
   a szekvenciadiagram szövegei) szövegként. */
function parts(svg) {
  const pre = svg.id + '-', seen = new Map(), keyed = [];
  for (const el of svg.querySelectorAll('[id]')) {
    if (!el.id.startsWith(pre) || el.closest('defs, marker')) continue;
    const base = el.tagName + ':' + el.id.slice(pre.length).replace(/[-_]\d+$/, '');
    const n = seen.get(base) || 0;
    seen.set(base, n + 1);
    keyed.push({ el, key: `${base}#${n}`,
                 sig: el.textContent.trim() + (el.tagName === 'path' ? '|' + el.getAttribute('class') : '') });
  }
  const texts = [...svg.querySelectorAll('text, span.nodeLabel, span.edgeLabel')]
    .filter(el => el.textContent.trim() && !keyed.some(k => k.el.contains(el)));
  return { keyed, texts };
}

/* A változott szövegek (`marks`: a diff szó-kiemelései a forrásban, `{ text, node }`)
   a rajzon is kiemelve, és az elemük is színes. A forrás jelölése (idézőjel, zárójel,
   `<br/>`) a rajzon nincs: a darabok ezek nélkül, az első előfordulásuk — a
   csomópontjukban, ha ismert (flowchart), különben az egész rajzban. */
const SVG_NS = 'http://www.w3.org/2000/svg';
function markText(svg, marks) {
  const nodeEl = node => [...svg.querySelectorAll('[id]')]
    .find(el => el.id.startsWith(`${svg.id}-flowchart-${node}-`) && /^\d+$/.test(el.id.slice(`${svg.id}-flowchart-${node}-`.length)));
  const pieces = marks.flatMap(m => m.text.split(/<br\s*\/?>/i).map(text => ({ text, node: m.node })))
    .map(p => ({ ...p, text: p.text.replace(/^[\s"'[\](){}<>|]+|[\s"'[\](){}<>|]+$/g, '') })).filter(p => p.text);
  for (const { text: piece, node } of pieces) {
    const walker = document.createTreeWalker((node && nodeEl(node)) || svg, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const n = /** @type {Text} */ (walker.currentNode);
      const at = n.data.indexOf(piece);
      if (at < 0 || n.parentElement.closest('style, .md-mmd-hl')) continue;
      const svgText = n.parentElement.namespaceURI === SVG_NS;
      const hl = svgText ? document.createElementNS(SVG_NS, 'tspan') : document.createElement('mark');
      hl.setAttribute('class', 'md-mmd-hl');
      const range = document.createRange();
      range.setStart(n, at);
      range.setEnd(n, at + piece.length);
      range.surroundContents(hl);
      hl.closest('g.node, g.edgeLabel, g[id]')?.classList.add('md-mmd-ch');
      break;
    }
  }
}

/* A két változat eltérő elemei `md-mmd-ch` jelet kapnak: a régiben (piros) ami
   eltűnt vagy változott, az újban (zöld) ami új vagy változott. */
function markChanges(oldSvg, newSvg) {
  const a = parts(oldSvg), b = parts(newSvg);
  const mark = (xs, ys) => {
    const other = new Map(ys.keyed.map(k => [k.key, k.sig]));
    for (const k of xs.keyed) if (other.get(k.key) !== k.sig) k.el.classList.add('md-mmd-ch');
    const left = new Map();
    for (const el of ys.texts) left.set(el.textContent.trim(), (left.get(el.textContent.trim()) || 0) + 1);
    for (const el of xs.texts) {
      const t = el.textContent.trim();
      if (left.get(t)) left.set(t, left.get(t) - 1);
      else el.classList.add('md-mmd-ch');
    }
  };
  mark(a, b);
  mark(b, a);
}

/* A `root` diagramjai; utána a side-by-side sormagasságai (`syncRows`) újra. */
export function renderMermaid(root, get) {
  const boxes = [...root.querySelectorAll('.md-mmd')];
  if (!boxes.length) return Promise.resolve();
  queue = queue.then(() => load(get))
    .then(mermaid => draw(boxes, mermaid), e => boxes.forEach(box => fail(box, e)))
    .then(() => syncRows(root));
  return queue;
}

/* Témaváltáskor a kirajzolt diagramok újra, az új témával. */
function redraw() {
  if (!lib) return;
  const boxes = [...document.querySelectorAll('.md-mmd-on')];
  if (boxes.length) queue = queue.then(() => lib).then(mermaid => draw(boxes, mermaid)).catch(() => {});
}
new MutationObserver(redraw).observe(root, { attributes: true, attributeFilter: ['data-theme'] });
darkMedia.addEventListener('change', redraw);
