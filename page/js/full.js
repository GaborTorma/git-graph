/* ── Teljes nézet ── a commit (vagy a WIP sor) az eszközsor és a lábléc közti rétegen: az eszközsorban
   balra a repó neve és a HEAD-chip marad, a szűrők és a kereső helyén a subject és az X; középen a
   kijelölt fájl diffje (`fileContent`: a CodeMirror, a markdown, a kép) — kijelölt fájl nélkül a
   gráf (a lap maga, a fa mellett, használható) —, jobbra a fájlfa; a kijelölt fájlra újra kattintva
   vissza a gráfhoz. A diff-szűrő bekapcsolva a sor változott fájljait mutatja (a mappaláncok összevonva),
   kikapcsolva a commit állapotának minden fájlját (`file_tree`; 20 000 fájl fölött mappánként,
   lustán); a tiszta worktree HEAD-jén (nincs WIP sor, nincs kijelölt commit) letiltva, minden fájllal. A
   kereső név szerint szűr, `?` előtaggal a tartalomban keres (`git grep`). A fa szélessége
   húzható (legalább 200 px), a lap megjegyzi. A nézet a commit gombjával nyílik, ott, ahol a
   Fejlesztő állt (a lenyitott fájl látszó sora) — a gomb ezért az eszközsorban, a görgetőn kívül
   van; nyitott commit nélkül a saját worktree mostani állapota nyílik (a WIP sor, tisztán a HEAD),
   minden fájllal. A lábléc alatta is látszik, a commitszám helyén a nézett fájl útja. A HEAD-commit tiszta fájlja is szerkeszthető: az első mentéstől a fájl a WIP
   soré, a nézet átvált rá; Esc-re bezárul, és a panelben a kijelölt fájl
   lenyitva, odagörgetve marad. A nézet billentyűit a réteg elkapja (a lap navigációja áll). */
import { editingDiff } from './cm.js';
import { codeViews, fileContent, forgetFile, onModeChange, mdRaw, setMdRaw, setSvgCode, source, svgCode, toggleFile } from './diff.js';
import { OPEN_PANEL, counter, pendingEl, scroller } from './dom.js';
import { fileIcon, icon } from './icons.js';
import { commitBySha, focusWt } from './model.js';
import { revealFile } from './panel.js';
import { DATA, expanded } from './state.js';
import { esc, fold } from './util.js';

const WIDTH_KEY = 'git-graph:treeWidth';
const WIDTH0 = 280, WIDTH_MIN = 200;
const GREP_MS = 250;           // a tartalomkeresés ennyi csend után indul

/** @type {any} */
let fv = null;

/* A réteg az eszközsor alatt kezdődik és a lábléc fölött ér véget: a két határ CSS-változóban; a fa
   szélessége is (a gráf annyival keskenyebb). */
const root = document.documentElement;
const foot = /** @type {HTMLElement} */ (document.getElementById('foot'));
const chrome = /** @type {HTMLElement} */ (document.querySelector('.chrome'));
const footPath = /** @type {HTMLElement} */ (document.getElementById('footPath'));
new ResizeObserver(() => root.style.setProperty('--foot-h', `${foot.offsetHeight}px`)).observe(foot);
new ResizeObserver(() => root.style.setProperty('--chrome-h', `${chrome.getBoundingClientRect().bottom}px`)).observe(chrome);
const setTreeWidth = w => root.style.setProperty('--fv-tree-w', `${Math.round(w)}px`);

/* A lábléc közepe: a nézett fájl útja (a worktree gyökeréhez képest), különben a commitszám. */
function showPath(path) {
  footPath.innerHTML = path ? `<bdi>${esc(path)}</bdi>` : '';   // az rtl-vágás ne fordítsa meg az utat
  footPath.hidden = !path;
  counter.hidden = Boolean(path);
}

/* Az eszközsor gombja: amíg egy commit (vagy WIP sor) nyitva van. */
const fullBtn = /** @type {HTMLButtonElement} */ (document.getElementById('fullBtn'));
fullBtn.innerHTML = icon('expand');
fullBtn.addEventListener('click', () => (expanded ? openFull(expanded) : openOwn()));

/* Nyitott commit nélkül: a saját worktree mostani állapota — a nem commitolt sora, ha van, különben a
   HEAD-commitja —, minden fájllal (ebből választ a Fejlesztő). */
