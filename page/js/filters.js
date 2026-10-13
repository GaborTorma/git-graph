/* Szűrők: ágválasztás, keresés, csak ref-es commitok, remote ágak. */
import { branchBtn, branchPop, branchQuery, branchSel, fillBranches, filterBranches, setBranchSel } from './branches.js';
import { headChip, rowsEl } from './dom.js';
import { hydrateFocus } from './hydrate.js';
import { makeMenu } from './menu.js';
import { ancestryOf, focusWt, headFiltered, localReach, remoteRefs, remotesOn, worktrees } from './model.js';
import { render } from './rows.js';
import { revealSha, scrollToSha } from './scroll.js';
import { DATA, expanded, setBranchKeep, setVisible, visible } from './state.js';
import { fold, menuOpen, queryWords } from './util.js';

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
/* A pipára kattintás csak azt a sort veszi ki vagy teszi be, a menü nyitva marad
   (a makeMenu kattintás-kezelője elé, rögzítő fázisban). */
branchPop.addEventListener('click', e => {
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

function matches(c, words) {
  if (!words.length) return true;
  const hay = fold([c.subject, c.body, c.author, c.email, ...c.refs.map(r => r.name)].join('\n'));
  return words.every(w => hay.includes(w) || c.sha.startsWith(w));
}

export function applyFilters() {
  const branch = branchSel.size ? branchSel : null;
  const remotes = remotesOn();
  const refsOnly = /** @type {HTMLInputElement} */ (document.getElementById('onlyRefs')).checked;
  const words = queryWords(searchEl.value);
  const keep = branch ? ancestryOf(branch) : null;
  setBranchKeep(keep);
  const local = remotes ? null : localReach();

  setVisible(DATA.commits.filter(c => {
    // Állapot, nem commit: keresésnél nem kell; ágszűrésnél csak annak a worktree-nek
    // a WIP-je, amelyikben a szűrt ág van kivéve — leválasztott HEAD-nél az app szerinti
    // ága (`appBranch`) —, nem elég, hogy a HEAD-je rajta van.
    if (c.uncommitted) {
      return !words.length && (!branch || worktrees().some(w => w.slug === c.worktree && branch.has(w.branch || w.appBranch)));
    }
    if (keep && !keep.has(c.sha)) return false;
    // Remote ágak nélkül a helyi történet minden commitja marad (csak a remote-badge
    // tűnik el); ami csak remote ágból érhető el, az kimarad.
    if (local && !local.has(c.sha)) return false;
    if (refsOnly && !c.refs.some(r => remotes || r.kind !== 'remote')) return false;
    return matches(c, words);
  }));
  render();
}
document.getElementById('onlyRefs').addEventListener('change', applyFilters);
// A remote-kapcsoló a fejléc chipjét is érinti (a ☁ szakasz).
document.getElementById('showRemotes').addEventListener('change', () => {
  // Remote ágak nélkül a kijelölt remote refek is kiesnek (üresen: minden ág).
  if (!remotesOn()) for (const r of remoteRefs()) branchSel.delete(r);
  hydrateFocus(); fillBranches(); applyFilters();
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
  if (cleared) revealExpanded();
});

/* ⌘F / Ctrl+F a keresőbe (a lap saját keresője helyett); Escape előbb a
   keresést üríti, aztán a kinyitott commitot csukja be. */
document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'f') {
    e.preventDefault();
    searchEl.focus();
    searchEl.select();
  } else if (e.key === 'Escape' && searchEl.value
             && !menuOpen()) {   // nyitott menüt a menü csuk
    e.stopImmediatePropagation();
    e.preventDefault();
    searchEl.value = '';
    lastQuery = '';
    applyFilters();
    revealExpanded();
  }
}, true);
