/* A gráf (sávok, élek, pöttyök) az `#lanes` SVG-be, és a fix sáv WIP-sorai. */
import { pendingEl, rowsEl, scroller, svg } from './dom.js';
import { directCount, hiddenSha, isMerge, layout, visibleBelow } from './merges.js';
import { commitBySha, fade, focusWt, fresh, laneColor, tint } from './model.js';
import { DATA, visible } from './state.js';

const ROW_H = 34, LANE_W = 14, X0 = 16, DOT_R = 4;
const CORE_R = 3.5, RING_R = 6;     // a merge pontja: telt mag, körülötte gyűrű (köztük háttérszínű rés)
/* A merge pontja mellett a „+N” és a nyíl (`.merge-fold`) jobb széle a pont közepétől: rés (10) +
   a szám keretje (8) + jelenként ~7 px (tabular) + köz (1) + a nyíl (16). Utána a sor 10 px-es
   paddingje a subjectig. */
const foldW = digits => 10 + 8 + (digits + 1) * 7 + 1 + 16;
const EDGE_HUG = DOT_R + 1;   // a sávváltó vonal ennyit fut a commit sávjában, mielőtt elfordul
const STUB_GAP = 11;   // több worktree-csonk pöttyei közti függőleges távolság

let graphW = 72;
/* Összecsukás közben (`foldRows`): a felcsukódó sorok és a haladás (0 → 1). A pontozott él ennyire
   látszik, a felcsukódó ág élei és pöttyei ennyivel halványabbak: a végén nincs ugrás. */
let foldFx = /** @type {{ hidden: Set<string>, p: number } | null} */ (null);
export function setFoldFx(fx) { foldFx = fx; }
const fadeAttr = op => (op < 1 ? ` opacity="${+op.toFixed(3)}"` : '');
/* A gráf-oszlop szélessége a sávok számából (a csonkokéval együtt); a CSS is ezt
   használja (`--graph-w`: a sorok bal paddingje, a panel margója). */
export function sizeGraph() {
  const laneCount = DATA.commits.reduce((m, c) => Math.max(m, c.lane, ...(c.stubs || []).map(t => t.lane)), 0) + 1;
  const { foldable } = layout();
  const fold = DATA.commits.reduce((m, c) => foldable.has(c.sha)
    ? Math.max(m, laneX(c.lane) + foldW(String(directCount(c.sha)).length)) : m, 0);
  graphW = Math.max(32, X0 * 2 + (laneCount - 1) * LANE_W, fold);
  document.documentElement.style.setProperty('--graph-w', graphW + 'px');
}