function openOwn() {
  const wt = focusWt();
  if (!wt) return;
  const wip = DATA.commits.find(c => c.uncommitted && !c.staged && c.worktree === wt.slug);
  openFull(wip ? wip.sha : wt.head, true, !wip);
}

/* A `--numstat` átnevezése (`a => b`, `dir/{a => b}/x`): az új út. */
const newPath = p => (p.includes(' => ')
  ? p.replace(/\{([^{}]*) => ([^{}]*)\}/, '$2').replace(/^.* => /, '').replace(/\/{2,}/g, '/') : p);

const savedWidth = () => {
  try { return Math.max(WIDTH_MIN, Number(localStorage.getItem(WIDTH_KEY)) || WIDTH0); } catch { return WIDTH0; }
};

/* A sor változott fájljai: út → bejegyzés (a commit-panel adatai: ikon, +/−, állapot). */
function changedFiles(sha) {
  const out = new Map();
  for (const f of DATA.stats[sha]?.files || []) {
    const path = newPath(f.path);
    out.set(path, { ...f, path, changed: true });
  }
  return out;
}

/* A fa bejegyzései: a változott fájlok, a kapcsolóval a commit minden fájlja (a törölt is, a
   helyén), kereséskor a találatok. */
function entries() {
  const changed = changedFiles(fv.sha);
  if (fv.grep) return fv.grep.map(f => changed.get(f.path) || { ...f, changed: false });
  let list = [...changed.values()];
  if (fv.all && fv.tree) {
    const seen = new Set(list.map(f => f.path));
    list = list.concat(fv.tree.files.filter(f => !seen.has(f.path)).map(f => ({ ...f, changed: false })));
  }
  const q = fv.query && !fv.query.startsWith('?') ? fold(fv.query) : '';
  return q ? list.filter(f => fold(f.path.split('/').pop()).includes(q)) : list;
}

/* A mappafa: { path, name, dirs, files, st (a változott fájlok állapotai), lazy }; az egyetlen
   almappájú, fájl nélküli mappák lánca egy sor („page/js”). */
function buildTree(list) {
  const root = { path: '', name: '', dirs: new Map(), files: [], st: new Set(), lazy: false };
  const dirOf = path => {
    let node = root;
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
    (i < 0 ? root : dirOf(f.path.slice(0, i))).files.push(f);
  }
  if (fv.all && fv.tree?.lazy && !fv.grep && !fv.query) {
    for (const d of fv.tree.dirs) { const node = dirOf(d); node.lazy = !fv.loaded.has(d); }
  }
  const status = f => (f.status === 'A' || f.status === 'D' ? f.status : 'M');
  const mark = node => {
    for (const d of node.dirs.values()) { mark(d); d.st.forEach(s => node.st.add(s)); }
    for (const f of node.files) if (f.changed) node.st.add(status(f));
    if (node.untracked) node.st.add('A');
  };
  mark(root);
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
  compact(root);
  return root;
}

/* Nyitva-e a mappa: kereséskor mind; alapnézetben mind, amit a Fejlesztő nem csukott be; a
   minden fájl nézetben csak a változott fájlok mappái és amit kinyitott. */
const isOpen = d => (fv.query ? true : fv.all ? fv.opened.has(d.path) || (d.st.size > 0 && !fv.closed.has(d.path))
  : !fv.closed.has(d.path));

const ST_CLASS = { A: ' added', D: ' deleted', M: ' modified' };
const stClass = st => (!st.size ? '' : st.size === 1 ? ST_CLASS[[...st][0]] : ' modified');

function churn(f) {
  if (!f.changed || f.bin || f.count) return '';
  return `<span class="churn">${f.add ? `<span class="a">+${f.add}</span>` : ''}${f.del ? `<span class="d">−${f.del}</span>` : ''}</span>`;
}

