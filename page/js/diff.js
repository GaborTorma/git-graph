/* ── Fájl-diff ───────────────────────────────────────────────────────────────
   A diffet a lap lustán kéri, fájlonként (a file_diff toollal) —
   a teljes adatban nincs benne. A commitok diffje nem változik, gyorstárazzuk;
   az Uncommitted soré adatcserekor elavul (`stale`): a régi látszik, amíg az
   új meg nem jön, így a 2 mp-es frissítés nem villog. */
import { grow, shrink } from './anim.js';
import { diffHtml } from './diff-html.js';
import { drawGraph } from './graph.js';
import { icon } from './icons.js';
import { IMAGE_RE, fitImages, imageDiffHtml, loadImages } from './images.js';
import { mdDiffHtml, syncRows } from './md-diff.js';
import { refitMermaid, renderMermaid } from './mermaid.js';
import { revealCommit, revealFile } from './panel.js';
import { expanded } from './state.js';
import { langOf } from './syntax.js';
import { esc } from './util.js';

/* A markdown side-by-side sormagasságai (`syncRows`) a szélességtől függnek:
   dobozonként egy méretfigyelő, csak szélességváltozásra (a magasságot a
   szinkron maga is változtatja). A gráfot a sorok figyelője rajzolja újra. */
const watched = new WeakSet();
function watchWidth(box) {
  if (watched.has(box)) return;
  watched.add(box);
  let width = box.clientWidth;
  new ResizeObserver(() => {
    if (box.clientWidth !== width) { width = box.clientWidth; refitMermaid(box); fitImages(box); syncRows(box); }
  }).observe(box);
}

export const openFiles = new Set();   // sha + '\n' + út
export const diffCache = new Map();   // ugyanígy kulcsolva → { data, stale }
let SRC = null;                // az élő adatforrás (startLive állítja); az appon kívül nincs
export const setSource = src => { SRC = src; };

/* `reveal`: a megnőtt panelt a nézetbe hozza — `true`: a commitot és a
   fájlt (felhasználói nyitás), `'commit'`: csak a commitot, `false`: semmit. */
/** @param {boolean | 'commit'} [reveal] */
export function toggleFile(fileEl, sha, on, reveal = true) {
  const key = sha + '\n' + fileEl.dataset.path;
  const box = fileEl.nextElementSibling;
  fileEl.setAttribute('aria-expanded', on ? 'true' : 'false');
  if (!on) {
    openFiles.delete(key);
    shrink(box, () => { box.hidden = true; drawGraph(); revealCommit(fileEl.closest('.details'), true); });
    return;
  }
  openFiles.add(key);

  const lang = langOf(fileEl.dataset.path);
  // Felhasználói nyitásnál a diff (és vele a panel) animálva nő; a nézetbe
  // hozás a végső méretből számol.
  const show = html => {
    if (!fileEl.isConnected || fileEl.getAttribute('aria-expanded') !== 'true') return;
    const fill = () => {
      box.hidden = false;
      box.innerHTML = html;
      syncRows(box);
      watchWidth(box);
      renderMermaid(box, () => SRC.mermaid());
      loadImages(box, ref => image(sha, fileEl.dataset.path, ref), () => syncRows(box));
      fitImages(box);
    };
    const settle = () => {
      if (reveal) revealCommit(fileEl.closest('.details'), true);
      if (reveal === true) revealFile(fileEl);
    };
    if (reveal === true) { grow(box, fill, settle); return; }
    fill();
    settle();
    drawGraph();
  };
  // Markdown-fájl: renderelve a teljes fájlból (`full`, külön gyorstárazva), a
  // kapcsolóval nyersen — a kapcsoló mindkét nézet fölött ott van. Képfájl: a két
  // oldal képe (`images.js`); az SVG-é a kapcsolóval a szöveges diff.
  const md = lang === 'md', full = md && !mdRaw, svg = /\.svg$/i.test(fileEl.dataset.path);
  const cacheKey = full ? key + '\nfull' : key;
  const render = d => (md ? mdModeHtml() : '') + (d.image && svg ? svgModeHtml() : '') + (full ? mdDiffHtml(d)
    : d.image && !(svg && svgCode) ? imageDiffHtml(d, fileEl.dataset.path) : diffHtml(d, lang));
  const cached = diffCache.get(cacheKey);
  if (!SRC) return show('<p class="diff-note">A diff csak élő nézetben látszik '
    + '(az Artifact a Claude appban).</p>');
  show(cached ? render(cached.data) : '<p class="diff-note loading">Betöltés…</p>');
  if (cached && !cached.stale) return;
  SRC.diff(sha, fileEl.dataset.path, full).then(d => withImages(d, sha, fileEl.dataset.path)).then(
    d => {
      // Élő frissítéskor a régi adat már kirajzolva: ha nem változott, nem rajzoljuk újra.
      const same = cached && JSON.stringify(cached.data) === JSON.stringify(d);
      diffCache.set(cacheKey, { data: d });
      if (!same && full === (md && !mdRaw)) show(render(d));   // közben átváltott: a másik nézet a soros
    },
    e => { if (!cached) show(`<p class="diff-note">A diff nem tölthető be: ${esc(
      e?.message || e?.code || e)}</p>`); });
}

