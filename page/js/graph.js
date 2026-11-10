/* A gráf (sávok, élek, pöttyök) az `#lanes` SVG-be, és a fix sáv WIP-sorai. */
import { pendingEl, rowsEl, scroller, svg } from './dom.js';
import { directCount, hiddenSha, isMerge, layout, visibleBelow, walkDown } from './merges.js';
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
/* Összecsukás és kibontás közben (`foldRows`, `unfoldRows`): az eltűnő / megjelenő sorok, a teljes
   magasságuk (`full`), és a pontozott él láthatósága (`p`: csukáskor 0 → 1, nyitáskor 1 → 0). A sorok
   élei és pöttyei 1 − p erősséggel látszanak: a végén nincs ugrás. */
let foldFx = /** @type {{ hidden: Set<string>, full: Map<string, number>, p: number } | null} */ (null);
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
/* Egy rajzolás közös adatai (`drawGraph` tölti): a látható sorok indexe (`idx`), a sor közepe
   (`rowY`), animáció közben a kibontott (`open`) és a csukott (`closed`) állapotban is, a
   merge-szárak (`stems`: a 2. szülő sora a teljes listában → a legfelső merge sora a láthatók
   közt), és hogy egy commit nem látszik-e (`gone`: nincs a listában, vagy épp felcsukódik /
   lenyílik). */
let g = /** @type {{ idx: Map<string, number>, rowY: (i: number) => number, open: (i: number) => number,
  closed: (i: number) => number, stems: Map<number, number>, gone: (sha: string) => boolean }} */
  (/** @type {unknown} */ (null));