function rowsHtml(node, depth) {
  const byName = (a, b) => a.name.localeCompare(b.name);
  let out = '';
  for (const d of [...node.dirs.values()].sort(byName)) {
    const open = isOpen(d) && !d.count;
    const inside = !open && fv.path?.startsWith(`${d.path}/`);
    out += `<div class="fv-row fv-dir${stClass(d.st)}${inside ? ' sel-in' : ''}" data-dir="${esc(d.path)}" style="--depth:${depth}"`
      + ` aria-expanded="${open}"><span class="chev">${d.count ? '' : icon('chev')}</span>${icon('folder', 'ic fic')}`
      + `<span class="name">${esc(d.name)}</span>${d.count ? `<span class="churn"><span class="tag">${d.count} fájl</span></span>` : ''}</div>`;
    if (open) out += rowsHtml(d, depth + 1);
  }
  for (const f of node.files.map(x => ({ ...x, name: x.path.split('/').pop() })).sort(byName)) {
    const st = f.changed ? ST_CLASS[f.status === 'A' || f.status === 'D' ? f.status : 'M'] : '';
    out += `<div class="fv-row fv-file${st}${f.path === fv.path ? ' sel' : ''}" data-path="${esc(f.path)}" style="--depth:${depth}"`
      + ` aria-selected="${f.path === fv.path}"><span class="chev"></span>${fileIcon(f)}<span class="name">${esc(f.name)}</span>${churn(f)}</div>`;
  }
  return out;
}

function renderTree() {
  if (!fv) return;
  const list = fv.el.querySelector('.fv-list');
  const top = list.scrollTop;
  const tree = buildTree(entries());
  list.innerHTML = rowsHtml(tree, 0) || `<p class="fv-empty">${fv.grep ? 'Nincs találat.' : 'Nincs ilyen fájl.'}</p>`;
  list.scrollTop = top;
}

/* A kijelölés megszűnik: középen újra a gráf; a függő mentés lefut. */
function deselect() {
  const ed = editingDiff();
  if (ed && fv.el.contains(ed.root)) ed.stopEditing();
  if (fv.key) forgetFile(fv.key);
  fv.path = null;
  fv.key = null;
  fv.el.querySelector('.fv-center').hidden = true;
  showPath(null);
  renderTree();
}

/* A fájl tartalma középen; `line`: ide görget (alapból az első változáshoz). */
function selectFile(path, line = null) {
  if (!fv) return;
  const ed = editingDiff();
  if (ed && fv.el.contains(ed.root)) ed.stopEditing();
  if (fv.key) forgetFile(fv.key);
  fv.path = path;
  fv.key = `fv\n${fv.sha}\n${path}`;
  renderTree();
  const head = fv.el.querySelector('.fv-path'), box = fv.el.querySelector('.fv-box'), center = fv.el.querySelector('.fv-center');
  const f = changedFiles(fv.sha).get(path) || { path, icon: fv.tree?.files.find(x => x.path === path)?.icon };
  center.hidden = false;
  head.innerHTML = `${fileIcon(f)}<span class="path">${esc(path)}</span>`;
  showPath(path);
  head.classList.toggle('deleted', f.status === 'D');
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
  fv.el.querySelector('.fv-diff').disabled = false;
  if (fv.all) loadTree();
  fv.bar.querySelector('.fv-subject').textContent = commitBySha(row).subject;
}

/* Élő frissítés (a WIP sor új adata): a fa és a nyitott fájl újra (a kódnézet helyben frissül). */
export function refreshFull() {
  if (!fv) return;
  toWip();
  if (!commitBySha(fv.sha)) return;
  if (fv.all && fv.sha.startsWith('*')) loadTree();
  renderTree();
  if (fv.path) {
    const box = fv.el.querySelector('.fv-box'), key = fv.key;
    const f = changedFiles(fv.sha).get(fv.path);
    fileContent(box, fv.sha, fv.path, key, fill => { if (fv?.key === key) fill(); }, { changed: Boolean(f?.changed) });
  }
}

function loadTree() {
  const sha = fv.sha;
  source()?.tree(sha).then(t => {
    if (fv?.sha !== sha) return;
    fv.tree = { ...t, files: t.files || [], dirs: t.dirs || [] };
    if (t.fileIcons) Object.assign(DATA.fileIcons, t.fileIcons);
    fv.loaded = new Set();
    renderTree();
  }, e => {
    if (fv?.sha !== sha) return;
    fv.el.querySelector('.fv-list').insertAdjacentHTML('afterbegin',
      `<p class="fv-empty fv-error">A fájllista nem tölthető be: ${esc(e?.message || e?.code || e)}</p>`);
  });
}

