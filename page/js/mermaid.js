/* ── Mermaid-diagramok a markdown-diffben ──
   A `md-diff.js` a ```mermaid blokkot kódnézetként rajzolja, a kirajzolandó
   változatokkal (`.md-mmd[data-mmd]`); ez cseréli diagramra. A Mermaidot (3,6 MB,
   `page/vendor/`) csak az első diagramnál kéri a gépen futó git-graph-tól
   (`page_code` `part: 'mermaid'`), és blobból futtatja (az Artifact CSP-je
   engedi — mérve, docs/artifact-findings.md). A diagram a lap témáját követi:
   váltáskor újrarajzol. Ha a Mermaid nem tölthető be, vagy a diagram hibás, a
   kódnézet marad, alatta a hibával. */
import { syncRows } from './md-diff.js';
import { esc } from './util.js';

let lib = null;              // a Mermaid betöltésének ígérete; hibánál a következő próba újrakéri
let queue = Promise.resolve();   // a rajzolások sorban: a téma (`initialize`) közös
let seq = 0;

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

function fail(box, e) {
  box.classList.remove('md-mmd-on');
  box.querySelector('.md-mmd-view').innerHTML = `<p class="md-mmd-err">A diagram nem rajzolható ki: ${
    esc(String(e?.message || e?.code || e).trim())}</p>`;
}

async function draw(boxes, mermaid) {
  mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', suppressErrorRendering: true,
                       theme: dark() ? 'dark' : 'default' });
  for (const box of boxes) {
    if (!box.isConnected) continue;
    try {
      const figs = [];
      for (const v of JSON.parse(box.dataset.mmd)) {
        const id = `gg-mmd-${++seq}`;
        try {
          figs.push(`<div class="md-mmd-fig${v.kind}">${(await mermaid.render(id, v.src)).svg}</div>`);
        } finally {
          document.getElementById('d' + id)?.remove();     // a Mermaid ideiglenes eleme
        }
      }
      box.querySelector('.md-mmd-view').innerHTML = figs.join('');
      box.classList.add('md-mmd-on');
    } catch (e) {
      fail(box, e);
    }
  }
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