export function drawGraph() {
  drawPending();
  const idx = new Map(visible.map((c, i) => [c.sha, i]));
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

  // A merge-ek szára (a 2. szülő-élük): összecsukva pontozott, kibontva folytonos; mindkettőbe
  // befuthat egy rá épülő ág (`joinStem`). A felcsukódó / lenyíló merge-é nem számít.
  const stems = new Map();
  for (const e of DATA.edges) {
    if (!e.merge) continue;
    const a = idx.get(DATA.commits[e.fromRow].sha);
    if (a === undefined || foldFx?.hidden.has(DATA.commits[e.fromRow].sha)) continue;
    stems.set(e.toRow, Math.min(stems.get(e.toRow) ?? Infinity, a));
  }
  g = { idx, rowY, open: rowY, closed: rowY, stems, gone: sha => Boolean(foldFx?.hidden.has(sha)) || !idx.has(sha) };
  if (foldFx) foldStates(heightBySha);

  // Az egyenesek előbb, a sávváltó vonalak felül: az elágazás a commit pöttyénél
  // is a saját színével indul, nem takarja el a sáv vonala.
  let out = '', bends = '';
  // Animáció közben a kibontott másik merge szárára épülő ág csatlakozása egyetlen, a helyére csúszó
  // vonal (`morphJoins`): a merge éle helyett, az ág legalsó commitjának éle (`skip`) nélkül.
  const morphs = foldFx ? morphJoins() : new Map();
  const morphed = new Set([...morphs.values()].map(m => m.skip));
  for (const e of DATA.edges) {
    if (morphed.has(e)) continue;
    if (morphs.has(e)) { out += morphs.get(e).path; continue; }
    const from = DATA.commits[e.fromRow], to = DATA.commits[e.toRow];
    const a = idx.get(from.sha), b = idx.get(to.sha);
    const hf = Boolean(foldFx?.hidden.has(from.sha)), ht = Boolean(foldFx?.hidden.has(to.sha));
    if (a === undefined) continue;                     // szűrve
    if (b === undefined) {
      // rejtett szülő: pontozott él az első látható commitig; a felcsukódó / lenyíló sorból
      // indulva a sorokkal együtt halványul
      if (hiddenSha(to.sha)) out += foldedEdge(e, a, false, hf ? 1 - foldFx.p : 1);
      continue;
    }
    if (ht && !hf) {
      // A felcsukódó / lenyíló ágba futó él: a kibontott ráépülő ág alja egy vonalként csúszik a
      // helyére; más él mellé a pontozott (a sorok nélküli) változata erősödik.
      const bottom = e.merge ? '' : dependentBottom(e, a, b);
      if (bottom) { out += bottom; continue; }
      out += foldedEdge(e, a, true, foldFx.p);
    }
    const x1 = laneX(e.fromLane), y1 = rowY(a);
    const x2 = laneX(e.toLane),   y2 = rowY(b);
    // A vonal annak a sávnak a színét kapja, amelyikben a hossza nagy részén fut:
    // a merge-vonal rögtön a cél sávjába fordul, a leágazó csak a szülő fölött.
    const color = tint(from, laneColor(e.merge ? e.toLane : e.fromLane));
    // A munkakönyvtár még nem commit: szaggatva lóg a HEAD-re. Görgetve a sajátja
    // eltűnik, ha nincs alatta más WIP-sor, vagy ha a HEAD-je már a sáv alá csúszott
    // (`hideOwnEdge`); a többié látszik — különben nem tudni, hová tart.
    const own = from.worktree === focusWt()?.slug ? ' own' : '';
    // A stash sem commit a branch-en: az éle a bázisára ugyanígy szaggatott.
    const dash = from.uncommitted ? ` class="pend-edge${own}" stroke-dasharray="3 3"`
      : from.stash ? ' stroke-dasharray="3 3"' : '';
    const path = solid(edgePath(x1, y1, x2, y2, e.merge), color, ht || hf ? 1 - foldFx.p : 1, dash);
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
      out += solid(d, color)
        + `<circle cx="${x}" cy="${y}" r="${DOT_R}" fill="${color}" stroke="${color}" stroke-width="2"/>`;
    }
  });
  // A tükör-commit (`mirrorOf`, pl. egy subtree-remote másolata) vékony, szaggatott íve a
  // forrás pöttyéhez, a tükör sávjának színével; a pöttyök alá, hogy a végeit takarják.
  // A subtree squash-commitja (`splitOf`) ugyanígy a split-commithoz: nem a szülője.
  visible.forEach((c, i) => {
    const to = c.mirrorOf || c.splitOf;
    const j = to ? idx.get(to) : undefined;
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
    // a felcsukódó / lenyíló sor pöttye az élével együtt halványul
    const op = foldFx?.hidden.has(c.sha) ? 1 - foldFx.p : 1;
    out += op < 1 ? `<g${fadeAttr(op)}>${dot(c, i)}</g>` : dot(c, i);
  });
  function dot(c, i) {
    const color = tint(c, laneColor(c.lane));
    const merge = isMerge(c), x = laneX(c.lane), y = rowY(i);
    // Az ál-sor és a stash pontja üres karika: a szaggatott vonal már jelzi, hogy nem
    // commit a branch-en — a pöttyözött körvonal ezen a méreten csak elmosódna.
    // A tükör-commit is: a forrása a valódi commit, ez csak a másolata.
    const hollow = c.uncommitted || c.stash || c.mirrorOf;
    const halo = fresh.has(c.sha) ? `<circle cx="${x}" cy="${y}" r="${merge ? 10 : 8}" fill="${color}" opacity=".28"/>` : '';
    // A merge a történet fő pontja: telt mag gyűrűvel, egy színben (a beolvasztott ág színe a
    // „+N”-en és a nyílon); a gyűrű háttérszínű kitöltése a rés.
    if (merge) {
      return `${halo}<circle cx="${x}" cy="${y}" r="${RING_R}" fill="var(--bg)" stroke="${color}" stroke-width="2"/>`
          +  `<circle cx="${x}" cy="${y}" r="${CORE_R}" fill="${color}"/>`;
    }
    return `${halo}<circle cx="${x}" cy="${y}" r="${hollow ? DOT_R + 1 : DOT_R}"`
        +  ` fill="${hollow ? 'var(--bg)' : color}" stroke="${color}" stroke-width="2"/>`;
  }
  svg.innerHTML = out;
}

/* Egy vonal: folytonos (`extra`: további attribútumok), pontozott (a rejtett commitokat átugró él),
   és ugyanazon az útvonalon az átmenet a kettő közt (`p`: a pontozott erőssége). */
const solid = (d, color, op = 1, extra = '') =>
  `<path d="${d}" fill="none" stroke="${color}" stroke-width="2"${extra}${fadeAttr(op)}/>`;
