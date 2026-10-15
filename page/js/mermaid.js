/* ── Mermaid-diagramok a markdown-diffben ──
   A `md-diff.js` a ```mermaid blokkot kódnézetként rajzolja, a kirajzolandó
   változatokkal (`.md-mmd[data-mmd]`); ez cseréli diagramra. A Mermaidot (karcsú
   build, 3,7 MB, `page/vendor/`) csak az első diagramnál kéri a gépen futó
   git-graph-tól (`page_code` `part: 'mermaid'`), és blobból futtatja (az Artifact
   CSP-je engedi — mérve, docs/artifact-findings.md). A rajz a lap palettáján
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

/* A Mermaid `base` témája a lap palettáján (page.css): a csomópont a háttérnél
   világosabb (sötétben sötétebb), a keret és a vonal halk. A `base` téma a
   színekből számol, ezért itt tömör hex áll, nem a lap áttetsző `--border`-e. */
const PALETTE = {
  light: { background: '#faf9f5', mainBkg: '#ffffff', primaryColor: '#ffffff', primaryTextColor: '#141413',
           primaryBorderColor: '#c9c6ba', secondaryColor: '#f5f4ed', tertiaryColor: '#efede4',
           lineColor: '#9c9a92', textColor: '#3d3d3a', clusterBkg: '#f5f4ed', clusterBorder: '#dedbd0',
           edgeLabelBackground: '#faf9f5', nodeTextColor: '#141413',
           actorBkg: '#ffffff', actorBorder: '#c9c6ba', actorTextColor: '#141413', signalColor: '#6b6a64',
           signalTextColor: '#3d3d3a', labelBoxBkgColor: '#f5f4ed', labelBoxBorderColor: '#dedbd0',
           loopTextColor: '#6b6a64', activationBkgColor: '#efede4', noteBkgColor: '#f5f4ed' },
  dark: { darkMode: true, background: '#1f1e1d', mainBkg: '#2d2c2a', primaryColor: '#2d2c2a', primaryTextColor: '#faf9f5',
          primaryBorderColor: '#57554f', secondaryColor: '#383734', tertiaryColor: '#262624',
          lineColor: '#7f7d76', textColor: '#e3e1d8', clusterBkg: '#262624', clusterBorder: '#3f3e3a',
          edgeLabelBackground: '#1f1e1d', nodeTextColor: '#faf9f5',
          actorBkg: '#2d2c2a', actorBorder: '#57554f', actorTextColor: '#faf9f5', signalColor: '#a8a69d',
          signalTextColor: '#e3e1d8', labelBoxBkgColor: '#262624', labelBoxBorderColor: '#3f3e3a',
          loopTextColor: '#a8a69d', activationBkgColor: '#383734', noteBkgColor: '#383734' },
};
const themeVariables = () => ({ ...PALETTE[dark() ? 'dark' : 'light'],
                                fontFamily: getComputedStyle(root).getPropertyValue('--font-ui').trim() });

function fail(box, e) {
  box.classList.remove('md-mmd-on');
  box.querySelector('.md-mmd-view').innerHTML = `<p class="md-mmd-err">A diagram nem rajzolható ki: ${
    esc(String(e?.message || e?.code || e).trim())}</p>`;
}

async function draw(boxes, mermaid) {
  mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', suppressErrorRendering: true,
                       theme: 'base', themeVariables: themeVariables(), look: 'neo' });
  for (const box of boxes) {
    if (!box.isConnected) continue;
    try {
      const versions = JSON.parse(box.dataset.mmd), figs = [], bases = [];
      const svgOf = async src => {
        const id = `gg-mmd-${++seq}`;
        try {
          return (await mermaid.render(id, src)).svg;
        } finally {
          document.getElementById('d' + id)?.remove();     // a Mermaid ideiglenes eleme
        }
      };
      for (const v of versions) {
        const kind = (v.kind ? ` md-mmd-${v.kind.trim()}` : '') + (v.whole ? ' md-mmd-whole' : '');
        figs.push(`<div class="md-mmd-half"><div class="md-mmd-fig${kind}">${await svgOf(v.src)}</div></div>`);
        // az egyetlen változat összevetési alapja: csak a változott elemek kereséséhez, nem látszik
        const base = document.createElement('div');
        if (v.base?.trim()) base.innerHTML = await svgOf(v.base);
        bases.push(base.querySelector('svg'));
      }
      const view = box.querySelector('.md-mmd-view');
      view.innerHTML = figs.join('');
      const svgs = [...view.querySelectorAll('.md-mmd-fig > svg')];
      svgs.forEach((svg, i) => {
        if (bases[i]) markChanges(svg, bases[i]);
        markText(svg, versions[i].marks || []);
      });
      if (svgs.length === 2) markChanges(svgs[0], svgs[1]);
      // A keret a diagram (kicsinyített) szélességét kapja, a fele legalább ekkora: két
      // változat így egymás mellé kerül, ha elfér, különben egymás alá.
      for (const svg of svgs) {
        const width = parseFloat(svg.style.maxWidth);
        if (!width) continue;
        const fig = svg.parentElement, outer = width * SCALE + FRAME;
        fig.style.width = `${outer}px`;
        fig.parentElement.style.minWidth = `min(100%, ${outer}px)`;
      }
      box.classList.add('md-mmd-on');
    } catch (e) {
      fail(box, e);
    }
  }
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

/* A változott szövegek (`marks`: a diff szó-kiemelései a forrásban) a rajzon is
   kiemelve, és az elemük is színes. A forrás jelölése (idézőjel, zárójel,
   `<br/>`) a rajzon nincs: a darabok ezek nélkül, az első előfordulásuk. */
const SVG_NS = 'http://www.w3.org/2000/svg';
function markText(svg, marks) {
  const pieces = marks.flatMap(m => m.split(/<br\s*\/?>/i))
    .map(p => p.replace(/^[\s"'[\](){}<>|]+|[\s"'[\](){}<>|]+$/g, '')).filter(Boolean);
  for (const piece of pieces) {
    const walker = document.createTreeWalker(svg, NodeFilter.SHOW_TEXT);
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