/* Lusta mappa (20 000 fájl fölött): a tartalma kinyitáskor. */
function loadDir(dir) {
  const sha = fv.sha;
  source()?.tree(sha, { dir }).then(t => {
    if (fv?.sha !== sha) return;
    if (t.fileIcons) Object.assign(DATA.fileIcons, t.fileIcons);
    fv.tree.files = fv.tree.files.concat(t.files || []);
    fv.tree.dirs = [...new Set([...fv.tree.dirs, ...(t.dirs || [])])];
    fv.loaded.add(dir);
    renderTree();
  }, () => {             // nem jött: a mappa csukva marad, a következő kinyitás újra kéri
    if (fv?.sha !== sha) return;
    fv.opened.delete(dir);
    renderTree();
  });
}

let grepTimer = 0;
function onQuery(value) {
  fv.query = value.trim();
  clearTimeout(grepTimer);
  if (!fv.query.startsWith('?') || fv.query.length < 2) { fv.grep = null; renderTree(); return; }
  const sha = fv.sha, q = fv.query.slice(1);
  grepTimer = setTimeout(() => source()?.tree(sha, { grep: q }).then(t => {
    if (fv?.sha !== sha || fv.query.slice(1) !== q) return;
    if (t.fileIcons) Object.assign(DATA.fileIcons, t.fileIcons);
    fv.grep = t.files || [];
    renderTree();
  }, () => {}), GREP_MS);
}

/* A panelben lenyitott fájl, amelyik a görgető régió tetején látszik, és a látszó sora. A régió a
   lista, a fix sávbeli WIP-panelnél maga a panel (saját görgetéssel). */
function handoff(sha) {
  const panel = document.querySelector(OPEN_PANEL);
  const area = panel && pendingEl.contains(panel) ? /** @type {HTMLElement} */ (panel) : scroller;
  const top = area.getBoundingClientRect().top;
  for (const f of panel?.querySelectorAll('.file[aria-expanded="true"]') || []) {
    const box = /** @type {HTMLElement} */ (f.nextElementSibling);
    if (box.getBoundingClientRect().bottom <= top + 1) continue;
    const path = /** @type {HTMLElement} */ (f).dataset.path;
    const view = codeViews.get(`${sha}\n${path}`);
    return { path: newPath(path), line: view ? view.topLine(area) : null };
  }
  const first = (DATA.stats[sha]?.files || []).find(f => !f.count);
  return { path: first ? newPath(first.path) : null, line: null };
}

/** @param {string} sha @param {boolean} [all] minden fájllal, kijelölt fájl nélkül
    @param {boolean} [clean] a tiszta worktree HEAD-je: a diff-szűrő letiltva */
export function openFull(sha, all = false, clean = false) {
  if (!sha || fv) return;
  const c = commitBySha(sha);
  if (!c) return;
  const { path, line } = all ? { path: null, line: null } : handoff(sha);
  const bar = document.createElement('div');
  bar.className = 'fv-bar';
  bar.innerHTML = `<h2 class="fv-subject">${esc(c.subject)}</h2>`
    + `<button type="button" class="mini fv-close" data-fv-close aria-label="Bezárás (Esc)" data-tip="Bezárás (Esc)">${icon('close')}</button>`;
  chrome.append(bar);
  const el = document.createElement('div');
  el.className = 'fv';
  el.setAttribute('role', 'region');
  el.setAttribute('aria-label', 'Teljes nézet');
  setTreeWidth(savedWidth());
  el.innerHTML = '<div class="fv-center" hidden><div class="fv-path"></div><div class="diff fv-box"></div></div>'
    + '<div class="fv-resize" role="separator" aria-orientation="vertical" aria-label="A fa szélessége"></div>'
    + '<div class="fv-tree"><div class="fv-tools">'
    + `<label class="search fv-search">${icon('search')}<input type="search" placeholder="Szűrés név szerint · ?tartalom"`
    + ' aria-label="Fájlok szűrése" spellcheck="false"></label>'
    + `<button type="button" class="mini fv-diff" aria-pressed="${!all}"${clean ? ' disabled' : ''}`
    + ` aria-label="Csak a változott fájlok" data-tip="Csak a változott fájlok">${icon('changes')}</button>`
    + '</div><div class="fv-list"></div></div>';
  document.body.append(el);
  document.body.classList.add('fv-on');
  fv = { sha, el, bar, path: null, key: null, all, tree: null, loaded: new Set(), query: '', grep: null,
         opened: new Set(), closed: new Set() };
  el.addEventListener('click', onClick);
  bar.addEventListener('click', onClick);
  el.querySelector('.fv-search input').addEventListener('input', e => onQuery(/** @type {HTMLInputElement} */ (e.target).value));
  el.querySelector('.fv-resize').addEventListener('pointerdown', onResize);
  addEventListener('keydown', onKey, true);
  if (all) loadTree();
  if (path) selectFile(path, line); else renderTree();
}