const dotted = (d, color, op = 1) =>
  `<path class="fold" d="${d}" fill="none" stroke="${color}" stroke-width="2" stroke-dasharray="2 2"${fadeAttr(op)}/>`;
const crossfade = (d, color, p) => solid(d, color, 1 - p) + dotted(d, color, p);

/* Rejtett szülőre mutató él (összecsukott merge 2. szülője, vagy egy ref-es commit beolvasztott
   lánca) helyette az első látható commitig (az első szülő láncán): pontozott, mert commitot ugrik
   át; a rejtett ág sávjában fut. A merge 2. szülőjénél, ha a cél a merge alatti sor (nincs köztük
   látható sor), nincs él; az első szülő éle mindig megvan, különben a lánc elszakadna. `a`: a
   kiinduló sor. `anim`: a felcsukódó / lenyíló sorok (`foldFx`) már rejtettnek számítanak. Az él
   `opacity` erősséggel látszik. */
function foldedEdge(e, a, anim, opacity) {
  const from = DATA.commits[e.fromRow], to = DATA.commits[e.toRow];
  const b = g.idx.get(anim ? walkDown(to.sha, g.gone).c?.sha : visibleBelow(to.sha));
  const join = b === undefined ? null : joinStem(e, a, b);
  if (join) return dotted(join.d, join.color, opacity);
  let next = a + 1;
  while (anim && next < (b ?? 0) && foldFx.hidden.has(visible[next].sha)) next++;
  if (b === undefined || (b === next && from.parents[0] !== to.sha)) return '';
  const x1 = laneX(e.fromLane), xv = laneX(e.toLane), x2 = laneX(visible[b].lane), y1 = g.rowY(a), y2 = g.rowY(b);
  // A rejtett ág sávjába fordul a merge alatt, és a cél fölött fordul a cél sávjába. Ha a kiinduló
  // már a rejtett ág sávjában van, vagy a két fordulónak nincs helye, egyetlen ív: két darabból a
  // második derékszögbe lapulna (a köztes pont a cél magasságára esne).
  const ym = Math.max(y1 + ROW_H, y2 - ROW_H);
  const d = xv === x2 ? edgePath(x1, y1, x2, y2, true)
    : x1 === xv ? edgePath(x1, y1, x2, y2, false)
    : y2 - y1 < 2 * ROW_H ? edgePath(x1, y1, x2, y2, true)
    : `${edgePath(x1, y1, xv, ym, true)} ${chain(edgePath(xv, ym, x2, y2, false))}`;
  return dotted(d, tint(from, laneColor(e.toLane)), opacity);
}

/* Animáció közben a sorok közepe a két végállapotban: kibontva (a felcsukódó / lenyíló sorok teljes
   magasságukkal) és csukva (nélkülük; a rejtett sor a helye tetejére kerül). A sorok magassága a
   haladással arányos, így a pillanatnyi hely a kettő közt van: `rowY = open + (closed − open)·p`. */
function foldStates(heightBySha) {
  const open = [], closed = [];
  let now = 0, full = 0;                    // a fölötte lévő rejtett sorok pillanatnyi és teljes magassága
  visible.forEach((c, i) => {
    const y = g.rowY(i);
    if (!foldFx.hidden.has(c.sha)) { open.push(y + full - now); closed.push(y - now); return; }
    const h = heightBySha.get(c.sha) || 0, top = y - h / 2, f = foldFx.full.get(c.sha) ?? h;
    open.push(top + full - now + f / 2);
    closed.push(top - now);
    now += h; full += f;
  });
  g.open = i => open[i];
  g.closed = i => closed[i];
}

/* A szár fordulópontja: egy sornyival a cél (`yEnd`) fölött, de legalább egy sornyival a szár
   merge-e (`stemRow`) alatt — itt fordul ki a szár a rejtett ág sávjából. `Y`: a sorok közepe. */
const stemBend = (stemRow, yEnd, Y) => Math.max(Y(stemRow) + ROW_H, yEnd - ROW_H);
/* Ahol egy lentebbi merge ága (merge-e: `y1`) befut a szárba: a szár merge-e és a saját merge-e
   alatt, de legkésőbb a szár fordulópontjában (`bend`). */
