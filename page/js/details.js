/* A commit-részletek panelje: nyitás, csukás, kattintások a listában. */
import { glide, grow, shrink } from './anim.js';
import { avatarOf } from './avatars.js';
import { fmtDate } from './dates.js';
import { mdRaw, openFiles, setMdRaw, setSvgCode, svgCode, toggleFile } from './diff.js';
import { OPEN_PANEL, pendingEl, rowsEl, scroller } from './dom.js';
import { drawGraph } from './graph.js';
import { fileIcon, icon } from './icons.js';
import { fitWho } from './layout.js';
import { commitBySha } from './model.js';
import { fitPanel, followPending, revealCommit } from './panel.js';
import { commitUrl, fileUrl, linkify } from './refs.js';
import { rowOf, select } from './scroll.js';
import { DATA, expanded, setExpanded, visible } from './state.js';
import { esc, fileCount, fmtBytes, fmtInt, ghLink, menuOpen } from './util.js';

// A bináris fájl mérete (`size`: [régi, új], a hiányzó oldal `null`): az új +méret, a
// törölt −méret, a változott az előjeles különbség (±0 B semleges); méret nélkül `bin`.
const sizeHtml = size => {
  if (!size || (size[0] == null && size[1] == null)) return '<span class="tag">bin</span>';
  const d = (size[1] ?? 0) - (size[0] ?? 0);
  return d > 0 ? `<span class="a">+${fmtBytes(d)}</span>` : d < 0 ? `<span class="d">−${fmtBytes(-d)}</span>`
    : '<span class="tag">±0 B</span>';
};

// A fájl útja: a mappa halványabban, a fájlnév teljes színnel.
// A `from` utáni mappa-előtag új / törölt (`dirFrom`): a fájlnévvel együtt színes.
const pathHtml = (path, from = Infinity) => {
  const i = path.lastIndexOf('/') + 1;
  const j = Math.min(from, i);
  return ((j ? `<span class="dir">${esc(path.slice(0, j))}</span>` : '')
    + (j < i ? `<span class="dir-st">${esc(path.slice(j, i))}</span>` : '') + esc(path.slice(i)))
    .replaceAll(' =&gt; ', ' <span class="rename-arrow">»</span> ');   // a `--numstat` átnevezés-nyila
};

/* Összevont követetlen mappa (pl. `node_modules/`): egy sor a fájlszámával, diff nélkül. */
const dirHtml = f => `<div class="file-dir"><span></span>${icon('folder', 'ic fic')}
  <span class="path added">${pathHtml(f.path, f.dirFrom)}</span>
  <span class="churn">${fmtInt(f.count)} fájl</span><span></span></div>`;

const miniBtn =(name, label, attrs = '') =>
  `<button class="mini" type="button" aria-label="${esc(label)}" title="${esc(label)}" ${attrs}>${icon(name)}</button>`;

/* Változásjelölő: 6 szegmens, a hozzáadás / törlés arányában. */
function bars(f) {
  const total = f.add + f.del;
  if (!total) return '';
  const a = Math.round(6 * f.add / total);
  return `<span class="bars" aria-hidden="true">${Array.from({ length: 6 },
    (_, i) => `<i class="${i < a ? 'a' : 'd'}"></i>`).join('')}</span>`;
}

function headHtml(c) {
  if (c.uncommitted) return '';   // a WIP-nek nincs szerzője, dátuma; a szülője a HEAD, a gráf mutatja
  const avatar = avatarOf(c);
  const who = `${avatar ? `<img src="${esc(avatar)}" alt="${esc(c.author)}">` : ''}<span class="name">${esc(c.author)}</span>`
      + `<span class="sep">·</span><span>${fmtDate(c.date)}</span>`;
  const parents = c.parents.map(p => `<button type="button" class="hash" data-jump="${p}" title="Ugrás a szülőre">${p.slice(0, 7)}</button>`
    + miniBtn('open', `Szülő megnyitása: ${p.slice(0, 7)}`, `data-jump="${p}"`)).join('');
  const parentChip = c.parents.length ? `<span class="chip" title="Szülő${c.parents.length > 1 ? 'k' : ''}">`
    + `${icon('parent')}${parents}</span>` : '';
  const commitChip = '<span class="chip">'
    + `<span class="hash plain">${c.short}</span>`
    + (c.pushed ? ghLink(commitUrl(c), icon('open'), 'mini', 'Commit megnyitása a GitHubon') : '')
    + miniBtn('copy', 'Hash másolása', `data-copy="${c.sha}"`) + '</span>';
  return `<div class="d-head"><span class="who">${who}</span><span class="chips">${parentChip}${commitChip}</span></div>`;
}

