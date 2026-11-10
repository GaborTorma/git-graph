/* ── Fájlfa: sidebar és teljes képernyő ──
   A sidebar az eszközsor gombjával nyílik (a lap megjegyzi): a gráf mellett, jobbra a fájlfa, az
   eszközsor és a lábléc között. A fa a lenyitott commitot követi (a változásai szerint színezve);
   lenyitott commit nélkül a saját worktree mostani állapotát mutatja minden fájllal, színezés nélkül
   (`plain`); ilyenkor a diff-szűrő a WIP sort (ha nincs, a HEAD-commitot) nyitja le, és a fa már azt követi. A fában a lenyitott commit változott fájlja a commit-panelben nyílik le, odagörgetve;
   a többi fájl (változatlan, vagy nincs lenyitott commit) teljes képernyőn.
   A teljes képernyő a panel lenyitott fájljának fejlécéből nyílik (`data-full`), a fájl első
   változásánál: a lap tetejétől a láblécig. Fent teljes szélességben a fejléc: a repó neve, a HEAD-chip (ha a
   fájl útja nem fér ki, eltűnik), a fájl útja, jobbra a fájlban kereső és a kilépés; alatta (a görgetés a
   fejléc alatt) a fájl diffje (`fileContent`: a CodeMirror, a markdown, a kép), keret nélkül; jobbra a saját
   fája (fölötte a kereső és a diff-szűrő), alatta a
   commitlista: a saját worktree WIP sora mindig, alatta a commit ágának (a HEAD-é, ha abban van)
   commitjai közül a commit és két-két szomszédja; rajtuk a commit váltható. A WIP sor kék / narancs
   (`wip-tone`), a fa a fájlok mellett a WIP számait is mutatja (`wipCounts`). A HEAD-commit tiszta
   fájlja is szerkeszthető: a mentés a WIP sorba ír, a nézet a commiton marad; Esc-re bezárul, és
   a panelben a kijelölt fájl lenyitva, odagörgetve marad. A nézet billentyűit a réteg elkapja.
   A diff-szűrő bekapcsolva a sor változott fájljait mutatja (a mappaláncok összevonva), kikapcsolva
   a commit állapotának minden fájlját (`file_tree`; 20 000 fájl fölött mappánként, lustán); a tiszta
   worktree HEAD-jén letiltva, minden fájllal. A kereső név szerint szűr, `?` előtaggal a tartalomban
   keres (`git grep`); a diff-szűrő a találatokra is vonatkozik. A fa szélessége húzható (legalább 200 px), a lap megjegyzi; a lábléc közepén a
   nézett fájl útja áll. */
import { editingDiff } from './cm.js';
import { codeViews, fileContent, forgetFile, onModeChange, mdRaw, setMdRaw, setSvgCode, source, svgCode, toggleFile } from './diff.js';
import { OPEN_PANEL, counter } from './dom.js';
import { fileIcon, icon } from './icons.js';
import { commitBySha, focusWt, reachable, wipCounts, wipHtml } from './model.js';
import { revealFile } from './panel.js';
import { DATA, expanded, onExpanded } from './state.js';
import { esc, fmtInt, fold } from './util.js';

const WIDTH_KEY = 'git-graph:treeWidth';
const SIDE_KEY = 'git-graph:sidebar';
const WIDTH0 = 280, WIDTH_MIN = 200;
const GREP_MS = 250;           // a tartalomkeresés ennyi csend után indul
const AROUND = 2;              // a commitlistán a commit fölött és alatt ennyi szomszéd

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
// a pontos (törtpixeles) magasság: a kerekített `offsetHeight` mellett a lábléc fölött hézag maradhat
new ResizeObserver(() => root.style.setProperty('--foot-h', `${foot.getBoundingClientRect().height}px`)).observe(foot);
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
const treeHtml = (all, clean, commits = false) => '<div class="fv-tree"><div class="fv-tools">'
  + `<label class="search fv-search">${icon('search')}<input type="search" placeholder="Szűrés név szerint · ?tartalom"`
  + ' aria-label="Fájlok szűrése" spellcheck="false"></label>'
  + `<button type="button" class="select gear fv-diff" aria-pressed="${!all}"${clean ? ' disabled' : ''}`
  + ` aria-label="Csak a változott fájlok" data-tip="Csak a változott fájlok">${icon('changes')}</button>`
  + `</div><div class="fv-list"></div>${commits ? '<div class="fv-commits" aria-label="Commitok" data-keep-editing></div>' : ''}</div>`;