export function laneX(l) { return X0 + l * LANE_W; }

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
  svg.setAttribute('width', String(graphW));
  svg.setAttribute('height', String(h));
  svg.setAttribute('viewBox', `0 0 ${graphW} ${h}`);

  // Az egyenesek előbb, a sávváltó vonalak felül: az elágazás a commit pöttyénél
  // is a saját színével indul, nem takarja el a sáv vonala.
  let out = '', bends = '';
  for (const e of DATA.edges) {
    const a = rowIndexBySha.get(DATA.commits[e.fromRow].sha);
    const b = rowIndexBySha.get(DATA.commits[e.toRow].sha);
    if (a !== undefined && b === undefined && hiddenSha(DATA.commits[e.toRow].sha)) {
      out += foldedEdge(e, a, rowIndexBySha, rowY);
      continue;
    }
    if (a === undefined || b === undefined) continue;   // szűrve
    // Összecsukás közben a felcsukódó ág éle halványul, a merge pontozott éle beúszik.
    let op = 1;
    if (foldFx) {
      const hf = foldFx.hidden.has(DATA.commits[e.fromRow].sha), ht = foldFx.hidden.has(DATA.commits[e.toRow].sha);
      if (ht && !hf) out += foldedEdge(e, a, rowIndexBySha, rowY, foldFx.hidden, foldFx.p);
      if (ht || hf) op = 1 - foldFx.p;
    }
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
    // A stash sem commit a branch-en: az éle a bázisára ugyanígy szaggatott.
    const dash = from.uncommitted ? ` class="pend-edge${own}" stroke-dasharray="3 3"`
      : from.stash ? ' stroke-dasharray="3 3"' : '';
    const path = `<path d="${edgePath(x1, y1, x2, y2, e.merge)}" fill="none" stroke="${color}" stroke-width="2"${dash}${fadeAttr(op)}/>`;
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
  // A tükör-commit (`mirrorOf`, pl. egy subtree-remote másolata) vékony, szaggatott íve a
  // forrás pöttyéhez, a tükör sávjának színével; a pöttyök alá, hogy a végeit takarják.
  // A subtree squash-commitja (`splitOf`) ugyanígy a split-commithoz: nem a szülője.
  visible.forEach((c, i) => {
    const to = c.mirrorOf || c.splitOf;
    const j = to ? rowIndexBySha.get(to) : undefined;
    if (j === undefined) return;                       // nincs tükör, vagy a forrása szűrve
    const src = visible[j];
    const x1 = laneX(c.lane), y1 = rowY(i), x2 = laneX(src.lane), y2 = rowY(j), ym = (y1 + y2) / 2;
    // Egy sávban egyenes volna (a sáv vonalán): ott oldalra hajlik.
    const bow = x1 === x2 ? LANE_W * 0.8 : 0;
    out += `<path d="M ${x1} ${y1} C ${x1 + bow} ${ym}, ${x2 + bow} ${ym}, ${x2} ${y2}" fill="none"`
      + ` stroke="${laneColor(c.lane)}" stroke-width="1.2" stroke-dasharray="2 2"/>`;
  });
  visible.forEach((c, i) => {
    if (c.uncommitted && c.worktree === focusWt()?.slug) return;   // a pontja a #pending sávban van
    // a felcsukódó sor pöttye az élével együtt halványul
    const start = out.length, op = foldFx?.hidden.has(c.sha) ? 1 - foldFx.p : 1;
    dot(c, i);
    if (op < 1) out = `${out.slice(0, start)}<g${fadeAttr(op)}>${out.slice(start)}</g>`;
  });
  function dot(c, i) {
    const color = tint(c, laneColor(c.lane));
    const merge = isMerge(c), x = laneX(c.lane), y = rowY(i);
    // Az ál-sor és a stash pontja üres karika: a szaggatott vonal már jelzi, hogy nem
    // commit a branch-en — a pöttyözött körvonal ezen a méreten csak elmosódna.
    // A tükör-commit is: a forrása a valódi commit, ez csak a másolata.
    const hollow = c.uncommitted || c.stash || c.mirrorOf;
    if (fresh.has(c.sha)) out += `<circle cx="${x}" cy="${y}" r="${merge ? 10 : 8}" fill="${color}" opacity=".28"/>`;
    // A merge a történet fő pontja: telt mag gyűrűvel, egy színben (a beolvasztott ág színe a
    // „+N”-en és a nyílon); a gyűrű háttérszínű kitöltése a rés.
    if (merge) {
      out += `<circle cx="${x}" cy="${y}" r="${RING_R}" fill="var(--bg)" stroke="${color}" stroke-width="2"/>`
          +  `<circle cx="${x}" cy="${y}" r="${CORE_R}" fill="${color}"/>`;
      return;
    }
    out += `<circle cx="${x}" cy="${y}" r="${hollow ? DOT_R + 1 : DOT_R}"`
        +  ` fill="${hollow ? 'var(--bg)' : color}" stroke="${color}" stroke-width="2"/>`;
  }
  svg.innerHTML = out;
}

/* Rejtett szülőre mutató él (összecsukott merge 2. szülője, vagy egy ref-es commit beolvasztott
   lánca) helyette az első látható commitig (az első szülő láncán): szaggatott, mert commitot ugrik
   át; a rejtett ág sávjában fut. A merge 2. szülőjénél, ha a cél a merge alatti sor (nincs köztük
   látható sor), nincs él; az első szülő éle mindig megvan, különben a lánc elszakadna. `a`: a
   kiinduló sor; a sorindex és a sor közepe a `drawGraph`-é. Összecsukás közben a `skip` sorai még
   a listában vannak, de már nem számítanak; az él `opacity` erősséggel látszik. */
function foldedEdge(e, a, rowIndexBySha, rowY, skip = null, opacity = 1) {
  const from = DATA.commits[e.fromRow], to = DATA.commits[e.toRow];
  const b = rowIndexBySha.get(visibleBelow(to.sha));
  let next = a + 1;
  while (skip && next < (b ?? 0) && skip.has(visible[next].sha)) next++;
  if (b === undefined || (b === next && from.parents[0] !== to.sha)) return '';
  const x1 = laneX(e.fromLane), xv = laneX(e.toLane), x2 = laneX(visible[b].lane), y1 = rowY(a), y2 = rowY(b);
  // A rejtett ág sávjába fordul a merge alatt, és a cél fölött fordul a cél sávjába. Ha a kiinduló
  // már a rejtett ág sávjában van, vagy a két fordulónak nincs helye, egyetlen ív: két darabból a
  // második derékszögbe lapulna (a köztes pont a cél magasságára esne).
  const ym = Math.max(y1 + ROW_H, y2 - ROW_H);
  const d = xv === x2 ? edgePath(x1, y1, x2, y2, true)
    : x1 === xv ? edgePath(x1, y1, x2, y2, false)
    : y2 - y1 < 2 * ROW_H ? edgePath(x1, y1, x2, y2, true)
    : `${edgePath(x1, y1, xv, ym, true)} ${edgePath(xv, ym, x2, y2, false)}`;
  const color = tint(from, laneColor(e.toLane));
  return `<path class="fold" d="${d}" fill="none" stroke="${color}" stroke-width="2" stroke-dasharray="2 2"${fadeAttr(opacity)}/>`;
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
  lane.setAttribute('width', String(graphW));
  lane.setAttribute('height', String(h));
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
