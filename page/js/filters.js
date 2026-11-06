/* Szűrők: ágválasztás, remote-ok (az ágválasztó fejlécein), keresés és csak ref-es commitok (a
   keresés lenyílójában). */
import { branchBtn, branchPop, branchQuery, branchSel, fillBranches, filterBranches, setBranchSel } from './branches.js';
import { headChip, rowsEl } from './dom.js';
import { hydrateFocus } from './hydrate.js';
import { makeMenu } from './menu.js';
import { icon } from './icons.js';
import { ancestryOf, anyRemoteHidden, focusWt, headFiltered, localReach, remoteRefs, remoteShown, toggleRemote, worktrees } from './model.js';
import { render } from './rows.js';
import { revealSha, scrollToSha } from './scroll.js';
import { DATA, expanded, setBranchKeep, setQuery, setVisible, visible } from './state.js';
import { esc, fold, menuOpen, queryWords } from './util.js';

makeMenu(branchBtn, branchPop, o => {
  setBranchSel(o.dataset.refs.split(' ').filter(Boolean));
  fillBranches();
  applyFilters();
  // A választás után a lista a kijelölés legfelső sorához ugrik — a csúcsai és a worktree-jük
  // listabeli WIP-sora közül —; „Minden ág”-nál a saját HEAD-hez.
  if (!branchSel.size) { revealHead(); return; }
  const shas = new Set(visible.filter(c => c.uncommitted || c.refs.some(r => branchSel.has(r.name))).map(c => c.sha));
  revealSha([...rowsEl.querySelectorAll('.row')].find(r => shas.has(r.dataset.sha))?.dataset.sha);
}, () => {
  // Üres szűrővel nyílik; a teljes lista szélessége marad, szűréskor nem ugrik össze.
  branchQuery.value = '';
  filterBranches();
  branchPop.style.minWidth = '';      // a természetes szélesség méréséhez
  branchPop.style.minWidth = `${branchPop.offsetWidth}px`;
  branchQuery.focus();
});
/* Az ágválasztó x-e (kijelölésnél a nyíl helyén) „Minden ág”-ra áll vissza, a menüt nem nyitja (a
   makeMenu nyitása előtt, rögzítő fázisban). */
branchBtn.addEventListener('click', e => {
  if (!(/** @type {HTMLElement} */ (e.target).closest('#branchX'))) return;
  e.stopPropagation();
  setBranchSel([]);
  fillBranches();
  applyFilters();
  revealHead();
}, true);
/* A pipára kattintás csak azt a sort veszi ki vagy teszi be; a remote fejlécének kapcsolója a
   remote-ot rejti vagy mutatja. A menü mindkettőnél nyitva marad (a makeMenu kattintás-kezelője
   elé, rögzítő fázisban). */
branchPop.addEventListener('click', e => {
  const sw = /** @type {HTMLElement} */ (e.target).closest('.rsw[data-remote]');
  if (sw) {
    e.stopPropagation();
    toggleRemote(sw.dataset.remote);
    remotesChanged();
    branchPop.querySelector(`.rsw[data-remote="${CSS.escape(sw.dataset.remote)}"]`)?.focus();
    return;
  }
  const c = /** @type {HTMLElement} */ (e.target).closest('.ckc[data-refs]');
  if (!c) return;
  e.stopPropagation();
  const refs = c.dataset.refs.split(' ');
  const on = refs.every(r => branchSel.has(r));
  for (const r of refs) on ? branchSel.delete(r) : branchSel.add(r);
  const key = c.closest('.option')?.dataset.key;
  fillBranches();
  applyFilters();
  branchPop.querySelector(`.option[data-key="${CSS.escape(key || '')}"]`)?.focus();
}, true);

/* Keresés: minden szó (szóközzel elválasztva) szerepeljen a commit
   üzenetében, törzsében, szerzőjében, e-mail-címében, ref-neveiben — vagy a
   hash eleje legyen. Kis- és nagybetű, ékezet nem számít. */
const searchEl = /** @type {HTMLInputElement} */ (document.getElementById('search'));
const searchBtn = document.getElementById('searchBtn');
const searchPop = document.getElementById('searchPop');
const onlyRefs = document.getElementById('onlyRefs');
const refsOnly = () => onlyRefs.getAttribute('aria-checked') === 'true';

function matches(c, words) {
  if (!words.length) return true;
  const hay = fold([c.subject, c.body, c.author, c.email, ...c.refs.map(r => r.name)].join('\n'));
  return words.every(w => hay.includes(w) || c.sha.startsWith(w));
}

export function applyFilters() {
  const branch = branchSel.size ? branchSel : null;
  const words = queryWords(searchEl.value);
  setQuery(words);
  const keep = branch ? ancestryOf(branch) : null;
  setBranchKeep(keep);
  const local = anyRemoteHidden() ? localReach() : null;
  const refs = refsOnly();

  setVisible(DATA.commits.filter(c => {
    // Állapot, nem commit: keresésnél nem kell; ágszűrésnél csak annak a worktree-nek
    // a WIP-je, amelyikben a szűrt ág van kivéve — leválasztott HEAD-nél az app szerinti
    // ága (`appBranch`) —, nem elég, hogy a HEAD-je rajta van.
    if (c.uncommitted) {
      return !words.length && (!branch || worktrees().some(w => w.slug === c.worktree && branch.has(w.branch || w.appBranch)));
    }
    // A stash nem őse semminek: ágszűrésnél akkor marad, ha a saját ága (`branch`) a
    // szűrtek közt van, és a bázisa is látszik (különben az éle a semmibe futna).
    if (c.stash && keep) {
      if (!branch.has(c.branch) || !keep.has(c.parents[0])) return false;
    } else if (keep && !keep.has(c.sha)) return false;
    // A rejtett remote-ok nélkül a helyi történet minden commitja marad (csak a remote-badge
    // tűnik el); ami csak rejtett remote ágból érhető el, az kimarad.
    if (local && !local.has(c.sha)) return false;
    if (refs && !c.refs.some(r => r.kind !== 'remote' || remoteShown(r.name))) return false;
    return matches(c, words);
  }));
  render();
}
/* A remote kapcsolója a fejléc chipjét is érinti (a ☁ szakasz). A nem látható remote refek a
   kijelölésből is kiesnek (üresen: minden ág). */