/* A hosszú commit-üzenetből elsőre csak az eleje látszik (szóhatáron vágva), a
   többi a „több” gombra nyílik le; a lenyitott üzenet újrarajzolás után is nyitva marad. */
const BODY_MAX = 200, BODY_SLACK = 40;
const fullBodies = new Set();
function bodyHtml(c) {
  if (c.body.length <= BODY_MAX + BODY_SLACK || fullBodies.has(c.sha)) return linkify(c.body);
  const cut = c.body.slice(0, BODY_MAX);
  const head = cut.slice(0, Math.max(cut.search(/\s\S*$/), BODY_MAX / 2)).trimEnd();
  return `${linkify(head)}… <button type="button" class="more" data-more>több</button>`;
}

export function open(sha, animate = false) {
  // A korábban nyitott panel felcsukódik (felhasználói nyitásnál), az új sor helyben marad.
  const row = document.querySelector(`.row[data-sha="${CSS.escape(sha)}"]`);
  const old = [...document.querySelectorAll(OPEN_PANEL)];
  for (const d of old) if (animate && row) d.classList.add('folding'); else d.remove();
  if (row?.nextElementSibling?.classList.contains('folding')) row.nextElementSibling.remove();   // újranyitás csukódás közben
  if (!row) return;
  document.querySelectorAll('.row').forEach(r => r.setAttribute('aria-expanded', 'false'));
  row.setAttribute('aria-expanded', 'true');

  const c = commitBySha(sha);
  const st = DATA.stats[sha] || { files: [], add: 0, del: 0 };

  const el = document.createElement('div');
  el.className = 'details';
  el.innerHTML = `
    ${headHtml(c)}
    ${c.body ? `<p class="body-text">${bodyHtml(c)}</p>` : ''}
    <div class="files">
      <div class="files-head">Fájlok<span class="n">${fmtInt(fileCount(st))}</span>
        <span class="a" style="color:var(--add)">+${st.add}</span>
        <span class="d" style="color:var(--del)">−${st.del}</span></div>
      ${st.files.map(f => f.count ? dirHtml(f) : `<div class="file" tabindex="-1" data-path="${esc(f.path)}" aria-expanded="false">
        <span class="chev">${icon('chev')}</span>${fileIcon(f)}
        <span class="path${{ A: ' added', D: ' deleted' }[f.status] ?? ' modified'}">${pathHtml(f.path, f.dirFrom)}</span>
        <span class="churn">${f.bin ? sizeHtml(f.size)
          : `${f.add ? `<span class="a">+${f.add}</span>` : ''}${f.del ? `<span class="d">−${f.del}</span>` : ''}${bars(f)}`}</span>
        ${c.pushed ? ghLink(fileUrl(c, f), icon('open'), 'mini', 'Fájl megnyitása a GitHubon') : '<span></span>'}</div>
        <div class="diff" hidden></div>`).join('')}
      ${st.more ? `<div class="files-note">+${fmtInt(st.more)} további fájl</div>` : ''}
      ${st.ignored ? `<div class="files-note">${fmtInt(st.ignored)} fájl rejtve (.gitignore)</div>` : ''}
    </div>`;
  // Az ál-sor a fix sávban ül: a panelje is ott, a saját sora alatt (több
  // worktree WIP-je közül a megfelelő alatt), korlátozott magasságban.
  row.after(el);
  fitWho();
  // A korábban lenyitott fájlok nyitva maradnak (újrarajzolás, újranyitás) —
  // még a méretezés és a nézetbe ugrás előtt, hogy a teljes panellel számoljon.
  el.querySelectorAll('.file').forEach(f => {
    if (openFiles.has(sha + '\n' + f.dataset.path)) toggleFile(f, sha, true, animate ? 'commit' : false);
  });
  fitPanel();
  if (animate) {
    // A nézetbe hozás a végső elrendezésből számol (a régi panel nélkül), és
    // a felcsukódással együtt görget oda: közben sem görget túl és vissza.
    const listed = old.filter(d => scroller.contains(d));
    const from = scroller.scrollTop;
    for (const d of listed) d.style.display = 'none';
    revealCommit(el);
    const to = scroller.scrollTop;
    for (const d of listed) d.style.display = '';
    scroller.scrollTop = from;
    glide(scroller, to - from);
    for (const d of old) shrink(d, () => { d.remove(); drawGraph(); }, pendingEl.contains(d) ? followPending(el) : undefined);
  }
  setExpanded(sha);
  drawGraph();               // a panel alatti sorok lejjebb kerültek
  if (animate) grow(el);
}