/* A kép két oldala oldalanként külön hívással (`file_diff` `side`): egy válasz így a host-híd
   határa alatt marad. `ref`: a markdown-fájl egy képe. `known`: a diffből ismert oldalak
   (a mérettel) — a hiányzót nem kérjük, és ha egy oldal hívása elbukik, a mérete marad (a
   lap „Túl nagy kép”-et mutat), a diff nem vész el. */
const sides = (sha, path, ref = null, known = null) => Promise.all(['old', 'new'].map(s =>
  known && !known[s] ? null : SRC.side(sha, path, s, ref).catch(e => { if (known) return known[s]; throw e; })))
  .then(([old, now]) => ({ old, new: now }));

/* A képfájl diffje a két oldal méretét adja: a képeket külön kérjük, és a diffbe tesszük. */
const withImages = (d, sha, path) => d.image ? sides(sha, path, null, d.image).then(image => ({ ...d, image })) : d;

/* A markdown-fájl egy képének két oldala, a diffekkel együtt gyorstárazva: az Uncommitted
   soré ugyanúgy elavul. */
function image(sha, path, ref) {
  const key = sha + '\n' + path + '\nimg\n' + ref, cached = diffCache.get(key);
  if (cached && !cached.stale) return Promise.resolve(cached.data);
  return sides(sha, path, ref).then(d => { diffCache.set(key, { data: d }); return d; },
    e => { if (cached) return cached.data; throw e; });
}

const MD_RAW_KEY = 'git-graph:mdRaw';
export let mdRaw = (() => { try { return localStorage.getItem(MD_RAW_KEY) === '1'; } catch { return false; } })();

export function setMdRaw(raw) {
  mdRaw = raw;
  try { localStorage.setItem(MD_RAW_KEY, raw ? '1' : '0'); } catch { /* privát ablak: nem baj */ }
  document.querySelectorAll('.details .file[aria-expanded="true"]').forEach(f => {
    if (langOf(f.dataset.path) === 'md') toggleFile(f, expanded, true, 'commit');
  });
}

/* A nézetváltó: kétgombos szegmens (`[érték, ikon, felirat]`), a választott a lenyomott. */
const segHtml = (attr, on, ...opts) => `<span class="md-seg" role="group">${opts.map(([value, name, label]) =>
  `<button type="button" data-${attr}="${value}" aria-pressed="${value === on}" aria-label="${label}" data-tip="${label}">`
  + `${icon(name)}</button>`).join('')}</span>`;
const mdModeHtml = () => segHtml('md-mode', mdRaw ? 'raw' : 'rendered',
  ['rendered', 'text', 'Renderelt nézet'], ['raw', 'code', 'Nyers diff']);

/* Az SVG-fájl: alapból kép, a kapcsolóval a kódja (a szöveges diff); a lap megjegyzi. */
const SVG_CODE_KEY = 'git-graph:svgCode';
export let svgCode = (() => { try { return localStorage.getItem(SVG_CODE_KEY) === '1'; } catch { return false; } })();

export function setSvgCode(code) {
  svgCode = code;
  try { localStorage.setItem(SVG_CODE_KEY, code ? '1' : '0'); } catch { /* privát ablak: nem baj */ }
  document.querySelectorAll('.details .file[aria-expanded="true"]').forEach(f => {
    if (IMAGE_RE.test(f.dataset.path) && /\.svg$/i.test(f.dataset.path)) toggleFile(f, expanded, true, 'commit');
  });
}

const svgModeHtml = () => segHtml('svg-mode', svgCode ? 'code' : 'image', ['image', 'image', 'Kép'], ['code', 'code', 'Kód']);
