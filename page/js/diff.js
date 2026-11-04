/* ── Fájl-diff ───────────────────────────────────────────────────────────────
   A diffet a lap lustán kéri, fájlonként (a file_diff toollal) —
   a teljes adatban nincs benne. A commitok diffje nem változik, gyorstárazzuk;
   az Uncommitted soré adatcserekor elavul (`stale`): a régi látszik, amíg az
   új meg nem jön, így a 2 mp-es frissítés nem villog. A kódfájlt a CodeMirror
   rajzolja (`cm.js`), a markdownt renderelve az `md-diff.js`, a képet az `images.js`. */
import { cardState, closeCard, grow, openCard } from './anim.js';
import { CodeDiff, cmLang, fromHunks, loadCM } from './cm.js';
import { drawGraph } from './graph.js';
import { icon } from './icons.js';
import { IMAGE_RE, fitImages, imageDiffHtml, loadImages } from './images.js';
import { mdDiffHtml, openGaps, syncRows } from './md-diff.js';
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
/* A kódfájlok CodeMirror-nézetei (`CodeDiff`), kulcsonként: a panel újrarajzolásakor a nézet
   (és vele a szerkesztés) átköltözik az új dobozba, nem épül újra. A teljes nézeté `fv\n`-nel. */
export const codeViews = new Map();
let SRC = null;                // az élő adatforrás (startLive állítja); az appon kívül nincs
export const setSource = src => { SRC = src; };
export const source = () => SRC;

/* Egy fájl nézete megszűnik (a fájl vagy a commit becsukódott): a függő mentés lefut. */
export function forgetFile(key) {
  openFiles.delete(key);
  const view = codeViews.get(key);
  if (!view) return;
  view.stopEditing();
  codeViews.delete(key);
  view.dispose();
}

/* `reveal`: a megnőtt panelt a nézetbe hozza — `true`: a commitot és a
   fájlt (felhasználói nyitás), `'commit'`: csak a commitot, `false`: semmit. */
/** @param {boolean | 'commit'} [reveal] */
export function toggleFile(fileEl, sha, on, reveal = true) {
  const key = sha + '\n' + fileEl.dataset.path;
  const box = fileEl.nextElementSibling;
  const before = cardState(fileEl);   // a fájlsor a hoveréből nyílik, a keretéből csukódik
  fileEl.setAttribute('aria-expanded', on ? 'true' : 'false');
  if (!on) {
    forgetFile(key);
    closeCard(fileEl, box, before, () => { box.hidden = true; drawGraph(); revealCommit(fileEl.closest('.details'), true); });
    return;
  }
  openFiles.add(key);

  // Felhasználói nyitásnál a diff (és vele a panel) animálva nő; a nézetbe
  // hozás a végső méretből számol.
  let opened = false;
  const paint = fill => {
    if (!fileEl.isConnected || fileEl.getAttribute('aria-expanded') !== 'true') return;
    const settle = () => {
      if (reveal) revealCommit(fileEl.closest('.details'), true);
      if (reveal === true) revealFile(fileEl);
    };
    const show = () => { box.hidden = false; fill(); };
    // Az első tartalom (a „Betöltés…” is) nyitja a kártyát; a később érkező csak a magasságát
    // viszi tovább onnan, ahol tart — a kártya animációja nem indul újra.
    if (reveal === true) {
      if (opened) grow(box, show, settle); else openCard(fileEl, box, before, show, settle);
      opened = true;
      return;
    }
    show();
    settle();
    drawGraph();
  };
  fileContent(box, sha, fileEl.dataset.path, key, paint);
}

/* Egy fájl tartalma a `box`-ba: markdown (renderelve, a kapcsolóval nyersen), kép (a két oldala;
   az SVG-é a kapcsolóval a kódja), a többi a CodeMirror-diff. `paint(fill)` rajzol: a `fill`
   cseréli a doboz tartalmát (a hívó animálhat körülötte). `o.changed`: a fájl a sor
   változásai között van-e (a teljes nézet fájájának változatlan fájlja: a tartalma, színezve);
   `o.ready(view)`: a kódnézet kész (a teljes nézet ide görget). */
