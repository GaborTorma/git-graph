/* ── Fájlfa: sidebar és teljes képernyő ──
   A sidebar az eszközsor gombjával nyílik (a lap megjegyzi): a gráf mellett, jobbra a fájlfa, az
   eszközsor és a lábléc között. A fa a lenyitott commitot követi (a változásai szerint színezve);
   lenyitott commit nélkül a saját worktree mostani állapotát mutatja (a WIP sor, tisztán a HEAD,
   minden fájllal). A fában a lenyitott commit változott fájlja a commit-panelben nyílik le, odagörgetve;
   a többi fájl (változatlan, vagy nincs lenyitott commit) teljes képernyőn.
   A teljes képernyő a panel lenyitott fájljának fejlécéből nyílik (`data-full`), a fájl első
   változásánál: a keret a láblécig, fent a subject és az X, középen a fájl
   diffje (`fileContent`: a CodeMirror, a markdown, a kép), jobbra a saját fája. A HEAD-commit tiszta
   fájlja is szerkeszthető: az első mentéstől a fájl a WIP soré, a nézet átvált rá; Esc-re bezárul, és
   a panelben a kijelölt fájl lenyitva, odagörgetve marad. A nézet billentyűit a réteg elkapja.
   A diff-szűrő bekapcsolva a sor változott fájljait mutatja (a mappaláncok összevonva), kikapcsolva
   a commit állapotának minden fájlját (`file_tree`; 20 000 fájl fölött mappánként, lustán); a tiszta
   worktree HEAD-jén letiltva, minden fájllal. A kereső név szerint szűr, `?` előtaggal a tartalomban
   keres (`git grep`). A fa szélessége húzható (legalább 200 px), a lap megjegyzi; a lábléc közepén a
   nézett fájl útja áll. */
import { editingDiff } from './cm.js';
import { codeViews, fileContent, forgetFile, onModeChange, mdRaw, setMdRaw, setSvgCode, source, svgCode, toggleFile } from './diff.js';
import { OPEN_PANEL, counter } from './dom.js';
import { fileIcon, icon } from './icons.js';
import { commitBySha, focusWt } from './model.js';
import { revealFile } from './panel.js';
import { DATA, expanded, onExpanded } from './state.js';
import { esc, fold } from './util.js';

const WIDTH_KEY = 'git-graph:treeWidth';
const SIDE_KEY = 'git-graph:sidebar';
const WIDTH0 = 280, WIDTH_MIN = 200;
const GREP_MS = 250;           // a tartalomkeresés ennyi csend után indul

/** @type {any} */
let fv = null;                 // a teljes képernyő (a fája is)
/** @type {any} */
let side = null;               // a sidebar fája

/* A sidebar az eszközsor alatt kezdődik, mindkettő a lábléc fölött ér véget: a határok és a fa
   szélessége CSS-változóban (a gráf a sidebar szélességével keskenyebb). */
const root = document.documentElement;
const foot = /** @type {HTMLElement} */ (document.getElementById('foot'));
const chrome = /** @type {HTMLElement} */ (document.querySelector('.chrome'));
const footPath = /** @type {HTMLElement} */ (document.getElementById('footPath'));
new ResizeObserver(() => root.style.setProperty('--foot-h', `${foot.offsetHeight}px`)).observe(foot);
new ResizeObserver(() => root.style.setProperty('--chrome-h', `${chrome.getBoundingClientRect().bottom}px`)).observe(chrome);
const setTreeWidth = w => root.style.setProperty('--fv-tree-w', `${Math.round(w)}px`);
const savedWidth = () => {
  try { return Math.max(WIDTH_MIN, Number(localStorage.getItem(WIDTH_KEY)) || WIDTH0); } catch { return WIDTH0; }
};
setTreeWidth(savedWidth());

/* A lábléc közepe: a nézett fájl útja (a worktree gyökeréhez képest), különben a commitszám. */
function showPath(path) {
  footPath.innerHTML = path ? `<bdi>${esc(path)}</bdi>` : '';   // az rtl-vágás ne fordítsa meg az utat
  footPath.hidden = !path;
  counter.hidden = Boolean(path);
}

/* A `--numstat` átnevezése (`a => b`, `dir/{a => b}/x`): az új út. */
const newPath = p => (p.includes(' => ')
  ? p.replace(/\{([^{}]*) => ([^{}]*)\}/, '$2').replace(/^.* => /, '').replace(/\/{2,}/g, '/') : p);

