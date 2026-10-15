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
  annotate(d);
  let uni = '', split = '', oldEnd = 1;
  const kinds = new Set();
  for (const h of d.hunks) {
    const gap = h.old - oldEnd;
    const gapHtml = gap > 0 ? `<p class="diff-gap" title="${gap} változatlan sor">···</p>` : '';
    const lines = oneSide(h.lines);
    for (const l of lines) kinds.add(l.t);
    // Egy blokk (hunk) a `···`-ig: fókuszálható, a nyilak blokkról blokkra lépnek.
    uni += gapHtml + '<div class="hunk" tabindex="-1">' + lines.map(l => `<div class="diff-line mono${kindOf(l)}">`
      + diffCell(l, l.n, lang) + '</div>').join('') + '</div>';
    split += gapHtml + '<div class="hunk" tabindex="-1">' + splitRows(h, lang) + '</div>';
    oldEnd = h.old + h.lines.filter(l => l.t !== '+').length;
  }
  const oneSided = !(kinds.has('+') && kinds.has('-'));   // a változatlan sor nem számít
  return (oneSided ? `<div>${uni}</div>`
    : `<div class="diff-uni">${uni}</div><div class="diff-split">${split}</div>`)
    + (d.truncated ? '<p class="diff-note">… a diff túl hosszú, a vége le van vágva.</p>' : '');
}

/* A sor párja (a Python `pair_lines`-a: `p` a törölt sor párjának hunkbeli
   indexe), mindkét irányban, és a megjelenése (`styles`): a diff betöltésekor
   egyszer, hunkonként (`annotate`) — így minden nézet (egymás alatti,
   side-by-side, markdown) ugyanazt látja, bármelyik szeletét rajzolja. A
   sorokon kívül tárolva: az adat gyorstárazott, és az élő frissítés
   JSON-összevetéssel nézi, változott-e. */
const PAIR = new WeakMap(), LOOK = new WeakMap(), DONE = new WeakSet();
export const partnerOf = l => PAIR.get(l) ?? null;
export function annotate(d) {
  for (const h of d.hunks) {
    if (DONE.has(h)) continue;
    DONE.add(h);
    for (const l of h.lines) if (l.p != null) { PAIR.set(l, h.lines[l.p]); PAIR.set(h.lines[l.p], l); }
    for (const [l, s] of styles(h.lines)) LOOK.set(l, s);
  }
}

export const KIND = { ' ': '', '+': ' add', '-': ' del' };
export const kindOf = l => KIND[l.t] + (l.only ? ' only' : '');

/* Változott-e a sor (a Python `w`-je): `same` — a szavai mind megvannak a
   másik oldalon (vagy üres sor); `words` / `whole` — szavai változtak / egészében
   új vagy törölt. `untouched`: a `t` oldalon egy sem változott. */
const changed = l => l.t !== ' ' && l.w !== 'same';
export const untouched = (ls, t) => !ls.some(l => l.t === t && changed(l));

/* Melyik változott sor érintetlen (`drop`: a szavai mind megvannak a másik
   oldalon), melyik a párja (`only`: a háttere semleges, csak a változott szavai
   színesek, `kindOf`), és melyik nem változott maga sem (`same`: újratördelés).
   Egy futamban (törölt + hozzáadott sorok): ha mindkét oldala érintetlen, tiszta
   újratördelés; ha az egyik, az az oldal (csak beszúrás / csak törlés); különben
   páronként, pl. egy táblázat egyetlen sorában csak törlés, a többiben csere. Az
   egészében új / törölt sor (`whole`) teljes színű marad. */