const newTree = (el, sha, all, clean = false) => ({ el, sha, all, clean, path: null, grepTimer: 0, tree: null, loaded: new Set(), query: '', grep: null,
  opened: new Set(), closed: new Set() });

/* A fa bejegyzései: a változott fájlok, a kapcsolóval a commit minden fájlja (a törölt is, a
   helyén), kereséskor a találatok. */
function entries(t) {
  const changed = t.plain ? new Map() : changedFiles(t.sha);
  if (t.grep) return (t.all ? t.grep : t.grep.filter(f => changed.has(f.path))).map(f => changed.get(f.path) || { ...f, changed: false });
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

/* A fájl számai: a commit +/−-a, mellette a WIP eltérései (`w`, kék / narancs). */
function churn(f, w) {
  if (f.bin || f.count) return '';
  const own = f.changed ? `${f.add ? `<span class="a">+${f.add}</span>` : ''}${f.del ? `<span class="d">−${f.del}</span>` : ''}` : '';
  const wip = wipHtml(w);
  return own || wip ? `<span class="churn">${own}${wip}</span>` : '';
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
      + ` aria-selected="${f.path === t.path}"><span class="chev"></span>${fileIcon(f)}<span class="name">${esc(f.name)}</span>${churn(f, t.wip?.get(f.path))}</div>`;
  }
  return out;
}