/* A sor változott fájljai: út → bejegyzés (a commit-panel adatai: ikon, +/−, állapot). */
function changedFiles(sha) {
  const out = new Map();
  for (const f of DATA.stats[sha]?.files || []) {
    const path = newPath(f.path);
    out.set(path, { ...f, path, changed: true });
  }
  return out;
}

/* ── A fa ── egy példány (`t`): { sha, el, path, all, clean, tree, loaded, query, grep, opened, closed }. */
const treeHtml = (all, clean) => '<div class="fv-tree"><div class="fv-tools">'
  + `<label class="search fv-search">${icon('search')}<input type="search" placeholder="Szűrés név szerint · ?tartalom"`
  + ' aria-label="Fájlok szűrése" spellcheck="false"></label>'
  + `<button type="button" class="mini fv-diff" aria-pressed="${!all}"${clean ? ' disabled' : ''}`
  + ` aria-label="Csak a változott fájlok" data-tip="Csak a változott fájlok">${icon('changes')}</button>`
  + '</div><div class="fv-list"></div></div>';

const newTree = (el, sha, all, clean = false) => ({ el, sha, all, clean, path: null, tree: null, loaded: new Set(), query: '', grep: null,
  opened: new Set(), closed: new Set() });

/* A fa bejegyzései: a változott fájlok, a kapcsolóval a commit minden fájlja (a törölt is, a
   helyén), kereséskor a találatok. */
function entries(t) {
  const changed = changedFiles(t.sha);
  if (t.grep) return t.grep.map(f => changed.get(f.path) || { ...f, changed: false });
  let list = [...changed.values()];
  if (t.all && t.tree) {
    const seen = new Set(list.map(f => f.path));
    list = list.concat(t.tree.files.filter(f => !seen.has(f.path)).map(f => ({ ...f, changed: false })));
  }
  const q = t.query && !t.query.startsWith('?') ? fold(t.query) : '';
  return q ? list.filter(f => fold(f.path.split('/').pop()).includes(q)) : list;
}

/* A mappafa: { path, name, dirs, files, st (a változott fájlok állapotai), lazy }; az egyetlen
   almappájú, fájl nélküli mappák lánca egy sor („page/js”). */
function buildTree(t, list) {
  const top = { path: '', name: '', dirs: new Map(), files: [], st: new Set(), lazy: false };
  const dirOf = path => {
    let node = top;
    for (const part of path.split('/')) {
      const at = node.path ? `${node.path}/${part}` : part;
      if (!node.dirs.has(part)) node.dirs.set(part, { path: at, name: part, dirs: new Map(), files: [], st: new Set(), lazy: false });
      node = node.dirs.get(part);
    }
    return node;
  };
  for (const f of list) {
    if (f.count) { const d = dirOf(f.path.replace(/\/$/, '')); d.count = f.count; d.untracked = true; continue; }
    const i = f.path.lastIndexOf('/');
    (i < 0 ? top : dirOf(f.path.slice(0, i))).files.push(f);
  }
  if (t.all && t.tree?.lazy && !t.grep && !t.query) {
    for (const d of t.tree.dirs) { const node = dirOf(d); node.lazy = !t.loaded.has(d); }
  }
  const status = f => (f.status === 'A' || f.status === 'D' ? f.status : 'M');
  const mark = node => {
    for (const d of node.dirs.values()) { mark(d); d.st.forEach(s => node.st.add(s)); }
    for (const f of node.files) if (f.changed) node.st.add(status(f));
    if (node.untracked) node.st.add('A');
  };
  mark(top);
  const compact = node => {
    for (const [k, d] of [...node.dirs]) {
      let c = d;
      while (c.dirs.size === 1 && !c.files.length && !c.lazy && !c.count) {
        const [g] = c.dirs.values();
        c = { ...g, name: `${c.name}/${g.name}` };
      }
      node.dirs.set(k, c);
      compact(c);
    }
  };
  compact(top);
  return top;
}

/* Nyitva-e a mappa: kereséskor mind; alapnézetben mind, amit a Fejlesztő nem csukott be; a
   minden fájl nézetben csak a változott fájlok mappái és amit kinyitott. */