function styles(lines) {
  const st = new Map();
  const kept = l => (l.w === 'words' ? 'only' : l.w === 'same' ? 'same' : null);
  for (let i = 0; i < lines.length;) {
    if (lines[i].t === ' ') { i++; continue; }
    let j = i; while (j < lines.length && lines[j].t !== ' ') j++;
    const run = lines.slice(i, j);
    i = j;
    if (!run.some(l => l.t === '+') || !run.some(l => l.t === '-')) continue;
    const drop = untouched(run, '-') ? '-' : untouched(run, '+') ? '+' : null;
    if (drop) {
      for (const l of run) st.set(l, l.t === drop ? 'drop' : kept(l));
      continue;
    }
    const inRun = new Set(run);
    for (const d of run) {
      const a = d.t === '-' ? partnerOf(d) : null;
      if (!a || !inRun.has(a)) continue;
      const [x, y] = !changed(d) ? [d, a] : !changed(a) ? [a, d] : [];
      if (x) { st.set(x, 'drop'); st.set(y, kept(y)); }
    }
  }
  return st;
}
// a sor a `styles` szerint: az érintetlen (`drop`) és a változatlan (`same`) jel
// nélkül, az `only` semleges háttérrel
const look = l => {
  const s = LOOK.get(l);
  return s === 'drop' || s === 'same' ? { ...l, t: ' ' } : s === 'only' ? { ...l, only: true } : l;
};

/* Az egymás alatti nézet sorai (`annotate` után): az érintetlen oldal kimarad —
   a másik oldal a kiemelt szavaival mindent elmond. */
export function oneSide(lines) {
  return lines.filter(l => LOOK.get(l) !== 'drop').map(look);
}

const diffCell = (l, no, lang) => `<span class="no">${no ?? ''}</span>`
  + `<span class="sg">${l.t === ' ' ? '' : l.t === '-' ? '−' : '+'}</span>`
  + `<span class="tx">${highlight(l.s, l.hl, lang)}</span>`;

/* Side-by-side sorai (`annotate` után): [{ a: régi, b: új, ctx }]. A változatlan
   sor mindkét oldalon (`ctx`), a törölt blokk és az utána jövő hozzáadott blokk
   párjai (`partnerOf`) egy sorba — ugyanaz a párosítás, amiből a Python a
   szó-kiemelést számolja. A két pár közti pár nélküli törölt és új sorok egymás
   mellé kerülnek (a többlet egyedül, a másik oldal `null`). Egészében egyoldalú
   futamban (csak beszúrás / csak törlés) az érintetlen oldal változatlanként
   látszik, a párok nem számítanak: a két oldal felülről, lyuk nélkül. */
export function alignRows(L) {
  const at = new Map(L.map((l, i) => [l, i]));
  const see = l => l && look(l);
  const rows = [];
  for (let i = 0; i < L.length;) {
    if (L[i].t === ' ') { rows.push({ a: L[i], b: L[i], ctx: true }); i++; continue; }
    let j = i; while (j < L.length && L[j].t === '-') j++;
    let k = j; while (k < L.length && L[k].t === '+') k++;
    const row = (d, n) => rows.push({ a: see(d), b: see(n) });
    const pair = d => { const x = at.get(partnerOf(L[d])); return x >= j && x < k ? x : null; };
    const run = L.slice(i, k);
    const pairs = [];
    if (!untouched(run, '-') && !untouched(run, '+')) {
      for (let d = i, last = j; d < j; d++) {
        const p = pair(d);
        if (p != null && p >= last) { pairs.push([d, p]); last = p + 1; }
      }
    }
    let d0 = i, a0 = j;
    for (const [d, p] of [...pairs, [j, k]]) {
      for (let x = 0; x < Math.max(d - d0, p - a0); x++) {
        row(d0 + x < d ? L[d0 + x] : null, a0 + x < p ? L[a0 + x] : null);
      }
      if (d < j) row(L[d], L[p]);
      d0 = d + 1; a0 = p + 1;
    }
    i = k;
  }
  return rows;
}

/* A nyers side-by-side: balra a régi sorszámmal (a változatlan soré is). */
function splitRows(h, lang) {
  const side = (l, no) => (l ? `<div class="half${kindOf(l)}">${diffCell(l, no, lang)}</div>`
    : '<div class="half none"></div>');
  let old = h.old;
  return alignRows(h.lines).map(r => {
    const left = side(r.a, r.ctx ? old : r.a?.n);
    if (r.a) old++;
    return `<div class="split-row mono">${left}${side(r.b, r.b?.n)}</div>`;
  }).join('');
}
