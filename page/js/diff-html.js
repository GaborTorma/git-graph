/* A nyers diff HTML-je: egymás alatti és side-by-side nézet. */
import { highlight } from './syntax.js';

/* Mindkét nézet elkészül (egymás alatti és side-by-side); hogy melyik látszik,
   azt a `.diff` szélessége dönti el egy container queryvel — átméretezéskor
   újrarenderelés nélkül vált. Ha a diffben csak hozzáadás vagy csak törlés van
   (új fájl, vagy beszúrás / kivágás a változatlan sorok közt), a side-by-side
   egyik oldala végig üres lenne: ott csak az egymás alatti nézet készül.
   Az egymás alatti nézetből kimarad a változás érintetlen oldala (`oneSide`).
   Hunkok közt a kihagyott sorok száma a régi oldal sorszámaiból jön. */
export function diffHtml(d, lang) {
  if (d.binary) return '<p class="diff-note">Bináris fájl.</p>';
  if (!d.hunks.length) return '<p class="diff-note">Nincs megjeleníthető változás.</p>';
  let uni = '', split = '', oldEnd = 1;
  for (const h of d.hunks) {
    const gap = h.old - oldEnd;
    const gapHtml = gap > 0 ? `<p class="diff-gap" title="${gap} változatlan sor">···</p>` : '';
    // Egy blokk (hunk) a `···`-ig: fókuszálható, a nyilak blokkról blokkra lépnek.
    uni += gapHtml + '<div class="hunk" tabindex="-1">' + oneSide(h.lines, partnerIn(h)).map(l => `<div class="diff-line mono${kindOf(l)}">`
      + diffCell(l, l.n, lang) + '</div>').join('') + '</div>';
    split += gapHtml + '<div class="hunk" tabindex="-1">' + splitRows(h, lang) + '</div>';
    oldEnd = h.old + h.lines.filter(l => l.t !== '+').length;
  }
  const kinds = new Set(d.hunks.flatMap(h => oneSide(h.lines, partnerIn(h)).map(l => l.t)));
  const oneSided = !(kinds.has('+') && kinds.has('-'));   // a változatlan sor nem számít
  return (oneSided ? `<div>${uni}</div>`
    : `<div class="diff-uni">${uni}</div><div class="diff-split">${split}</div>`)
    + (d.truncated ? '<p class="diff-note">… a diff túl hosszú, a vége le van vágva.</p>' : '');
}

// a hunk törölt sorának párja (`p`: a hunkbeli indexe)
const partnerIn = h => l => (l.p != null ? h.lines[l.p] : null);

export const KIND = { ' ': '', '+': ' add', '-': ' del' };
export const kindOf = l => KIND[l.t] + (l.only ? ' only' : '');

/* A `t` jelű sorok minden szava megmaradt a másik oldalon: mind párosított
   (van `hl`-je), és nincs kiemelt szakasza. A pár nélküli sor (`hl` nincs)
   egészében változott. */
export const untouched = (ls, t) => ls.every(l => l.t !== t || (l.hl && !l.hl.length));

/* Melyik változott sor érintetlen (`drop`: a szavai mind megvannak a másik
   oldalon) és melyik a párja (`only`: a háttere semleges, csak a változott
   szavai színesek, `kindOf`). Egy futamban (törölt + hozzáadott sorok): ha az
   egyik oldala egészében érintetlen (csak beszúrás / csak törlés), az az oldal;
   különben páronként (`partner`: a törölt sor párja), pl. egy táblázat egyetlen
   sorában csak törlés, a többiben csere. */
export function styles(lines, partner) {
  const st = new Map();
  for (let i = 0; i < lines.length;) {
    if (lines[i].t === ' ') { i++; continue; }
    let j = i; while (j < lines.length && lines[j].t !== ' ') j++;
    const run = lines.slice(i, j);
    i = j;
    if (!run.some(l => l.t === '+') || !run.some(l => l.t === '-')) continue;
    const drop = untouched(run, '-') ? '-' : untouched(run, '+') ? '+' : null;
    if (drop) { for (const l of run) st.set(l, l.t === drop ? 'drop' : 'only'); continue; }
    const inRun = new Set(run);
    for (const d of run) {
      const a = d.t === '-' ? partner(d) : null;
      if (!a || !inRun.has(a)) continue;
      const [x, y] = untouched([d], '-') ? [d, a] : untouched([a], '+') ? [a, d] : [];
      if (x) { st.set(x, 'drop'); st.set(y, 'only'); }
    }
  }
  return st;
}
/** @type {(l: any) => any} */
const noPartner = () => null;