function remotesChanged() {
  for (const r of remoteRefs()) if (!remoteShown(r)) branchSel.delete(r);
  hydrateFocus(); fillBranches(); applyFilters();
}

/* A keresés gombja: szűrő nélkül egy ikon; szűrve akcentus színű, és kiírja a szűrést (a keresett
   szöveg, ~160 px-nél „…”, a ref-szűrő címke-ikonja), a végén x — az mindkét szűrőt törli, a
   popupot nem nyitja. Kattintásra (⌘F) lenyílik: fent a keresőmező, alatta a ref-kapcsoló. */
function searchView() {
  const q = searchEl.value.trim(), refs = refsOnly(), on = Boolean(q || refs);
  const part = (name, html, cls = '') => `<span class="sb-part${cls}" data-part="${name}">${html}</span>`;
  const html = part('search', icon('search', 'ic', 'md'))   // a ghost gomb ikonja 20 px (`md`)
    + (q ? part('query', esc(q), ' search-q') : '')
    + (refs ? part('tag', icon('tag', 'ic', 'md')) : '')
    + (on ? `<span class="sb-part clear-x" id="searchX" data-part="clear" role="button" aria-label="Szűrés törlése"`
      + ` data-tip="Szűrés törlése">${icon('close')}</span>` : '');
  searchBtn.classList.toggle('filtered', on);
  searchBtn.setAttribute('aria-label', `Commitok keresése${q ? `: ${q}` : ''}${refs ? ' · csak ref-es commitok' : ''}`);
  if (searchBtn.innerHTML !== html) searchBtn.innerHTML = html;
}
/* A keresés törlése (az Esc); `refs`: a ref-szűrő is (az x). A kinyitott commit a lista tetejére. */
function clearSearch(refs = false) {
  searchEl.value = '';
  lastQuery = '';
  if (refs) onlyRefs.setAttribute('aria-checked', 'false');
  applyFilters();
  searchView();
  revealExpanded();
}
searchView();
makeMenu(searchBtn, searchPop, o => {
  o.setAttribute('aria-checked', String(!refsOnly()));
  applyFilters();
  searchView();
}, () => { searchEl.focus(); searchEl.select(); });
/* Az x (a gombon belül, a makeMenu nyitása előtt, rögzítő fázisban). */
searchBtn.addEventListener('click', e => {
  if (!(/** @type {HTMLElement} */ (e.target).closest('#searchX'))) return;
  e.stopPropagation();
  clearSearch(true);
}, true);
/* A mező billentyűi (a makeMenu kezelője előtt): az Esc előbb a keresett szöveget törli (a
   ref-szűrő marad, a popup nyitva), üres mezőben a popupot zárja; Enter bezárja a popupot (a
   szűrés marad); Home/End a kurzort mozgatja. */
searchEl.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    e.preventDefault();                 // a keresőmező natív Esc-törlése helyett
    if (searchEl.value) { e.stopPropagation(); clearSearch(); }
  } else if (e.key === 'Enter') {
    e.preventDefault();
    searchBtn.click();
    searchBtn.focus();
  } else if (e.key === 'Home' || e.key === 'End') e.stopPropagation();
});

/* A fejléc chipjére kattintva a saját HEAD commitjához; ha az ágválasztó elrejti, előbb
   minden ágra áll vissza. */
const revealHead = () => revealSha(focusWt()?.head);
headChip.addEventListener('click', () => {
  if (headFiltered()) {
    setBranchSel([]);
    fillBranches();
    applyFilters();
  }
  revealHead();
});
/* A keresés törlésekor (Escape, a mező ×-e vagy kitörölt szöveg) a szűrés
   megszűnik; ha van kinyitott commit, az a lista tetejére kerül (a napfejléc
   alá), hogy a visszajött sorok közt se vesszen el. */
let lastQuery = '';
const revealExpanded = () => scrollToSha(expanded);
searchEl.addEventListener('input', () => {
  const cleared = lastQuery && !searchEl.value;
  lastQuery = searchEl.value;
  applyFilters();
  searchView();
  if (cleared) revealExpanded();
});

/* ⌘F / Ctrl+F a keresés popupját nyitja, a keresőbe (a lap saját keresője helyett); zárt
   popupnál az Escape előbb a keresett szöveget üríti (a ref-szűrő marad), aztán a kinyitott
   commitot csukja be. A kódnézetben (CodeMirror) a
   billentyűk az övéi: a ⌘F a fájlban keres, az Esc a szerkesztést zárja. */
document.addEventListener('keydown', e => {
  if (/** @type {HTMLElement} */ (e.target).closest?.('.cm-editor')) return;
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'f') {
    e.preventDefault();
    if (searchPop.hidden) searchBtn.click();      // a nyitás a mezőbe teszi a fókuszt
    else { searchEl.focus(); searchEl.select(); }
  } else if (e.key === 'Escape' && searchEl.value
             && !menuOpen()) {   // nyitott menüt a menü csuk
    e.stopImmediatePropagation();
    e.preventDefault();
    clearSearch();
  }
}, true);