const isOpen = (t, d) => (t.query ? true : t.all ? t.opened.has(d.path) || (d.st.size > 0 && !t.closed.has(d.path))
  : !t.closed.has(d.path));

const ST_CLASS = { A: ' added', D: ' deleted', M: ' modified' };
const stClass = st => (!st.size ? '' : st.size === 1 ? ST_CLASS[[...st][0]] : ' modified');

function churn(f) {
  if (!f.changed || f.bin || f.count) return '';
  return `<span class="churn">${f.add ? `<span class="a">+${f.add}</span>` : ''}${f.del ? `<span class="d">−${f.del}</span>` : ''}</span>`;
}

function rowsHtml(t, node, depth) {
  const byName = (a, b) => a.name.localeCompare(b.name);
  let out = '';
  for (const d of [...node.dirs.values()].sort(byName)) {
    const open = isOpen(t, d) && !d.count;
    const inside = !open && t.path?.startsWith(`${d.path}/`);
    out += `<div class="fv-row fv-dir${stClass(d.st)}${inside ? ' sel-in' : ''}" data-dir="${esc(d.path)}" style="--depth:${depth}"`
      + ` aria-expanded="${open}"><span class="chev">${d.count ? '' : icon('chev')}</span>${icon('folder', 'ic fic')}`
      + `<span class="name">${esc(d.name)}</span>${d.count ? `<span class="churn"><span class="tag">${d.count} fájl</span></span>` : ''}</div>`;
    if (open) out += rowsHtml(t, d, depth + 1);
  }
  for (const f of node.files.map(x => ({ ...x, name: x.path.split('/').pop() })).sort(byName)) {
    const st = f.changed ? ST_CLASS[f.status === 'A' || f.status === 'D' ? f.status : 'M'] : '';
    out += `<div class="fv-row fv-file${st}${f.path === t.path ? ' sel' : ''}" data-path="${esc(f.path)}" style="--depth:${depth}"`
      + ` aria-selected="${f.path === t.path}"><span class="chev"></span>${fileIcon(f)}<span class="name">${esc(f.name)}</span>${churn(f)}</div>`;
  }
  return out;
}

function renderTree(t) {
  if (!t) return;
  const list = t.el.querySelector('.fv-list');
  const top = list.scrollTop;
  list.innerHTML = rowsHtml(t, buildTree(t, entries(t)), 0) || `<p class="fv-empty">${t.grep ? 'Nincs találat.' : 'Nincs ilyen fájl.'}</p>`;
  list.scrollTop = top;
}

const current = t => t === fv || t === side;

function loadTree(t) {
  const sha = t.sha;
  source()?.tree(sha).then(r => {
    if (!current(t) || t.sha !== sha) return;
    t.tree = { ...r, files: r.files || [], dirs: r.dirs || [] };
    if (r.fileIcons) Object.assign(DATA.fileIcons, r.fileIcons);
    t.loaded = new Set();
    renderTree(t);
  }, e => {
    if (!current(t) || t.sha !== sha) return;
    t.el.querySelector('.fv-list').insertAdjacentHTML('afterbegin',
      `<p class="fv-empty fv-error">A fájllista nem tölthető be: ${esc(e?.message || e?.code || e)}</p>`);
  });
}

/* Lusta mappa (20 000 fájl fölött): a tartalma kinyitáskor. */
function loadDir(t, dir) {
  const sha = t.sha;
  source()?.tree(sha, { dir }).then(r => {
    if (!current(t) || t.sha !== sha) return;
    if (r.fileIcons) Object.assign(DATA.fileIcons, r.fileIcons);
    t.tree.files = t.tree.files.concat(r.files || []);
    t.tree.dirs = [...new Set([...t.tree.dirs, ...(r.dirs || [])])];
    t.loaded.add(dir);
    renderTree(t);
  }, () => {             // nem jött: a mappa csukva marad, a következő kinyitás újra kéri
    if (!current(t) || t.sha !== sha) return;
    t.opened.delete(dir);
    renderTree(t);
  });
}

let grepTimer = 0;
function onQuery(t, value) {
  t.query = value.trim();
  clearTimeout(grepTimer);
  if (!t.query.startsWith('?') || t.query.length < 2) { t.grep = null; renderTree(t); return; }
  const sha = t.sha, q = t.query.slice(1);
  grepTimer = setTimeout(() => source()?.tree(sha, { grep: q }).then(r => {
    if (!current(t) || t.sha !== sha || t.query.slice(1) !== q) return;
    if (r.fileIcons) Object.assign(DATA.fileIcons, r.fileIcons);
    t.grep = r.files || [];
    renderTree(t);
  }, () => {}), GREP_MS);
}