export function fileContent(box, sha, path, key, paint, o = {}) {
  const lang = langOf(path), changed = o.changed ?? true;
  const md = lang === 'md' && changed, full = md && !mdRaw, svg = /\.svg$/i.test(path);
  const html = h => paint(() => {
    box.innerHTML = h;
    syncRows(box);
    watchWidth(box);
    renderMermaid(box, () => SRC.mermaid());
    box.loadPics = () => loadImages(box, ref => image(sha, path, ref), () => syncRows(box));
    box.loadPics();
    fitImages(box);
  });
  if (!SRC) { html('<p class="diff-note">A diff csak élő nézetben látszik (az Artifact a Claude appban).</p>'); return; }
  const modes = (md ? mdModeHtml() : '');
  const pic = IMAGE_RE.test(path) && !(svg && svgCode);
  if (full || pic) {
    const cacheKey = full ? key + '\nfull' : key;
    const render = d => modes + (d.image && svg ? svgModeHtml() : '') + (full ? mdDiffHtml(d) : imageDiffHtml(d, path));
    const cached = diffCache.get(cacheKey);
    html(cached ? render(cached.data) : '<p class="diff-note loading">Betöltés…</p>');
    if (cached && !cached.stale) return;
    SRC.diff(sha, path, full).then(d => withImages(d, sha, path)).then(
      d => {
        // Élő frissítéskor a régi adat már kirajzolva: ha nem változott, nem rajzoljuk újra.
        const same = cached && JSON.stringify(cached.data) === JSON.stringify(d);
        diffCache.set(cacheKey, { data: d });
        if (!same && full === (md && !mdRaw)) html(render(d));   // közben átváltott: a másik nézet a soros
      },
      e => { if (!cached) html(`<p class="diff-note">A diff nem tölthető be: ${esc(e?.message || e?.code || e)}</p>`); });
    return;
  }
  // Kódnézet: a CodeMirror-diff a két oldal teljes szövegéből (2 MB fölött a csonkolt hunkokból).
  const prefix = modes + (svg ? svgModeHtml() : '');
  const place = view => paint(() => {
    if (view.root.parentElement === box) { o.ready?.(view); return; }   // már itt van: a görgetés, a fókusz marad
    box.innerHTML = prefix;
    box.append(view.root);
    if (view.big) box.insertAdjacentHTML('beforeend', '<p class="diff-note">… a diff túl hosszú, a vége le van vágva.</p>');
    view.layout();
    if (view.editing) view.ed?.focus();
    o.ready?.(view);
  });
  const note = h => html(prefix + h);
  const textKey = key + '\ntext';    // a kép diffje ugyanerre az útra (SVG) külön gyorstárban
  const cached = diffCache.get(textKey), live = codeViews.get(key);
  if (live) place(live);
  else note('<p class="diff-note loading">Betöltés…</p>');
  const shown = d => {
    if (d.binary) { codeViews.delete(key); note('<p class="diff-note">Bináris fájl.</p>'); return; }
    // a teljes képernyőn megtartott fájl egy olyan commitban, ahol (még / már) nincs meg
    if (d.old == null && d.new == null && !d.big) { codeViews.delete(key); note('<p class="diff-note">A fájl ebben a commitban nincs meg.</p>'); return; }
    // a nézet egy korábbi (azóta újrarajzolt) panelhez épülhetett: ide költözik
    const reuse = view => { view.update(d); if (view.root.parentElement !== box) place(view); };
    const view = codeViews.get(key);
    if (view) { reuse(view); return; }
    loadCM(() => SRC.codemirror()).then(CM => {
      const known = codeViews.get(key);
      if (known) { reuse(known); return; }
      const fresh = new CodeDiff(CM, d, { lang: cmLang(path), write: (text, base, row) => SRC.write(row ?? sha, path, text, base) });
      codeViews.set(key, fresh);
      place(fresh);
    }, e => note(`<p class="diff-note">A kódnézet nem tölthető be: ${esc(e?.message || e?.code || e)}</p>`));
  };
  if (cached && !cached.stale) { if (!live) shown(cached.data); return; }
  codeText(sha, path).then(d => {
    const same = cached && JSON.stringify(cached.data) === JSON.stringify(d);
    diffCache.set(textKey, { data: d });
    if (!same || !codeViews.get(key)) shown(d);
  }, e => { if (!cached && !live) note(`<p class="diff-note">A diff nem tölthető be: ${esc(e?.message || e?.code || e)}</p>`); });
}

