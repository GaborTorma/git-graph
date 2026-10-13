/* A gráf (sávok, élek, pöttyök) az `#lanes` SVG-be, és a fix sáv WIP-sorai. */
import { pendingEl, rowsEl, scroller, svg } from './dom.js';
import { commitBySha, fade, focusWt, fresh, laneColor, tint } from './model.js';
import { DATA, visible } from './state.js';

const ROW_H = 30, LANE_W = 14, X0 = 16, DOT_R = 4;
const EDGE_HUG = DOT_R + 1;   // a sávváltó vonal ennyit fut a commit sávjában, mielőtt elfordul
const STUB_GAP = 11;   // több worktree-csonk pöttyei közti függőleges távolság

let graphW = 72;
/* A gráf-oszlop szélessége a sávok számából (a csonkokéval együtt); a CSS is ezt
   használja (`--graph-w`: a sorok bal paddingje, a panel margója). */
export function sizeGraph() {
  const laneCount = DATA.commits.reduce((m, c) => Math.max(m, c.lane, ...(c.stubs || []).map(t => t.lane)), 0) + 1;
  graphW = Math.max(32, X0 * 2 + (laneCount - 1) * LANE_W);
  document.documentElement.style.setProperty('--graph-w', graphW + 'px');
}

function laneX(l) { return X0 + l * LANE_W; }

/* A sorok Y-pozíciója a DOM-ból jön, nem sorszám × magasság: a napok fejléce
   és a kinyitott commit-panel az alattuk lévő sorokat lejjebb tolja, és a
   pöttyöknek velük kell menniük — közben a vonal egyszerűen hosszabb lesz. */
/* Az Uncommitted ál-sorok a lista FÖLÖTT, a fix `#pending` sávban ülnek: a
   pontjuk ott van, a szaggatott vonaluk innen, a lista teteje fölül (negatív
   Y, az SVG túllóghat) fut le a HEAD-ig. */
const WRAP_TOP = 4;                   // a .graph-wrap felső margója
export function drawGraph() {
  drawPending();
  const rowIndexBySha = new Map(visible.map((c, i) => [c.sha, i]));
  // A sor közepe: a kétsoros sor (`.two`) magasabb.
  const listRows = [...rowsEl.querySelectorAll('.row')];
  const midBySha = new Map(listRows.map(el => [el.dataset.sha, el.offsetTop + el.offsetHeight / 2]));
  const heightBySha = new Map(listRows.map(el => [el.dataset.sha, el.offsetHeight]));
  for (const el of pendingEl.querySelectorAll('.row')) {
    midBySha.set(el.dataset.sha, el.offsetTop + el.offsetHeight / 2 - pendingEl.offsetHeight - WRAP_TOP);
  }
  const rowY = i => midBySha.get(visible[i].sha) ?? i * ROW_H + ROW_H / 2;
  const h = Math.max(rowsEl.offsetHeight, visible.length * ROW_H);
  svg.setAttribute('width', graphW);
  svg.setAttribute('height', h);
  svg.setAttribute('viewBox', `0 0 ${graphW} ${h}`);

  // Az egyenesek előbb, a sávváltó vonalak felül: az elágazás a commit pöttyénél
  // is a saját színével indul, nem takarja el a sáv vonala.
  let out = '', bends = '';
  for (const e of DATA.edges) {
    const a = rowIndexBySha.get(DATA.commits[e.fromRow].sha);
    const b = rowIndexBySha.get(DATA.commits[e.toRow].sha);
    if (a === undefined || b === undefined) continue;   // szűrve
    const x1 = laneX(e.fromLane), y1 = rowY(a);
    const x2 = laneX(e.toLane),   y2 = rowY(b);
    // A vonal annak a sávnak a színét kapja, amelyikben a hossza nagy részén fut:
    // a merge-vonal rögtön a cél sávjába fordul, a leágazó csak a szülő fölött.
    const color = tint(DATA.commits[e.fromRow],
      laneColor(e.merge ? e.toLane : e.fromLane));
    // A munkakönyvtár még nem commit: szaggatva lóg a HEAD-re. Görgetve a sajátja
    // eltűnik, ha nincs alatta más WIP-sor, vagy ha a HEAD-je már a sáv alá csúszott
    // (`hideOwnEdge`); a többié látszik — különben nem tudni, hová tart.
    const from = DATA.commits[e.fromRow];
    const own = from.worktree === focusWt()?.slug ? ' own' : '';
    const dash = from.uncommitted ? ` class="pend-edge${own}" stroke-dasharray="3 3"` : '';
    const path = `<path d="${edgePath(x1, y1, x2, y2, e.merge)}" fill="none" stroke="${color}" stroke-width="2"${dash}/>`;
    if (x1 === x2) out += path; else bends += path;
  }
  out += bends;
  // A worktree csonkja: vonal a commitról a saját oszlopába, ott pötty. Több csonk
  // esetén a pöttyök a commit magassága körül, legyezőszerűen ágaznak le.
  visible.forEach((c, i) => {
    const stubs = c.stubs || [];
    if (!stubs.length) return;
    const y0 = rowY(i), x0 = laneX(c.lane), span = (heightBySha.get(c.sha) || ROW_H) - 8;
    // a pöttyök közepe a commit magassága, köztük legfeljebb STUB_GAP (a sor magasságán belül)
    const gap = Math.min(STUB_GAP, span / (stubs.length + 1));
    const ys = stubs.map((t, k) => y0 + (k - (stubs.length - 1) / 2) * gap);
    // a commit magasságától legtávolabbit rajzoljuk először: a közös szakaszon a közelebbi látszik
    const order = stubs.map((t, k) => k).sort((p, q) => Math.abs(ys[q] - y0) - Math.abs(ys[p] - y0));
    for (const k of order) {
      const t = stubs[k], y = ys[k], x = laneX(t.lane), dy = y - y0;
      const color = t.worktree === focusWt()?.slug ? laneColor(t.lane) : fade(laneColor(t.lane));
      // legyező: egyetlen sima ív a commit pöttyéből a csonk pöttyéig
      const d = !dy ? `M ${x0} ${y0} H ${x}`
        : `M ${x0} ${y0} C ${x0 + (x - x0) * 0.45} ${y0}, ${x0 + (x - x0) * 0.35} ${y}, ${x} ${y}`;
      out += `<path d="${d}" fill="none" stroke="${color}" stroke-width="2"/>`
        + `<circle cx="${x}" cy="${y}" r="${DOT_R}" fill="${color}" stroke="${color}" stroke-width="2"/>`;
    }
  });
  visible.forEach((c, i) => {
    if (c.uncommitted && c.worktree === focusWt()?.slug) return;   // a pontja a #pending sávban van
    const color = tint(c, laneColor(c.lane));
    const merge = c.parents.length > 1;
    // Az ál-sor pontja üres karika: a szaggatott vonal már jelzi, hogy nem
    // commit — a pöttyözött körvonal ezen a méreten csak elmosódna.
    const hollow = merge || c.uncommitted;
    if (fresh.has(c.sha)) out += `<circle cx="${laneX(c.lane)}" cy="${rowY(i)}" r="8" fill="${color}" opacity=".28"/>`;
    out += `<circle cx="${laneX(c.lane)}" cy="${rowY(i)}" r="${hollow ? DOT_R + 1 : DOT_R}"`
        +  ` fill="${hollow ? 'var(--bg)' : color}" stroke="${color}" stroke-width="2"/>`;
  });
  svg.innerHTML = out;
}