/* A fa kattintásai: a diff-szűrő, a mappák; a fájlra `onFile(path)`. */
function treeClick(t, target, onFile) {
  const diff = target.closest('.fv-diff');
  if (diff) {
    t.all = !t.all;
    diff.setAttribute('aria-pressed', String(!t.all));
    if (t.all && !t.tree) loadTree(t); else renderTree(t);
    return true;
  }
  const dir = /** @type {HTMLElement} */ (target.closest('.fv-dir'));
  if (dir) {
    const path = dir.dataset.dir, open = dir.getAttribute('aria-expanded') === 'true';
    if (open) { t.closed.add(path); t.opened.delete(path); }
    else { t.closed.delete(path); t.opened.add(path); }
    if (!open && t.all && t.tree?.lazy && !t.loaded.has(path) && t.tree.dirs.includes(path)) loadDir(t, path);
    renderTree(t);
    return true;
  }
  const file = /** @type {HTMLElement} */ (target.closest('.fv-file'));
  if (file) { onFile(file.dataset.path); return true; }
  return false;
}

function onResize(e) {
  const tree = /** @type {HTMLElement} */ (e.currentTarget.parentElement.querySelector('.fv-tree'));
  const handle = /** @type {HTMLElement} */ (e.currentTarget);
  const x0 = e.clientX, w0 = tree.getBoundingClientRect().width;
  handle.setPointerCapture(e.pointerId);
  handle.classList.add('on');
  const move = ev => setTreeWidth(Math.max(WIDTH_MIN, Math.min(innerWidth * 0.7, w0 + x0 - ev.clientX)));
  const up = () => {
    handle.removeEventListener('pointermove', move);
    handle.classList.remove('on');
    try { localStorage.setItem(WIDTH_KEY, String(Math.round(tree.getBoundingClientRect().width))); } catch { /* privát ablak */ }
  };
  handle.addEventListener('pointermove', move);
  handle.addEventListener('pointerup', up, { once: true });
  e.preventDefault();
}

/* ── Sidebar ── */
const sideBtn = /** @type {HTMLButtonElement} */ (document.getElementById('sideBtn'));
sideBtn.innerHTML = icon('sidebar');
sideBtn.addEventListener('click', () => (side ? closeSide() : openSide()));

/* A fa tárgya: a lenyitott commit (a változott fájlai), különben a saját worktree mostani állapota —
   a nem commitolt sora, ha van, különben a HEAD-commitja —, minden fájllal. */
function sideTarget() {
  if (expanded) return { sha: expanded, all: false, clean: false, commit: true };
  const wt = focusWt();
  if (!wt) return null;
  const wip = DATA.commits.find(c => c.uncommitted && !c.staged && c.worktree === wt.slug);
  return wip ? { sha: wip.sha, all: true, clean: false, commit: false } : { sha: wt.head, all: true, clean: true, commit: false };
}

function retarget() {
  if (!side) return;
  const want = sideTarget();
  // a lenyitott HEAD-commit és a tiszta worktree HEAD-je ugyanaz a sha, más tárgy
  if (!want || (want.sha === side.sha && want.commit === side.commit)) { renderTree(side); return; }
  const { el, query } = side;
  side = { ...newTree(el, want.sha, want.all, want.clean), commit: want.commit };
  side.query = query;
  const btn = el.querySelector('.fv-diff');
  btn.setAttribute('aria-pressed', String(!want.all));
  btn.disabled = want.clean;
  if (side.all) loadTree(side);
  renderTree(side);
}

function openSide() {
  if (side) return;
  const el = document.createElement('aside');
  el.className = 'side';
  el.setAttribute('aria-label', 'Fájlok');
  el.innerHTML = `<div class="fv-resize" role="separator" aria-orientation="vertical" aria-label="A fa szélessége"></div>${treeHtml(false, false)}`;
  document.body.append(el);
  document.body.classList.add('side-on');
  side = { ...newTree(el, null, false), commit: false };
  el.addEventListener('click', e => treeClick(side, /** @type {HTMLElement} */ (e.target), sideFile));
  el.querySelector('.fv-search input').addEventListener('input', e => onQuery(side, /** @type {HTMLInputElement} */ (e.target).value));
  el.querySelector('.fv-resize').addEventListener('pointerdown', onResize);
  sideBtn.setAttribute('aria-pressed', 'true');
  try { localStorage.setItem(SIDE_KEY, '1'); } catch { /* privát ablak */ }
  retarget();
}

