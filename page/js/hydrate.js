/* Adatcserekor újraszámolandó: a fejléc, a saját worktree chipje, a gráf szélessége. */
import { hydrateAvatars } from './avatars.js';
import { headChip } from './dom.js';
import { sizeGraph } from './graph.js';
import { icon } from './icons.js';
import { fitChrome } from './layout.js';
import { computeFresh, computeOwn, focusAuto, focusWt, worktrees, wtColor } from './model.js';
import { distText, wtChipInner, wtTrack } from './refs.js';
import { render } from './rows.js';
import { DATA } from './state.js';
import { esc, ghLink } from './util.js';

/* A repónév olvasható alakja a fejlécbe: `git-graph` → `Git Graph`. */
const displayName = name => name.split(/[-_.\s]+/).filter(Boolean)
  .map(w => w[0].toUpperCase() + w.slice(1)).join(' ');

/* Minden, ami a DATA-ból származik és adatcserekor újraszámolandó. */
export function hydrate() {
  computeFresh(render);
  sizeGraph();
  document.getElementById('repoName').textContent = displayName(DATA.meta.repo);
  hydrateFocus();
  const base = DATA.meta.repoUrl;
  document.getElementById('footLinks').innerHTML = base
    ? ghLink(`${base}/issues`, icon('issue'), 'mini', 'Issue-k a GitHubon')
      + ghLink(`${base}/pulls`, icon('pr'), 'mini', 'Pull requestek a GitHubon')
      + ghLink(base, icon('github'), 'mini', 'A repó a GitHubon') : '';
  fitChrome();                // a repó- és ágnév hossza dönt a kompakt fejlécről
  hydrateAvatars();
}

export function hydrateFocus() {
  const wts = worktrees(), own = focusWt();
  const chip = headChip;
  // A fejléc chipje a saját ág gráfbeli színét viseli; worktree-ben a worktree-ikonnal,
  // az előnnyel és — ha van commitolatlan változás — üres karikával, mint az ál-sor pontja.
  chip.style.setProperty('--lc', (own && wtColor(own)) || 'var(--accent)');
  chip.innerHTML = own ? wtChipInner(own) : icon('branch') + esc(DATA.meta.head || '');
  chip.hidden = !(own || DATA.meta.head);
  chip.dataset.tip = !own ? '' : (own.main ? 'fő checkout: ' : 'worktree: ') + own.path
    + (wts.length < 2 ? ''
      : focusAuto?.known ? '\naz előtérben lévő session itt dolgozik'
      : '\nnincs ismert session a repóban — a fő checkout')
    + distText(own.branch || '', wtTrack(own));
  computeOwn();
}