/* A vágólap az Artifact keretében tiltott lehet: akkor a régi `execCommand`. */
async function copyText(text, btn) {
  try { await navigator.clipboard.writeText(text); }
  catch {
    const t = Object.assign(document.createElement('textarea'), { value: text });
    document.body.append(t); t.select();
    try { document.execCommand('copy'); } finally { t.remove(); }
  }
  btn.classList.add('done');
  btn.innerHTML = icon('check');
  setTimeout(() => { btn.classList.remove('done'); btn.innerHTML = icon('copy'); }, 1200);
}

function onListClick(e) {
  if (e.target.closest('a[href]')) return;   // GitHub-link: nyíljon, a sor ne csukódjon
  const copy = e.target.closest('[data-copy]');
  if (copy) { copyText(copy.dataset.copy, copy); return; }
  const md = e.target.closest('[data-md-mode]'), svg = e.target.closest('[data-svg-mode]');
  if (md) { if ((md.dataset.mdMode === 'raw') !== mdRaw) setMdRaw(!mdRaw); return; }
  if (svg) { if ((svg.dataset.svgMode === 'code') !== svgCode) setSvgCode(!svgCode); return; }
  const jump = e.target.closest('[data-jump]');
  if (jump) {
    const target = rowsEl.querySelector(`.row[data-sha="${jump.dataset.jump}"]`);
    if (target) open(jump.dataset.jump, true);   // mint a kattintás: animálva, a nézetbe hozva
    return;
  }
  const more = e.target.closest('[data-more]');
  if (more) {
    const c = commitBySha(expanded);
    fullBodies.add(c.sha);
    const panel = more.closest('.details'), body = more.parentElement;
    grow(body, () => { body.innerHTML = bodyHtml(c); }, () => revealCommit(panel, true));
    return;
  }
  const file = e.target.closest('.file');
  if (file) { toggleFile(file, expanded, file.getAttribute('aria-expanded') !== 'true'); return; }
  if (e.target.closest('.details')) return;   // a panelben kattintás ne csukja be
  const row = e.target.closest('.row');
  if (!row) return;
  if (row.getAttribute('aria-expanded') === 'true' && expanded) closeCommit(false);
  else open(row.dataset.sha, true);
}
rowsEl.addEventListener('click', onListClick);
pendingEl.addEventListener('click', onListClick);

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && expanded && !menuOpen()) closeCommit();
});

/* Bezárás felcsukással: a commit azonnal zárt (`expanded`), a panel a
   felcsukódás végén tűnik el. Ha közben újra kinyílik, az `open` már levette. */
export function closeCommit(focusRow = true) {
  const row = expanded && rowOf(visible.find(c => c.sha === expanded));
  const panel = document.querySelector(OPEN_PANEL);
  setExpanded(null);
  if (row && focusRow) select(row);
  if (!panel) { drawGraph(); return; }
  panel.classList.add('folding');
  shrink(panel, () => {
    if (!panel.isConnected) return;
    const own = /** @type {HTMLElement} */ (panel.previousElementSibling);
    panel.remove();
    if (own?.classList.contains('row') && own.dataset.sha !== expanded) own.setAttribute('aria-expanded', 'false');   // közben újra kinyílhatott
    drawGraph();
  });
}

/* A lista lefelé görgetése bezárja a fix sávban lenyitott saját WIP-panelt: a
   görgetés a listának szól, a panel csak a helyét foglalná. */
let lastScrollTop = 0;
scroller.addEventListener('scroll', () => {
  const panel = pendingEl.querySelector(OPEN_PANEL);
  if (scroller.scrollTop > lastScrollTop && panel) closeCommit(false);
  lastScrollTop = scroller.scrollTop;
}, { passive: true });