function closeSide() {
  if (!side) return;
  side.el.remove();
  side = null;
  document.body.classList.remove('side-on');
  sideBtn.setAttribute('aria-pressed', 'false');
  try { localStorage.setItem(SIDE_KEY, '0'); } catch { /* privát ablak */ }
}

/* A sidebar fájlja: a lenyitott commit változott fájlja a panelben nyílik le (odagörgetve), a többi
   teljes képernyőn. */
function sideFile(path) {
  side.path = path;
  renderTree(side);
  const el = side.commit && expanded === side.sha && /** @type {HTMLElement} */ ([...document.querySelectorAll(`${OPEN_PANEL} .file`)]
    .find(x => newPath(/** @type {HTMLElement} */ (x).dataset.path) === path));
  if (!el) { openFull(side.sha, path, { all: true, clean: side.clean }); return; }
  if (el.getAttribute('aria-expanded') === 'true') revealFile(el);
  else toggleFile(el, expanded, true);
}

onExpanded(retarget);
try { if (localStorage.getItem(SIDE_KEY) === '1') queueMicrotask(openSide); } catch { /* privát ablak */ }

/* ── Teljes képernyő ── */

/* A panel fájlfejlécének ikonja: a fájl teljes képernyőn, az első változásánál. */
export function openFromPanel(fileEl, sha) {
  openFull(sha, newPath(fileEl.dataset.path));
}

/** @param {string} sha @param {string} path
    @param {{ line?: number | null, all?: boolean, clean?: boolean }} [o] `all`: minden fájllal;
    `clean`: a tiszta worktree HEAD-je (a diff-szűrő letiltva) */
export function openFull(sha, path, o = {}) {
  if (!sha || fv) return;
  const c = commitBySha(sha);
  if (!c) return;
  const all = Boolean(o.all), clean = Boolean(o.clean);
  const el = document.createElement('div');
  el.className = 'fv';
  el.setAttribute('role', 'dialog');
  el.setAttribute('aria-label', 'Teljes képernyő');
  el.innerHTML = `<div class="fv-head"><h2 class="fv-subject">${esc(c.subject)}</h2>`
    + `<button type="button" class="mini fv-close" data-fv-close aria-label="Bezárás (Esc)" data-tip="Bezárás (Esc)">${icon('close')}</button></div>`
    + '<div class="fv-main"><div class="fv-center"><div class="fv-path"></div><div class="diff fv-box"></div></div>'
    + '<div class="fv-resize" role="separator" aria-orientation="vertical" aria-label="A fa szélessége"></div>'
    + `${treeHtml(all, clean)}</div>`;
  document.body.append(el);
  fv = { ...newTree(el, sha, all, clean), key: null };
  el.addEventListener('click', onFullClick);
  el.querySelector('.fv-search input').addEventListener('input', e => onQuery(fv, /** @type {HTMLInputElement} */ (e.target).value));
  el.querySelector('.fv-resize').addEventListener('pointerdown', onResize);
  addEventListener('keydown', onKey, true);
  if (all) loadTree(fv);
  selectFile(path, o.line ?? null);
}

/* A fájl tartalma középen; `line`: ide görget (alapból az első változáshoz). */
function selectFile(path, line = null) {
  if (!fv) return;
  const ed = editingDiff();
  if (ed && fv.el.contains(ed.root)) ed.stopEditing();
  if (fv.key) forgetFile(fv.key);
  fv.path = path;
  fv.key = `fv\n${fv.sha}\n${path}`;
  renderTree(fv);
  const head = fv.el.querySelector('.fv-path'), box = fv.el.querySelector('.fv-box'), center = fv.el.querySelector('.fv-center');
  const f = changedFiles(fv.sha).get(path) || { path, icon: fv.tree?.files.find(x => x.path === path)?.icon };
  head.innerHTML = `${fileIcon(f)}<span class="path">${esc(path)}</span>`;
  head.classList.toggle('deleted', f.status === 'D');
  showPath(path);
  let scrolled = false;
  const key = fv.key;
  fileContent(box, fv.sha, path, key, fill => { if (fv?.key === key) fill(); }, {
    changed: Boolean(f.changed),
    ready: view => {
      if (scrolled || fv?.key !== key) return;
      scrolled = true;
      view.scrollToLine(line ?? view.firstChange(), center, head.offsetHeight);
    },
  });
  if (line == null) center.scrollTop = 0;
}