/* Sávváltásnál ott hajlik a vonal, ahol a git is: merge-nél rögtön a merge
   commit alatt, ág-leágazásnál pedig közvetlenül a szülő fölött. */
function edgePath(x1, y1, x2, y2, merge) {
  if (x1 === x2) return `M ${x1} ${y1} L ${x2} ${y2}`;
  // Legyező: a vonal a commit pöttyéből függőlegesen indul (fel vagy le), és a
  // worktree-csonk ívét elforgatva fordul a másik sávba egy soron belül.
  if (merge) {
    const bend = Math.min(y1 + ROW_H, y2);
    const s1 = Math.min(y1 + EDGE_HUG, bend), dy = bend - s1;
    return `M ${x1} ${y1} L ${x1} ${s1} C ${x1} ${s1 + dy * 0.45}, ${x2} ${s1 + dy * 0.35}, ${x2} ${bend} L ${x2} ${y2}`;
  }
  const bend = Math.max(y2 - ROW_H, y1);
  const s2 = Math.max(y2 - EDGE_HUG, bend), dy = bend - s2;
  return `M ${x1} ${y1} L ${x1} ${bend} C ${x1} ${s2 + dy * 0.35}, ${x2} ${s2 + dy * 0.45}, ${x2} ${s2} L ${x2} ${y2}`;
}

/* Van-e a listában más worktree WIP-sora (a saját szaggatott vonala ilyenkor átfut rajtuk). */
let otherWip = false;
export const setOtherWip = on => { otherWip = on; };
/* A saját WIP szaggatott vonala görgetve eltűnik, ha nincs alatta más WIP-sor, vagy ha
   a HEAD-je már a lista teteje fölé csúszott (köztük commit van, a vonal nem vezet sehova). */
export function hideOwnEdge() {
  const head = focusWt()?.head;
  const row = head && rowsEl.querySelector(`.row[data-sha="${head}"]`);
  const past = row && row.getBoundingClientRect().bottom <= scroller.getBoundingClientRect().top;
  const hide = scroller.scrollTop > 0 && (!otherWip || Boolean(past));
  scroller.classList.toggle('hide-own', hide);
  pendingEl.classList.toggle('hide-own', hide);
}
function drawPending() {
  const lane = pendingEl.querySelector('.pend-lane');
  if (!lane) return;
  // A lista görgetősávja szűkíti a sorokat: a sáv ugyanennyivel beljebb zár, hogy
  // az idő · avatar · diff oszlopban álljon a lista soraival.
  pendingEl.style.paddingRight = `${scroller.offsetWidth - scroller.clientWidth}px`;
  const h = pendingEl.offsetHeight;
  lane.setAttribute('width', graphW);
  lane.setAttribute('height', h);
  lane.innerHTML = [...pendingEl.querySelectorAll('.row')].map(row => {
    const c = commitBySha(row.dataset.sha);
    if (!c) return '';
    const x = laneX(c.lane), y = row.offsetTop + row.offsetHeight / 2;
    const color = tint(c, laneColor(c.lane));
    const own = c.worktree === focusWt()?.slug ? ' own' : '';
    return `<path class="pend-edge${own}" d="M ${x} ${y + DOT_R + 1} L ${x} ${h}" stroke="${color}" stroke-width="2" stroke-dasharray="3 3"/>`
      + `<circle cx="${x}" cy="${y}" r="${DOT_R + 1}" fill="var(--bg)" stroke="${color}" stroke-width="2"/>`;
  }).join('');
}
