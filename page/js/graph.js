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
/* Összecsukás és kibontás közben (`foldRows`, `unfoldRows`): az eltűnő / megjelenő sorok, és a
   pontozott él láthatósága (`p`: csukáskor 0 → 1, nyitáskor 1 → 0). A sorok élei és pöttyei
   1 − p erősséggel látszanak: a végén nincs ugrás. */
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
  // Az összecsukott merge-ek szára: a rejtett 2. szülő sora → a merge sora. Ha egy látható
  // commit (egy ráépülő, kibontott ág alja) ugyanerre a rejtett commitra épül, a pontozott vége
  // ebbe a szárba fut be, nem húz külön vonalat (`foldedEdge`, `stemAbove`).
  // A szár a merge 2. szülő-éle: összecsukva pontozott, kibontva folytonos; mindkettőbe befuthat
  // egy rá épülő ág. Animáció közben (`foldFx`) a felcsukódó / megjelenő sorok rejtettnek számítanak.
  const stems = new Map();
  for (const e of DATA.edges) {
    if (!e.merge) continue;
    const a = rowIndexBySha.get(DATA.commits[e.fromRow].sha);
    if (a === undefined || foldFx?.hidden.has(DATA.commits[e.fromRow].sha)) continue;
    stems.set(e.toRow, Math.min(stems.get(e.toRow) ?? Infinity, a));
  }
  // Animáció közben a kibontott másik merge szárára épülő ág csatlakozása egyetlen, a helyére csúszó
  // vonal (`morphJoins`): a merge éle és az ág legalsó commitjának éle helyett.
  const morphs = foldFx ? morphJoins(rowIndexBySha, rowY, stems) : new Map();
  const morphed = new Set([...morphs.values()].map(m => m.skip));
  for (const e of DATA.edges) {
    const a = rowIndexBySha.get(DATA.commits[e.fromRow].sha);
    const b = rowIndexBySha.get(DATA.commits[e.toRow].sha);
    if (morphed.has(e)) continue;
    if (morphs.has(e)) { out += morphs.get(e).path; continue; }
    if (a !== undefined && b === undefined && hiddenSha(DATA.commits[e.toRow].sha)) {
      // a lenyíló / felcsukódó ág sorából induló pontozott él is a sorokkal együtt halványul
      const op = foldFx?.hidden.has(DATA.commits[e.fromRow].sha) ? 1 - foldFx.p : 1;
      out += foldedEdge(e, a, rowIndexBySha, rowY, null, op, stems);
      continue;
    }
    if (a === undefined || b === undefined) continue;   // szűrve
    // Összecsukás közben a felcsukódó ág éle halványul, a merge pontozott éle beúszik.
    let op = 1;
    if (foldFx) {
      const hf = foldFx.hidden.has(DATA.commits[e.fromRow].sha), ht = foldFx.hidden.has(DATA.commits[e.toRow].sha);
      if (ht && !hf) out += foldedEdge(e, a, rowIndexBySha, rowY, foldFx.hidden, foldFx.p, stems);
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
function foldedEdge(e, a, rowIndexBySha, rowY, skip = null, opacity = 1, stems = null) {
  const from = DATA.commits[e.fromRow], to = DATA.commits[e.toRow];
  const b = rowIndexBySha.get(skip ? belowSkipping(to.sha, skip, rowIndexBySha) : visibleBelow(to.sha));
  const join = b === undefined ? '' : joinStem(e, a, b, rowIndexBySha, rowY, skip, stems, from);
  if (join) return join + fadeAttr(opacity) + '/>';
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
    : `${edgePath(x1, y1, xv, ym, true)} ${chain(edgePath(xv, ym, x2, y2, false))}`;
  const color = tint(from, laneColor(e.toLane));
  return `<path class="fold" d="${d}" fill="none" stroke="${color}" stroke-width="2" stroke-dasharray="2 2"${fadeAttr(opacity)}/>`;
}

/* Egy másik összecsukott merge szárába befutó rövid pontozott él, ha az él rejtett lánca (az első
   szülők mentén) olyan rejtett commiton át vezet, amelyre egy másik merge szára fut (`stems`: a
   rejtett commit sora → a merge sora). A szár a merge alatt fordul a rejtett ág sávjába, és a cél
   előtt egy sornyival fordul el onnan: a befutás e két pont között van. A szár a forrás fölött
   (egy ráépülő, kibontott ág alja): egy sornyi ív a szár sávjába. A szár a forrás alatt (a
   ráépülő ág merge-e is összecsukva): a saját rejtett sávjában le a szár merge-e alá, ott be a
   szárba. A path nyitva marad (`fadeAttr` és lezárás a hívóé); ha nincs ilyen szár, ''. */
function joinStem(e, a, b, rowIndexBySha, rowY, skip, stems, from) {
  if (!stems?.size) return '';
  const hidden = sha => skip?.has(sha) || foldFx?.hidden.has(sha) || !rowIndexBySha.has(sha);
  // A rejtett lánc első olyan commitja, amelyre egy másik merge szára fut; ha a lánc egy látható
  // commiton ér véget, az is lehet szár-cél (kibontott merge 2. szülője).
  let c = DATA.commits[e.toRow], stemRow, hRow;
  while (c) {
    const r = rowOfSha().get(c.sha), s = stems.get(r);
    if (s !== undefined && s !== a) { stemRow = s; hRow = r; break; }
    if (!hidden(c.sha)) break;
    c = commitBySha(c.parents[0]);
  }
  if (stemRow === undefined) return '';
  const tip = rowIndexBySha.get(DATA.commits[hRow].sha);
  const end = tip !== undefined && !hidden(DATA.commits[hRow].sha) ? tip : b;
  const x1 = laneX(e.fromLane), xs = laneX(DATA.commits[hRow].lane), y1 = rowY(a);
  const bend = Math.max(rowY(stemRow) + ROW_H, rowY(end) - ROW_H);
  // Az ív annak az ágnak a színe, amelyikből jön: a commit alól a commit sávjáé, a merge-ből a
  // rejtett ágáé.
  const color = tint(from, laneColor(stemRow < a ? e.fromLane : e.toLane));
  let d;
  if (stemRow < a) {
    if (bend <= y1 + 4) return '';
    d = `M ${x1} ${y1} ${sCurve(x1, y1, xs, Math.min(y1 + ROW_H, bend))}`;
  } else {
    const xo = laneX(e.toLane), yJoin = Math.min(Math.max(rowY(stemRow) + ROW_H, y1 + 2 * ROW_H), bend);
    if (yJoin <= y1 + ROW_H) return '';
    const yTurn = Math.max(y1 + ROW_H, yJoin - ROW_H);     // a rejtett sávjában eddig egyenesen
    d = x1 === xo ? `M ${x1} ${y1} L ${x1} ${yTurn} ${sCurve(x1, yTurn, xs, yJoin)}`
      : `${edgePath(x1, y1, xo, y1 + ROW_H, true)} L ${xo} ${yTurn} ${sCurve(xo, yTurn, xs, yJoin)}`;
  }
  return `<path class="fold" d="${d}" fill="none" stroke="${color}" stroke-width="2" stroke-dasharray="2 2"`;
}

/* Összecsukás / kibontás közben: ha a csukódó / nyíló ág (`foldFx.hidden`) egy kibontott másik
   merge szárára épül (az ág legalsó commitjának szülője annak a merge-nek a látható 2. szülője),
   a csatlakozás egyetlen vonal, amely a helyére csúszik: a fordulója a kibontott helyről (a csúcs
   fölött) a csukott helyre (a másik merge alatt) megy a haladással (`foldFx.p`), és ugyanazon az
   útvonalon a folytonos rajzolat halványul, a pontozott erősödik. Kulcs: a merge éle; `skip`: az
   ág legalsó commitjának éle, ezt a vonal helyettesíti. */
function morphJoins(rowIndexBySha, rowY, stems) {
  const res = new Map();
  for (const e of DATA.edges) {
    if (!e.merge) continue;
    const m = DATA.commits[e.fromRow], a = rowIndexBySha.get(m.sha);
    if (a === undefined || foldFx.hidden.has(m.sha) || !foldFx.hidden.has(DATA.commits[e.toRow].sha)) continue;
    let prev = null, c = DATA.commits[e.toRow];
    while (c && foldFx.hidden.has(c.sha)) { prev = c; c = commitBySha(c.parents[0]); }
    // A másik merge kibontva: a szár célja a látható csúcs (`tip`), a kibontott csatlakozás a csúcs
    // fölött fordul (folytonos). Összecsukva: a szár a csúcs alatti első látható commitig fut, a
    // kibontott csatlakozás a legalsó commit alól egy sornyi pontozott ív — a vonal végig pontozott.
    const stemRow = c && stems.get(rowOfSha().get(c.sha));
    if (!prev || !c || stemRow === undefined || stemRow <= a) continue;
    const tip = rowIndexBySha.get(c.sha), shown = tip !== undefined;
    const end = shown ? tip : rowIndexBySha.get(belowSkipping(c.sha, foldFx.hidden, rowIndexBySha));
    if (end === undefined) continue;
    const skip = DATA.edges.find(x => !x.merge && DATA.commits[x.fromRow] === prev && DATA.commits[x.toRow] === c);
    const p = foldFx.p, lerp = (u, v) => u + (v - u) * p;
    const xm = laneX(e.fromLane), xg = laneX(e.toLane), xp = laneX(c.lane);
    const ym = rowY(a), yb = rowY(rowIndexBySha.get(prev.sha)), ye = rowY(end);
    const bend = Math.max(rowY(stemRow) + ROW_H, ye - ROW_H);
    const yJoin = Math.min(Math.max(rowY(stemRow) + ROW_H, ym + 2 * ROW_H), bend);
    const y0 = shown ? [Math.max(ye - ROW_H, yb), ye] : [yb, Math.min(yb + ROW_H, bend)];
    const yS = lerp(y0[0], Math.max(ym + ROW_H, yJoin - ROW_H)), yE = lerp(y0[1], yJoin);
    const d = xm === xg ? `M ${xm} ${ym} L ${xg} ${yS} ${sCurve(xg, yS, xp, yE)}`
      : `${edgePath(xm, ym, xg, ym + ROW_H, true)} L ${xg} ${yS} ${sCurve(xg, yS, xp, yE)}`;
    const color = tint(m, laneColor(e.toLane)), line = `d="${d}" fill="none" stroke="${color}" stroke-width="2"`;
    const dotted = `<path class="fold" ${line} stroke-dasharray="2 2"`;
    // összecsukott szárnál mindkét végállapot pontozott: egy vonal, teljes erővel (a folytonos ág
    // élei alatta halványulnak); kibontott szárnál a folytonos átvált pontozottá
    res.set(e, { skip, path: shown ? `<path ${line}${fadeAttr(1 - p)}/>${dotted}${fadeAttr(p)}/>` : `${dotted}/>` });
  }
  return res;
}

/* Egy útvonal folytatása: a kezdő `M` helyett `L` (ugyanoda), így a szaggatás nem indul újra. */
const chain = d => d.replace(/^M/, 'L');

/* Sima S-ív két sáv között: függőleges érintővel indul és érkezik (a csatlakozó ívé). */
const sCurve = (x1, y1, x2, y2) => {
  const dy = (y2 - y1) / 2;
  return `C ${x1} ${y1 + dy}, ${x2} ${y2 - dy}, ${x2} ${y2}`;
};

/* A commitok sora a teljes listában (`DATA.commits`), sha szerint; adatcserekor újraépül. */
let rowCache = { data: null, map: new Map() };
function rowOfSha() {
  if (rowCache.data !== DATA.commits) rowCache = { data: DATA.commits, map: new Map(DATA.commits.map((c, i) => [c.sha, i])) };
  return rowCache.map;
}

/* Az első látható commit az első szülő láncán, a `skip` sorait (és a már rejtetteket) átlépve. */
function belowSkipping(sha, skip, rowIndexBySha) {
  let c = commitBySha(sha);
  while (c && (skip.has(c.sha) || !rowIndexBySha.has(c.sha))) c = commitBySha(c.parents[0]);
  return c ? c.sha : null;
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