/* A HEAD-commit fájljának első mentése után megjelent a worktree nem commitolt sora: a nézet arra vált,
   a kódnézet (és a szerkesztés) a helyén marad, az új kulcson. */
function toWip() {
  const view = fv.key && codeViews.get(fv.key), row = view?.d.write;
  if (!row || fv.sha === row || !commitBySha(row)) return;
  const key = `fv\n${row}\n${fv.path}`;
  codeViews.delete(fv.key);
  codeViews.set(key, view);
  fv.sha = row;
  fv.key = key;
  fv.tree = null;
  fv.clean = false;
  fv.el.querySelector('.fv-diff').disabled = false;
  if (fv.all) loadTree(fv);
  fv.el.querySelector('.fv-subject').textContent = commitBySha(row).subject;
}

/* Élő frissítés (a WIP sor új adata): a fák és a nyitott fájl újra (a kódnézet helyben frissül). */
export function refreshFull() {
  if (side) {
    retarget();
    if (side.all && side.sha?.startsWith('*')) loadTree(side);
  }
  if (!fv) return;
  toWip();
  if (!commitBySha(fv.sha)) return;
  if (fv.all && fv.sha.startsWith('*')) loadTree(fv);
  renderTree(fv);
  const box = fv.el.querySelector('.fv-box'), key = fv.key;
  const f = changedFiles(fv.sha).get(fv.path);
  fileContent(box, fv.sha, fv.path, key, fill => { if (fv?.key === key) fill(); }, { changed: Boolean(f?.changed) });
}

function closeFull() {
  if (!fv) return;
  const { sha, path, el } = fv;
  const ed = editingDiff();
  if (ed && el.contains(ed.root)) ed.stopEditing();
  if (fv.key) forgetFile(fv.key);
  el.remove();
  fv = null;
  showPath(null);
  removeEventListener('keydown', onKey, true);
  const f = /** @type {HTMLElement} */ ([...document.querySelectorAll(`${OPEN_PANEL} .file`)]
    .find(x => newPath(/** @type {HTMLElement} */ (x).dataset.path) === path));
  if (!f || expanded !== sha) return;
  if (f.getAttribute('aria-expanded') === 'true') revealFile(f);
  else toggleFile(f, sha, true);
}

function onFullClick(e) {
  const t = /** @type {HTMLElement} */ (e.target);
  if (t.closest('[data-fv-close]')) { closeFull(); return; }
  const md = /** @type {HTMLElement} */ (t.closest('[data-md-mode]')), svg = /** @type {HTMLElement} */ (t.closest('[data-svg-mode]'));
  if (md) { if ((md.dataset.mdMode === 'raw') !== mdRaw) setMdRaw(!mdRaw); return; }
  if (svg) { if ((svg.dataset.svgMode === 'code') !== svgCode) setSvgCode(!svgCode); return; }
  treeClick(fv, t, path => { if (path !== fv.path) selectFile(path); });
}

/* A markdown / SVG nézetváltója a teljes képernyő fájlját is újrarajzolja. */
onModeChange(() => { if (fv?.path) selectFile(fv.path); });

function onKey(e) {
  const t = /** @type {HTMLElement} */ (e.target);
  if (e.key === 'Escape') {
    if (t.closest?.('.cm-panel')) return;        // a CodeMirror keresője zárul
    e.preventDefault();
    e.stopImmediatePropagation();
    const ed = editingDiff();
    if (ed && fv.el.contains(ed.root)) ed.stopEditing();   // a nézet nyitva marad
    else if (t.closest?.('.fv-search') && fv.query) {
      const input = /** @type {HTMLInputElement} */ (t);
      input.value = '';
      onQuery(fv, '');
    } else closeFull();
    return;
  }
  if (!t.closest?.('.cm-editor, input, textarea')) e.stopImmediatePropagation();   // a lap navigációja áll
}