/* A kódnézet adata: a két (WIP-réteggel három) oldal teljes szövege, a fejadattal egy hívásban, ha együtt
   átfér a host-híd határán, különben oldalanként; 2 MB fölött a csonkolt hunkok. */
async function codeText(sha, path) {
  const meta = await SRC.text(sha, path);
  if (meta.binary) return { binary: true };
  if (meta.big) return fromHunks(meta);
  // a worktree HEAD-commitja (`wip`): a dokumentum a lemez szövege, a HEAD-beli a WIP-rétegnek
  // az oldalak a fejadattal jönnek, ha együtt átférnek a host-hídon (egy hívás); különben oldalanként
  const [old, now, disk] = meta.sides ? [meta.sides.old, meta.sides.new, meta.sides.disk]
    : await Promise.all(['old', 'new', ...(meta.wip ? ['disk'] : [])].map(s => SRC.textSide(sha, path, s)));
  if (old.binary || now.binary || disk?.binary) return { binary: true };
  if (old.big || now.big || disk?.big) return fromHunks(await SRC.diff(sha, path, false));
  if (disk && disk.text != null) {
    return { old: old.text, new: disk.text, head: now.text ?? '', hash: disk.hash ?? meta.hash ?? null,
             editable: Boolean(meta.editable), write: meta.write ?? null };
  }
  // a HEAD-commit tiszta fájlja: a mentés sora (`write`, az Uncommitted sor) és a lemez hashe a fejadatból
  return { old: old.text, new: now.text, hash: now.hash ?? meta.hash ?? null, editable: Boolean(meta.editable),
           write: meta.write ?? null };
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

/* A markdown változatlan rése egy kattintásra egyben nyílik (mindkét nézetben). */
document.addEventListener('click', e => {
  const gap = /** @type {HTMLElement} */ (e.target).closest?.('[data-gap]');
  if (!gap) return;
  const box = openGaps(/** @type {HTMLElement} */ (gap));
  renderMermaid(box, () => SRC.mermaid());   // a kinyílt blokkok diagramjai és képei
  box.loadPics?.();
  fitImages(box);
});

const MD_RAW_KEY = 'git-graph:mdRaw';
export let mdRaw = (() => { try { return localStorage.getItem(MD_RAW_KEY) === '1'; } catch { return false; } })();

/* `rerender`: a teljes nézet is újrarajzolja a saját fájlját (`full.js`). */
let rerender = () => {};
export const onModeChange = fn => { rerender = fn; };

export function setMdRaw(raw) {
  mdRaw = raw;
  try { localStorage.setItem(MD_RAW_KEY, raw ? '1' : '0'); } catch { /* privát ablak: nem baj */ }
  document.querySelectorAll('.details .file[aria-expanded="true"]').forEach(f => {
    if (langOf(f.dataset.path) === 'md') toggleFile(f, expanded, true, 'commit');
  });
  rerender();
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
  rerender();
}

const svgModeHtml = () => segHtml('svg-mode', svgCode ? 'code' : 'image', ['image', 'image', 'Kép'], ['code', 'code', 'Kód']);