function closeFull() {
  if (!fv) return;
  const { sha, path, el, bar } = fv;
  const ed = editingDiff();
  if (ed && el.contains(ed.root)) ed.stopEditing();
  if (fv.key) forgetFile(fv.key);
  el.remove();
  bar.remove();
  document.body.classList.remove('fv-on');
  fv = null;
  showPath(null);
  removeEventListener('keydown', onKey, true);
  const f = /** @type {HTMLElement} */ ([...document.querySelectorAll(`${OPEN_PANEL} .file`)]
    .find(x => newPath(/** @type {HTMLElement} */ (x).dataset.path) === path));
  if (!f) return;
  if (f.getAttribute('aria-expanded') === 'true') revealFile(f);
  else toggleFile(f, sha, true);
}

function onClick(e) {
  const t = /** @type {HTMLElement} */ (e.target);
  if (t.closest('[data-fv-close]')) { closeFull(); return; }
  const diff = t.closest('.fv-diff');
  if (diff) {
    fv.all = !fv.all;
    diff.setAttribute('aria-pressed', String(!fv.all));
    if (fv.all && !fv.tree) loadTree(); else renderTree();
    return;
  }
  const md = /** @type {HTMLElement} */ (t.closest('[data-md-mode]')), svg = /** @type {HTMLElement} */ (t.closest('[data-svg-mode]'));
  if (md) { if ((md.dataset.mdMode === 'raw') !== mdRaw) setMdRaw(!mdRaw); return; }
  if (svg) { if ((svg.dataset.svgMode === 'code') !== svgCode) setSvgCode(!svgCode); return; }
  const dir = /** @type {HTMLElement} */ (t.closest('.fv-dir'));
  if (dir) {
    const path = dir.dataset.dir, open = dir.getAttribute('aria-expanded') === 'true';
    if (open) { fv.closed.add(path); fv.opened.delete(path); }
    else { fv.closed.delete(path); fv.opened.add(path); }
    if (!open && fv.all && fv.tree?.lazy && !fv.loaded.has(path) && fv.tree.dirs.includes(path)) loadDir(path);
    renderTree();
    return;
  }
  const file = /** @type {HTMLElement} */ (t.closest('.fv-file'));
  if (file) { if (file.dataset.path === fv.path) deselect(); else selectFile(file.dataset.path); }
}

/* A markdown / SVG nézetváltója a teljes nézet fájlját is újrarajzolja. */
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
      onQuery('');
    } else closeFull();
    return;
  }
  // a fájl nézete alatt a lap navigációja áll; kijelölt fájl nélkül a gráfé
  if (fv.path && !t.closest?.('.cm-editor, input, textarea')) e.stopImmediatePropagation();
}

function onResize(e) {
  const tree = /** @type {HTMLElement} */ (fv.el.querySelector('.fv-tree'));
  const handle = /** @type {HTMLElement} */ (e.currentTarget);
  const x0 = e.clientX, w0 = tree.getBoundingClientRect().width;
  handle.setPointerCapture(e.pointerId);
  handle.classList.add('on');
  const move = ev => {
    const w = Math.max(WIDTH_MIN, Math.min(innerWidth * 0.7, w0 + x0 - ev.clientX));
    setTreeWidth(w);
  };
  const up = () => {
    handle.removeEventListener('pointermove', move);
    handle.classList.remove('on');
    try { localStorage.setItem(WIDTH_KEY, String(Math.round(tree.getBoundingClientRect().width))); } catch { /* privát ablak */ }
  };
  handle.addEventListener('pointermove', move);
  handle.addEventListener('pointerup', up, { once: true });
  e.preventDefault();
}