/* Az egymás alatti nézet sorai: az érintetlen oldal kimarad (`styles`) — a
   másik oldal a kiemelt szavaival mindent elmond. */
export function oneSide(lines, partner = noPartner) {
  const st = styles(lines, partner);
  return lines.filter(l => st.get(l) !== 'drop').map(l => (st.get(l) === 'only' ? { ...l, only: true } : l));
}

/* A side-by-side egyik oldala (`keep`: '-' a régi, '+' az új): a változatlan
   sorok és a `keep` jelűek; az érintetlen sor (`styles`) változatlanként. */
export function sideOf(lines, keep, partner = noPartner) {
  const st = styles(lines, partner);
  return lines.filter(l => l.t === ' ' || l.t === keep).map(l => (st.get(l) === 'drop' ? { ...l, t: ' ' }
    : st.get(l) === 'only' ? { ...l, only: true } : l));
}
const diffCell = (l, no, lang) => `<span class="no">${no ?? ''}</span>`
  + `<span class="sg">${l.t === ' ' ? '' : l.t === '-' ? '−' : '+'}</span>`
  + `<span class="tx">${highlight(l.s, l.hl, lang)}</span>`;

/* Side-by-side sorai: [{ a: régi, b: új, ctx }]. A változatlan sor mindkét
   oldalon (`ctx`), a törölt blokk és az utána jövő hozzáadott blokk párjai
   (`partner`: a törölt sor párja, a Python `pair_lines`-a) egy sorba, a pár
   nélküliek egyedül (a másik oldal `null`): a törölt a helyén, a hozzáadott a
   megelőző pár alá (az első pár előttiek elé) — ugyanaz a párosítás, amiből a
   Python a szó-kiemelést számolja. Csak beszúrásnál vagy csak törlésnél (mint
   a `styles`-ban) az érintetlen sor változatlanként, a párja `only`. */
export function alignRows(L, partner) {
  const at = new Map(L.map((l, i) => [l, i]));
  const st = styles(L, partner);
  const look = l => (!l ? l : st.get(l) === 'drop' ? { ...l, t: ' ' } : st.get(l) === 'only' ? { ...l, only: true } : l);
  const rows = [];
  for (let i = 0; i < L.length;) {
    if (L[i].t === ' ') { rows.push({ a: L[i], b: L[i], ctx: true }); i++; continue; }
    let j = i; while (j < L.length && L[j].t === '-') j++;
    let k = j; while (k < L.length && L[k].t === '+') k++;
    const row = (d, n) => rows.push({ a: look(d), b: look(n) });
    const pair = d => { const x = at.get(partner(L[d])); return x >= j && x < k ? x : null; };
    let a = j;
    for (let d = i; d < j; d++) {
      const p = pair(d);
      if (p == null || p < a) { row(L[d], null); continue; }
      while (a < p) row(null, L[a++]);
      row(L[d], L[a++]);
      let next = k;
      for (let e = d + 1; e < j; e++) if (pair(e) != null) { next = pair(e); break; }
      while (a < next) row(null, L[a++]);
    }
    while (a < k) row(null, L[a++]);
    i = k;
  }
  return rows;
}

/* A nyers side-by-side: balra a régi sorszámmal (a változatlan soré is). */
function splitRows(h, lang) {
  const side = (l, no) => (l ? `<div class="half${kindOf(l)}">${diffCell(l, no, lang)}</div>`
    : '<div class="half none"></div>');
  let old = h.old;
  return alignRows(h.lines, partnerIn(h)).map(r => {
    const left = side(r.a, r.ctx ? old : r.a?.n);
    if (r.a) old++;
    return `<div class="split-row mono">${left}${side(r.b, r.b?.n)}</div>`;
  }).join('');
}
