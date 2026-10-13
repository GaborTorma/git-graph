/* ── Billentyűzetes navigáció ─────────────────────────────────────────────
   A kijelölés a billentyűzet-fókusz (sor- és fájl-elem), így az élő
   adatcsere után is visszaáll (`render`).
   Commit-szint:  ↑/↓ kijelölés (nem nyit), → kinyit és belép a fájlokba,
                  ← / Esc becsuk; ⌘/Ctrl+↓/↑ szülő / gyerek ugyanazon az ágon,
                  Shift-tel merge-nél a másik ág; H a HEAD (a ⌘H az appot rejti)
   Fájl-szint:    ↑/↓ a fájlokon, → kinyitja a diffet, ← becsukja; bezárt
                  fájlon ← vissza a commitra.
   Beviteli mezőben és nyitott menünél a billentyűk a saját dolgukat végzik. */
import { closeCommit, open } from './details.js';
import { toggleFile } from './diff.js';
import { OPEN_PANEL, rowsEl, scroller } from './dom.js';
import { commitBySha, focusWt } from './model.js';
import { nextFile } from './panel.js';
import { STEP_TOP, rowOf, select } from './scroll.js';
import { DATA, expanded, visible } from './state.js';
import { menuOpen } from './util.js';

/* Egy nyitott fájl blokkjai — csak a látható nézetéé (egymás alatti vagy
   side-by-side, a szélesség dönt). Bezárt fájlnál üres. */
const hunksOf = fileEl => fileEl?.getAttribute('aria-expanded') === 'true'
  ? [...fileEl.nextElementSibling.querySelectorAll('.hunk')].filter(h => h.offsetParent !== null) : [];
/* Fájl kinyitása után a kijelölés az első blokkra lép — ha a diff még
   töltődik, megvárja (legfeljebb 3 mp), amíg megjelenik. Ha közben máshová
   lépett a kijelölés, nem rántja vissza. */
function enterFirstHunk(fileEl) {
  const go = () => {
    const first = hunksOf(fileEl)[0];
    if (first && document.activeElement === fileEl) select(first);
    // kész: van blokk, vagy végleges üzenet jött (bináris, üres, hiba) — a betöltésre vár
    return Boolean(first) || fileEl.nextElementSibling.querySelector('.diff-note:not(.loading)') !== null;
  };
  if (go()) return;
  const box = fileEl.nextElementSibling;
  const obs = new MutationObserver(() => { if (go()) obs.disconnect(); });
  obs.observe(box, { childList: true, subtree: true });
  setTimeout(() => obs.disconnect(), 3000);
}
/* A nyitott commit alatti commit sora — az utolsó fájlról / blokkról lefelé ide lép. */
const belowCommit = () => {
  const i = visible.findIndex(c => c.sha === expanded);
  return i < 0 ? null : rowOf(visible[i + 1]);
};

const commitOf = el => el && visible.find(c => c.sha === el.dataset.sha);

function selectCommit(c) {
  return Boolean(c && visible.includes(c)) && select(rowOf(c));   // szűrve: nem látszik
}

function topVisible() {
  // Görgetés nélkül a legfelső sor 4 px-re van (nincs fölötte ragadós fejléc).
  const top = scroller.getBoundingClientRect().top + (scroller.scrollTop > 0 ? STEP_TOP : 0) - 1;
  const row = [...rowsEl.querySelectorAll('.row')].find(r => r.getBoundingClientRect().top >= top);
  return row && visible.find(c => c.sha === row.dataset.sha);
}
function relative(c, dir, other) {
  if (dir > 0) {                                    // lefelé: szülő
    const p = other ? c.parents[1] : c.parents[0];
    return p && commitBySha(p);
  }
  return DATA.commits.find(x => other ? x.parents.slice(1).includes(c.sha) : x.parents[0] === c.sha);
}
document.addEventListener('keydown', e => {
  if (e.altKey || /** @type {HTMLElement} */ (e.target).closest('input, textarea, .menu-pop')
      || menuOpen()) return;
  const active = document.activeElement;
  const hunk = active?.closest?.('.hunk');
  const file = !hunk && active?.closest?.('.file');
  const row = !hunk && !file && active?.closest?.('.row');
  const cur = commitOf(row);
  const k = e.key, mod = e.metaKey || e.ctrlKey;
  let handled = true;

  if (e.shiftKey && !mod && (k === 'ArrowDown' || k === 'ArrowUp')) {   // ── csak görget, a kijelölés marad
    scroller.scrollTop += (k === 'ArrowDown' ? 1 : -1) * SHIFT_SCROLL;
  } else if (hunk) {                                     // ── blokk-szint (nyitott diff)
    const fileEl = hunk.closest('.diff').previousElementSibling;
    const blocks = hunksOf(fileEl), i = blocks.indexOf(hunk);
    if (k === 'ArrowDown' || k === 'ArrowRight') select(blocks[i + 1] || nextFile(fileEl));   // az utolsó fájl utolsó blokkján marad
    else if (k === 'ArrowUp') select(blocks[i - 1] || fileEl);
    else if (k === 'ArrowLeft') { toggleFile(fileEl, expanded, false); select(fileEl); }   // bezárja a fájlt
    else handled = false;
  } else if (file) {                                     // ── fájl-szint
    const files = [...file.parentElement.querySelectorAll('.file')];
    const isOpen = file.getAttribute('aria-expanded') === 'true';
    const prev = files[files.indexOf(file) - 1];
    if (k === 'ArrowDown') select((isOpen && hunksOf(file)[0]) || nextFile(file) || belowCommit());
    else if (k === 'ArrowUp') select((prev && hunksOf(prev).at(-1)) || prev || rowOf(visible.find(c => c.sha === expanded)));
    else if (k === 'ArrowRight' && !isOpen) { toggleFile(file, expanded, true); enterFirstHunk(file); }
    else if (k === 'ArrowRight') enterFirstHunk(file);          // már nyitva: az első blokkra
    else if (k === 'ArrowLeft' && isOpen) toggleFile(file, expanded, false);
    else if (k === 'ArrowLeft') select(rowOf(visible.find(c => c.sha === expanded)));
    else handled = false;
  } else if ((k === 'ArrowDown' || k === 'ArrowUp') && mod) {   // ── ág mentén
    handled = Boolean(cur) && (selectCommit(relative(cur, k === 'ArrowDown' ? 1 : -1, e.shiftKey)) || true);
  } else if ((k === 'ArrowDown' || k === 'ArrowUp') && !e.shiftKey) {
    handled = cur ? (selectCommit(visible[visible.indexOf(cur) + (k === 'ArrowDown' ? 1 : -1)]) || true)
                  : selectCommit(topVisible());
  } else if (k === 'ArrowRight' && cur) {                 // belép: kinyit, első fájl
    if (expanded !== cur.sha) open(cur.sha, true);
    const first = document.querySelector(`${OPEN_PANEL} .file`);
    if (first) select(first); else select(rowOf(cur));
  } else if (k === 'ArrowLeft' && cur && expanded === cur.sha) {
    closeCommit();
  } else if ((k === 'h' || k === 'H') && !mod) {
    const isHead = r => r.kind === 'head' || r.kind === 'detached';
    const own = focusWt()?.slug;
    handled = selectCommit(visible.find(c => c.refs.some(r => isHead(r) && r.worktree === own))
      || visible.find(c => c.refs.some(isHead)));
  } else {
    handled = false;
  }
  if (handled) e.preventDefault();
});

const SHIFT_SCROLL = 54;   // Shift+↑/↓: három diff-sornyit görget (a kijelölés marad)