const stemJoin = (stemRow, y1, bend, Y) => Math.min(Math.max(Y(stemRow) + ROW_H, y1 + 2 * ROW_H), bend);

/* Egy másik merge szárába befutó rövid pontozott él, ha az él rejtett lánca (az első szülők
   mentén) olyan commiton át vezet, amelyre egy másik merge szára fut. A szár a merge alatt fordul
   a rejtett ág sávjába, és a cél előtt egy sornyival fordul el onnan: a befutás e két pont között
   van. A szár a forrás fölött (egy ráépülő, kibontott ág alja): egy sornyi ív a szár sávjába. A
   szár a forrás alatt (a ráépülő ág merge-e is összecsukva): a saját rejtett sávjában le a szár
   merge-e alá, ott be a szárba. `Y`: a sorok közepe (animáció közben a két végállapot egyike is).
   Az eredmény az útvonal, és a szár sávjába forduló ív eleje (`turn`) és vége (`end`); ha nincs
   ilyen szár: null. */
function joinStem(e, a, b, Y = g.rowY) {
  if (!g.stems.size) return null;
  // A rejtett lánc első olyan commitja, amelyre egy másik merge szára fut; ha a lánc egy látható
  // commiton ér véget, az is lehet szár-cél (kibontott merge 2. szülője).
  let c = DATA.commits[e.toRow], stemRow, hRow;
  while (c) {
    const r = rowOfSha().get(c.sha), s = g.stems.get(r);
    if (s !== undefined && s !== a) { stemRow = s; hRow = r; break; }
    if (!g.gone(c.sha)) break;
    c = commitBySha(c.parents[0]);
  }
  if (stemRow === undefined) return null;
  const hc = DATA.commits[hRow], tip = g.idx.get(hc.sha);
  const end = tip !== undefined && !g.gone(hc.sha) ? tip : b;
  const x1 = laneX(e.fromLane), xs = laneX(hc.lane), y1 = Y(a);
  const bend = stemBend(stemRow, Y(end), Y);
  // Az ív annak az ágnak a színe, amelyikből jön: a commit alól a commit sávjáé, a merge-ből a
  // rejtett ágáé.
  const color = tint(DATA.commits[e.fromRow], laneColor(stemRow < a ? e.fromLane : e.toLane));
  if (stemRow < a) {
    if (bend <= y1 + 4) return null;
    const end = Math.min(y1 + ROW_H, bend);
    return { color, turn: y1, end, d: `M ${x1} ${y1} ${sCurve(x1, y1, xs, end)}` };
  }
  const xo = laneX(e.toLane), yJoin = stemJoin(stemRow, y1, bend, Y);
  if (yJoin <= y1 + ROW_H) return null;
  const yTurn = Math.max(y1 + ROW_H, yJoin - ROW_H);     // a rejtett sávjában eddig egyenesen
  return { color, turn: yTurn, end: yJoin, d: x1 === xo ? `M ${x1} ${y1} L ${x1} ${yTurn} ${sCurve(x1, yTurn, xs, yJoin)}`
    : `${edgePath(x1, y1, xo, y1 + ROW_H, true)} L ${xo} ${yTurn} ${sCurve(xo, yTurn, xs, yJoin)}` };
}

/* Összecsukás / kibontás közben: ha a csukódó / nyíló ág (`foldFx.hidden`) egy másik merge szárára
   épül (az ág legalsó commitjának szülője annak a merge-nek a 2. szülője), a csatlakozás egyetlen
   vonal, amely a helyére csúszik. A két végállapota a statikus rajz: kibontva az ág legalsó
   commitjának éle (a csúcsba vagy a szárba), csukva a merge pontozott éle a szárba. A forduló a
   legalsó committal együtt mozog, és a haladás köbével fut be a csukott helyére (eleinte a sorokkal
   megy, a végén ér célba); az ív hossza a haladással vált. Kibontott szárnál az egész vonal
   folytonosból pontozottá vált; összecsukottnál a pontozott végig látszik, és a merge-ből induló
   szakaszán egy folytonos réteg halványul (kibontva ez takarja). Kulcs: a merge éle; `skip`: az ág
   legalsó commitjának éle, ezt a vonal helyettesíti. */