function renderTree(t) {
  if (!t) return;
  const list = t.el.querySelector('.fv-list');
  const top = list.scrollTop;
  t.wip = t.plain ? new Map() : wipCounts(t.sha);
  t.el.classList.toggle('wip-tone', !t.plain && Boolean(commitBySha(t.sha)?.uncommitted));
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
    if (t === fv && fv.path) pathHead();      // a fejléc ikonja a fa adatából (a fájl a fából jöhetett)
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

function onQuery(t, value) {
  t.query = value.trim();
  clearTimeout(t.grepTimer);
  if (!t.query.startsWith('?') || t.query.length < 2) { t.grep = null; renderTree(t); return; }
  const sha = t.sha, q = t.query.slice(1);
  t.grepTimer = setTimeout(() => source()?.tree(sha, { grep: q }).then(r => {
    if (!current(t) || t.sha !== sha || t.query.slice(1) !== q) return;
    if (r.fileIcons) Object.assign(DATA.fileIcons, r.fileIcons);
    t.grep = r.files || [];
    renderTree(t);
  }, e => {                                       // a régi találat nem maradhat az új keresés alatt
    if (!current(t) || t.sha !== sha || t.query.slice(1) !== q) return;
    t.grep = [];
    renderTree(t);
    t.el.querySelector('.fv-list').innerHTML = `<p class="fv-empty fv-error">A keresés nem sikerült: ${esc(e?.message || e?.code || e)}</p>`;
  }), GREP_MS);
}

/* A fa kattintásai: a diff-szűrő, a mappák; a fájlra `onFile(path)`. */
function treeClick(t, target, onFile) {
  const diff = target.closest('.fv-diff');
  // commit nélkül a fa tárgya (`t.sha`) a WIP sor, ha van, különben a HEAD-commit: a szűrő ezt jelöli ki
  if (diff && t.plain && t === fv) {     // teljes képernyőn: ez lesz a kijelölt
    t.all = false;
    diff.setAttribute('aria-pressed', 'true');
    switchCommit(t.sha, false);
    return true;
  }
  if (diff && t.plain) {                 // a sidebarban: ez nyílik le, a fa azt követi
    /** @type {HTMLElement} */ (t.sha && document.querySelector(`.row[data-sha="${CSS.escape(t.sha)}"]`))?.click();
    return true;
  }
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
sideBtn.innerHTML = icon('sidebar', 'ic', 'md');
sideBtn.addEventListener('click', () => (side ? closeSide() : openSide()));

/* A fa tárgya: a lenyitott commit (a változott fájlai), különben a saját worktree mostani állapota —
   a nem commitolt sora, ha van, különben a HEAD-commitja —, minden fájllal. */
function sideTarget() {
  if (expanded) return { sha: expanded, all: false, clean: false, commit: true, plain: false };
  const wt = focusWt();
  if (!wt) return null;
  const sha = plainSha(wt);
  return { sha, all: true, clean: sha === wt.head, commit: false, plain: true };
}

/* Commit nélkül a fa tárgya: a worktree nem commitolt sora, ha van, különben a HEAD-commitja. */
function plainSha(wt) {
  return DATA.commits.find(c => c.uncommitted && !c.staged && c.worktree === wt.slug)?.sha || wt.head;
}

function retarget() {
  if (!side) return;
  const want = sideTarget();
  // a lenyitott HEAD-commit és a tiszta worktree HEAD-je ugyanaz a sha, más tárgy
  if (want && want.sha === side.sha && want.commit === side.commit) { renderTree(side); return; }
  const { el, query, path, plain } = side;
  side = want ? { ...newTree(el, want.sha, want.all, want.clean), commit: want.commit, plain: want.plain }
    : { ...newTree(el, null, false), commit: false };
  if (!want) { renderTree(side); return; }   // nincs tárgy (nincs saját worktree): üres fa, nem a régi
  side.query = query;
  if (plain && want.plain) side.path = path;  // a WIP sor megjelent / eltűnt: a kijelölt fájl marad
  const btn = el.querySelector('.fv-diff');
  btn.setAttribute('aria-pressed', String(!want.all));
  btn.disabled = want.clean && !want.plain;
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

/* A lenyitott commit-panel fájlsora az út szerint (az átnevezettnél az új út). */
const panelFile = path => /** @type {HTMLElement} */ ([...document.querySelectorAll(`${OPEN_PANEL} .file`)]
  .find(x => newPath(/** @type {HTMLElement} */ (x).dataset.path) === path));

/* A sidebar fájlja: a lenyitott commit változott fájlja a panelben nyílik le (odagörgetve), a többi
   teljes képernyőn. */
function sideFile(path) {
  side.path = path;
  renderTree(side);
  const el = side.commit && expanded === side.sha && panelFile(path);
  if (!el) { openFull(side.sha, path, { all: true, plain: side.plain }); return; }
  if (el.getAttribute('aria-expanded') === 'true') revealFile(el);
  else toggleFile(el, expanded, true);
}

onExpanded(retarget);
try { if (localStorage.getItem(SIDE_KEY) === '1') queueMicrotask(openSide); } catch { /* privát ablak */ }

/* ── Teljes képernyő ── */

/* A panel fájlfejlécének ikonja: a fájl teljes képernyőn, az első változásánál. */
export function openFromPanel(fileEl, sha) {
  // A panel élő nézete (a szerkesztett szöveg, a mentés sora, a visszavonás) költözik át, nem épül új a
  // commit tartalmából; bezáráskor visszakerül a panelbe (`dropView`).
  const path = newPath(fileEl.dataset.path), panelKey = `${sha}\n${fileEl.dataset.path}`, fvKey = `fv\n${sha}\n${path}`;
  const view = codeViews.get(panelKey);
  if (view) {
    if (editingDiff() === view) view.stopEditing();
    codeViews.delete(panelKey);
    codeViews.set(fvKey, view);
  }
  if (!openFull(sha, path, { borrowed: view ? { key: panelKey, fvKey } : null }) && view) {
    codeViews.delete(fvKey);
    codeViews.set(panelKey, view);
  }
}

/* A teljes képernyő fájlnézete megszűnik: a panelből kölcsönzött visszakerül a panelbe (a lenyitott
   fájl dobozába), a többi lefut és eldobódik (`forgetFile`). */
function dropView() {
  const b = fv.borrowed;
  if (!b || fv.key !== b.fvKey) { if (fv.key) forgetFile(fv.key); return; }
  const view = codeViews.get(b.fvKey);
  codeViews.delete(b.fvKey);
  if (!refillPanel(view)) view?.dispose();
}

/* A kölcsönzött nézet panelbeli fájlja újra kitöltődik: a `view`-val (visszakapja), nélküle újat épít a
   tartalmából. Hamis, ha a fájl a panelben már nincs lenyitva. */
function refillPanel(view = null) {
  const b = fv.borrowed;
  fv.borrowed = null;
  const sha = b.key.slice(0, b.key.indexOf('\n')), raw = b.key.slice(b.key.indexOf('\n') + 1);
  const f = expanded === sha && panelFile(newPath(raw));
  if (!f || f.getAttribute('aria-expanded') !== 'true') return false;
  if (view) codeViews.set(b.key, view);
  fileContent(/** @type {HTMLElement} */ (f.nextElementSibling), sha, raw, b.key, fill => fill());
  return true;
}

/** @param {string} sha @param {string} path
    @param {{ line?: number | null, all?: boolean, clean?: boolean, plain?: boolean, borrowed?: any }} [o] `all`:
    minden fájllal; `clean`: a tiszta worktree HEAD-je (a diff-szűrő letiltva); `plain`: commit nélkül (a sidebar
    színezés nélküli fájából: a worktree állapota, kijelölt commit nélkül); `borrowed`: a panelből átvett nézet
    @returns {boolean} megnyílt-e */
export function openFull(sha, path, o = {}) {
  if (!sha || fv) return false;
  if (!commitBySha(sha)) return false;
  const all = Boolean(o.all), clean = Boolean(o.clean);
  const el = document.createElement('div');
  el.className = 'fv';
  el.setAttribute('role', 'dialog');
  el.setAttribute('aria-label', 'Teljes képernyő');
  // a repó neve és a chip a lap fejlécének szerkezetében (`.repo`): ugyanott állnak
  el.innerHTML = '<div class="fv-head"><div class="repo">'
    + `<span class="repo-name">${esc(document.getElementById('repoName')?.textContent || '')}</span>`
    + '<span class="fv-chip"></span></div><div class="fv-path"></div>'
    + `<label class="search fv-find">${icon('search')}<input type="search" placeholder="Keresés a fájlban"`
    + ' aria-label="Keresés a fájlban" spellcheck="false"></label>'
    + '<button type="button" class="select gear fv-close" data-fv-close aria-label="Kilépés a teljes képernyőből (Esc)"'
    + ` data-tip="Kilépés a teljes képernyőből (Esc)">${icon('collapse', 'ic', 'md')}</button>`
    + '</div><div class="fv-main"><div class="fv-center"><div class="fv-scroll"><div class="diff fv-box"></div></div></div>'
    + '<div class="fv-resize" role="separator" aria-orientation="vertical" aria-label="A fa szélessége"></div>'
    + `${treeHtml(all, clean, true)}</div>`;
  // a fejléc HEAD-chipje (a worktree / ág), másolatként: itt nem gomb
  const chip = /** @type {HTMLElement} */ (document.getElementById('headChip')?.cloneNode(true));
  if (chip) {
    chip.removeAttribute('id');
    chip.querySelectorAll('[id]').forEach(x => x.removeAttribute('id'));
    chip.tabIndex = -1;
    el.querySelector('.fv-chip').replaceWith(chip);
  }
  document.body.append(el);
  document.body.classList.add('fv-on');
  fv = { ...newTree(el, sha, all, clean), plain: Boolean(o.plain), key: null, find: '', borrowed: o.borrowed ?? null };
  el.addEventListener('click', onFullClick);
  el.querySelector('.fv-search input').addEventListener('input', e => onQuery(fv, /** @type {HTMLInputElement} */ (e.target).value));
  const find = /** @type {HTMLInputElement} */ (el.querySelector('.fv-find input'));
  find.addEventListener('input', () => { fv.find = find.value; findInFile(0); });
  find.addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    findInFile(e.shiftKey ? -1 : 1);
  });
  el.querySelector('.fv-resize').addEventListener('pointerdown', onResize);
  fv.fit = new ResizeObserver(() => fv && fitHead());
  fv.fit.observe(el.querySelector('.fv-head'));
  addEventListener('keydown', onKey, true);
  if (all) loadTree(fv);
  renderCommits();
  selectFile(path, o.line ?? null);
  return true;
}

/* A fejléc keresője a nyitott fájl kódnézetében (`CodeDiff.find`); `dir`: 0 — a kurzortól, ±1 — lépés. */
function findInFile(dir) {
  codeViews.get(fv.key)?.find?.(fv.find, dir);
}

/* A commitlista: fent a saját worktree WIP sora (mindig), alatta a commit ágának commitjai — a HEAD
   őseié, ha a commit köztük van (vagy WIP sor), különben a commit őseié — közül a commit és fölötte, alatta
   `AROUND` szomszéd (a lista szélén a másik oldalról pótolva), fölöttük és alattuk a többi száma. A súgó
   a teljes commit message. */
function renderCommits() {
  const box = fv.el.querySelector('.fv-commits'), wt = focusWt();
  const wip = wt ? DATA.commits.filter(c => c.uncommitted && c.worktree === wt.slug) : [];
  const head = wt ? reachable([wt.head]) : null;
  const reach = head && (head.has(fv.sha) || wip.some(c => c.sha === fv.sha)) ? head : reachable([fv.sha]);
  const list = DATA.commits.filter(c => !c.uncommitted && reach.has(c.sha));
  const i = Math.max(0, list.findIndex(c => c.sha === fv.sha)), n = 2 * AROUND + 1;
  const from = Math.max(0, Math.min(i - AROUND, list.length - n)), to = Math.min(list.length, from + n);
  const more = k => (k ? `<div class="fv-more">még ${fmtInt(k)} commit</div>` : '');
  const item = c => {
    const tip = [c.subject, ...(c.body || '').split('\n').filter(l => l.trim())].join('\n');
    const sel = !fv.plain && c.sha === fv.sha;
    return `<div class="fv-commit${sel ? ' sel' : ''}" data-sha="${esc(c.sha)}" data-tip="${esc(tip)}"`
      + ` aria-selected="${sel}"><span class="subj">${esc(c.subject)}</span>`
      + `${c.uncommitted ? '' : `<span class="sha">${esc(c.short)}</span>`}</div>`;
  };
  box.innerHTML = wip.map(item).join('') + more(from) + list.slice(from, to).map(item).join('') + more(list.length - to);
}

/* Commitváltás a listán: a megnyitott fájl marad (akkor is, ha a commit nem változtatta); ha nincs
   megnyitott fájl, a commit első változott fájlja. A megnyitott kódnézet nem töltődik újra, helyben frissül:
   a nem mentett szöveg, a szerkesztő mód és a kinyitott rések maradnak (a panel új nézetet kap). */
function switchCommit(sha, plain = false) {
  if (!sha || (sha === fv.sha && plain === fv.plain) || !commitBySha(sha)) return;
  const changed = plain ? new Map() : changedFiles(sha);
  const path = fv.path || (changed.size ? changed.keys().next().value : fv.path);
  const keep = path && path === fv.path ? codeViews.get(fv.key) : null;
  if (keep) {
    codeViews.delete(fv.key);
    if (fv.borrowed) refillPanel();
  } else {
    const ed = editingDiff();
    if (ed && fv.el.contains(ed.root)) ed.stopEditing();
    dropView();
  }
  Object.assign(fv, { sha, plain, key: null, tree: null, loaded: new Set(), grep: null, clean: false, borrowed: null });
  if (plain) fv.all = true;
  const btn = fv.el.querySelector('.fv-diff');
  btn.disabled = false;
  btn.setAttribute('aria-pressed', String(!fv.all));
  if (fv.all) loadTree(fv);
  if (fv.query.startsWith('?')) onQuery(fv, fv.query);
  renderCommits();
  selectFile(path, null, keep);
  if (keep?.editing) keep.ed?.contentDOM.focus({ preventScroll: true });   // a lista kattintása elvitte
}

/* A fájl tartalma középen; `line`: ide görget (alapból az első változáshoz). `keep`: a commitváltáson
   átvitt élő kódnézet — nem épül új, nem görget, helyben frissül. */
function selectFile(path, line = null, keep = null) {
  if (!fv) return;
  if (!keep) {
    const ed = editingDiff();
    if (ed && fv.el.contains(ed.root)) ed.stopEditing();
    dropView();
  }
  fv.path = path;
  fv.key = `fv\n${fv.sha}\n${path}`;
  if (keep) codeViews.set(fv.key, keep);
  renderTree(fv);
  const box = fv.el.querySelector('.fv-box'), scroller = fv.el.querySelector('.fv-scroll');
  const f = pathHead();
  showPath(path);
  let scrolled = false;
  const key = fv.key;
  fileContent(box, fv.sha, path, key, fill => { if (fv?.key === key) fill(); }, {
    changed: Boolean(f.changed),
    retarget: Boolean(keep),
    ready: view => {
      if (keep || scrolled || fv?.key !== key) return;
      scrolled = true;
      if (fv.find && line == null) view.find?.(fv.find);
      // a kódnézet a saját görgetőjében (a teljes magasságot kitölti), a többi a doboz görgetőjében
      else view.scrollToLine(line ?? view.firstChange(), view.scrollEl?.() || scroller);
    },
  });
  if (line == null && !keep) scroller.scrollTop = 0;
}

/* Élő frissítés (a WIP sor új adata): a fák és a nyitott fájl újra (a kódnézet helyben frissül). */
/* A fejlécben a fájl: ikon, út, mellette a commit +/−-a és a WIP kék / narancs számai (a fa sora szerint). */
function pathHead() {
  const head = fv.el.querySelector('.fv-path'), path = fv.path;
  const icon = (fv.tree || side?.tree)?.files.find(x => x.path === path)?.icon;
  const f = (fv.plain ? null : changedFiles(fv.sha).get(path)) || { path, icon };
  head.innerHTML = `${fileIcon(f)}<span class="path">${esc(path)}</span>${churn(f, fv.wip?.get(path))}`;
  head.classList.toggle('deleted', f.status === 'D');
  fitHead();
  return f;
}

/* Ha a fájl útja nem fér ki a fejlécben, a HEAD-chip eltűnik (`tight`): az út fontosabb. */
function fitHead() {
  const head = fv.el.querySelector('.fv-head'), path = head.querySelector('.fv-path .path');
  head.classList.remove('tight');
  if (path && path.scrollWidth > path.clientWidth) head.classList.add('tight');
}

export function refreshFull() {
  if (side) {
    retarget();
    if (side.all && side.sha?.startsWith('*')) loadTree(side);
  }
  if (!fv) return;
  const wt = focusWt();
  // a kijelölt WIP sor eltűnt (a munkakönyvtár újra tiszta): a nézet helyben a worktree állapotára vált
  if (!commitBySha(fv.sha) && fv.sha.startsWith('*') && wt && commitBySha(wt.head)) { switchCommit(wt.head, true); return; }
  if (!commitBySha(fv.sha)) return;
  // commit nélkül (tiszta worktree) a nézetben szerkesztett fájl mentése után megjelent WIP sor kijelölődik:
  // a nézet helyben arra vált (a szerkesztés marad)
  const wip = fv.plain && !fv.sha.startsWith('*') && codeViews.get(fv.key)?.wrote && wt
    && DATA.commits.find(c => c.uncommitted && c.worktree === wt.slug && c.sha.startsWith('*uncommitted:'));
  if (wip) { switchCommit(wip.sha); return; }
  // commit nélkül a fa a worktree mostani állapotát követi: a megjelent WIP sort, vagy újra a HEAD-et
  if (fv.plain && wt && plainSha(wt) !== fv.sha && commitBySha(plainSha(wt))) { switchCommit(plainSha(wt), true); return; }
  if (fv.all && fv.sha.startsWith('*')) loadTree(fv);
  renderTree(fv);
  renderCommits();
  pathHead();
  const box = fv.el.querySelector('.fv-box'), key = fv.key;
  const f = fv.plain ? null : changedFiles(fv.sha).get(fv.path);
  fileContent(box, fv.sha, fv.path, key, fill => { if (fv?.key === key) fill(); }, { changed: Boolean(f?.changed) });
}

function closeFull() {
  if (!fv) return;
  const { sha, path, el } = fv;
  const ed = editingDiff();
  if (ed && el.contains(ed.root)) ed.stopEditing();
  dropView();
  fv.fit.disconnect();
  el.remove();
  document.body.classList.remove('fv-on');
  fv = null;
  showPath(null);
  removeEventListener('keydown', onKey, true);
  const f = expanded === sha && panelFile(path);
  if (!f) return;
  if (f.getAttribute('aria-expanded') === 'true') revealFile(f);
  else toggleFile(f, sha, true);
}

function onFullClick(e) {
  const t = /** @type {HTMLElement} */ (e.target);
  if (t.closest('[data-fv-close]')) { closeFull(); return; }
  const commit = /** @type {HTMLElement} */ (t.closest('.fv-commit'));
  if (commit) {
    // a kijelölt commitra kattintva, WIP sor nélkül, a kijelölés lekerül: a worktree állapota (`plain`)
    const wt = focusWt();
    if (commit.dataset.sha !== fv.sha || fv.plain) switchCommit(commit.dataset.sha);
    else if (wt && !DATA.commits.some(c => c.uncommitted && c.worktree === wt.slug)) switchCommit(wt.head, true);
    return;
  }
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
    } else if (t.closest?.('.fv-find') && fv.find) {
      /** @type {HTMLInputElement} */ (t).value = '';
      fv.find = '';
      findInFile(0);
    } else closeFull();
    return;
  }
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'f' && !e.shiftKey && !e.altKey) {   // a fejléc keresője
    e.preventDefault();
    e.stopImmediatePropagation();
    const input = /** @type {HTMLInputElement} */ (fv.el.querySelector('.fv-find input'));
    input.focus();
    input.select();
    return;
  }
  if (!t.closest?.('.cm-editor, input, textarea')) e.stopImmediatePropagation();   // a lap navigációja áll
}