function morphJoins() {
  const res = new Map();
  for (const e of DATA.edges) {
    if (!e.merge) continue;
    const m = DATA.commits[e.fromRow], a = g.idx.get(m.sha);
    if (a === undefined || foldFx.hidden.has(m.sha) || !foldFx.hidden.has(DATA.commits[e.toRow].sha)) continue;
    const { prev, c } = walkDown(DATA.commits[e.toRow].sha, sha => foldFx.hidden.has(sha));
    const stemRow = c && g.stems.get(rowOfSha().get(c.sha));
    if (!prev || !c || stemRow === undefined || stemRow <= a) continue;
    // a szár célja: kibontva a látható csúcs, összecsukva az alatta lévő első látható commit
    const tip = g.idx.get(c.sha), shown = tip !== undefined;
    const b = shown ? tip : g.idx.get(walkDown(c.sha, g.gone).c?.sha);
    if (b === undefined) continue;
    const skip = DATA.edges.find(x => !x.merge && DATA.commits[x.fromRow] === prev && DATA.commits[x.toRow] === c);
    const ib = g.idx.get(prev.sha), O = g.open;
    const open = shown ? { turn: Math.max(O(tip) - ROW_H, O(ib)), end: O(tip) } : joinStem(skip, ib, b, O);
    const closed = joinStem(e, a, b, g.closed);
    if (!open || !closed) continue;
    // a forduló a legalsó committal mozog; ahová az a csukott állapotban kerülne, és a csukott
    // forduló közti különbséget a haladás köbével vonjuk le
    const p = foldFx.p, rows = g.rowY(ib) - O(ib), settled = open.turn + g.closed(ib) - O(ib);
    const yS = open.turn + rows + (closed.turn - settled) * p ** 3;
    const len = open.end - open.turn + (closed.end - closed.turn - (open.end - open.turn)) * p;
    // Az ív vége kibontott szárnál legfeljebb a csúcs, összecsukottnál a szár pillanatnyi
    // fordulópontja (ott fordul el a sávjából); sosem a forduló fölött (nem kanyarodik vissza).
    const cap = shown ? g.rowY(tip) : Math.max(stemBend(stemRow, g.rowY(b), g.rowY), closed.end);
    const yE = Math.max(yS, Math.min(yS + len, cap));
    const xm = laneX(e.fromLane), xg = laneX(e.toLane), ym = g.rowY(a);
    const upper = xm === xg ? `M ${xm} ${ym} L ${xg} ${yS}` : `${edgePath(xm, ym, xg, ym + ROW_H, true)} L ${xg} ${yS}`;
    const d = `${upper} ${sCurve(xg, yS, laneX(c.lane), yE)}`, color = tint(m, laneColor(e.toLane));
    res.set(e, { skip, path: shown ? crossfade(d, color, p) : dotted(d, color) + solid(upper, color, 1 - p) });
  }
  return res;
}

/* Kibontott ráépülő ág legalsó commitja, miközben a másik merge (amelynek a csúcsára épül)
   összecsukódik / kinyílik: egyetlen vonal a commitból a másik ág sávjába. A vége a haladással
   megy a kibontott helyéről (a másik ág csúcsa) a csukott helyére (a statikus rajz íve a szárba);
   közben a folytonos halványul, a pontozott erősödik. */
function dependentBottom(e, a, b) {
  const stem = g.stems.get(e.toRow);
  if (stem === undefined || stem >= a) return '';
  const x1 = laneX(e.fromLane), x2 = laneX(e.toLane), y1 = g.rowY(a);
  const bc = g.idx.get(walkDown(DATA.commits[e.toRow].sha, g.gone).c?.sha);
  const closed = bc === undefined ? { end: y1 + ROW_H } : joinStem(e, a, bc, g.closed) ?? { end: y1 + 4 };
  const open = Math.max(g.open(b), g.open(a) + ROW_H);
  const yEnd = open + (closed.end - open) * foldFx.p, turn = Math.max(yEnd - ROW_H, y1);
  const d = `M ${x1} ${y1} L ${x1} ${turn} ${sCurve(x1, turn, x2, yEnd)}`;
  return crossfade(d, tint(DATA.commits[e.fromRow], laneColor(e.fromLane)), foldFx.p);
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
