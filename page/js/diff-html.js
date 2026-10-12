/* A nyers diff HTML-je: egymás alatti és side-by-side nézet. */
import { highlight } from './syntax.js';

/* Mindkét nézet elkészül (egymás alatti és side-by-side); hogy melyik látszik,
   azt a `.diff` szélessége dönti el egy container queryvel — átméretezéskor
   újrarenderelés nélkül vált. Ha a diffben csak hozzáadás vagy csak törlés van
   (új fájl, vagy beszúrás / kivágás a változatlan sorok közt), a side-by-side
   egyik oldala végig üres lenne: ott csak az egymás alatti nézet készül.
   Hunkok közt a kihagyott sorok száma a régi oldal sorszámaiból jön. */
export function diffHtml(d, lang) {
  if (d.binary) return '<p class="diff-note">Bináris fájl.</p>';
  if (!d.hunks.length) return '<p class="diff-note">Nincs megjeleníthető változás.</p>';
  let uni = '', split = '', oldEnd = 1;
  for (const h of d.hunks) {
    const gap = h.old - oldEnd;
    const gapHtml = gap > 0 ? `<p class="diff-gap" title="${gap} változatlan sor">···</p>` : '';
    // Egy blokk (hunk) a `···`-ig: fókuszálható, a nyilak blokkról blokkra lépnek.
    uni += gapHtml + '<div class="hunk" tabindex="-1">' + h.lines.map(l => `<div class="diff-line mono${KIND[l.t]}">`
      + diffCell(l, l.n, lang) + '</div>').join('') + '</div>';
    split += gapHtml + '<div class="hunk" tabindex="-1">' + splitRows(h, lang) + '</div>';
    oldEnd = h.old + h.lines.filter(l => l.t !== '+').length;
  }
  const kinds = new Set(d.hunks.flatMap(h => h.lines.map(l => l.t)));
  const oneSided = !(kinds.has('+') && kinds.has('-'));   // a változatlan sor nem számít
  return (oneSided ? `<div>${uni}</div>`
    : `<div class="diff-uni">${uni}</div><div class="diff-split">${split}</div>`)
    + (d.truncated ? '<p class="diff-note">… a diff túl hosszú, a vége le van vágva.</p>' : '');
}

export const KIND = { ' ': '', '+': ' add', '-': ' del' };
const diffCell = (l, no, lang) => `<span class="no">${no ?? ''}</span>`
  + `<span class="sg">${l.t === ' ' ? '' : l.t === '-' ? '−' : '+'}</span>`
  + `<span class="tx">${highlight(l.s, l.hl, lang)}</span>`;

/* Side-by-side: a változatlan sor mindkét oldalon (balra a régi sorszámmal), a
   törölt blokk és az utána jövő hozzáadott blokk párjai (`p`, a Python
   `pair_lines`-a) egy sorba, a pár nélküliek egyedül, a párok közé —
   ugyanaz a párosítás, amiből a Python a szó-kiemelést számolja. */
function splitRows(h, lang) {
  const L = h.lines, side = (l, no) => l
    ? `<div class="half${KIND[l.t]}">${diffCell(l, no, lang)}</div>` : '<div class="half none"></div>';
  let out = '', old = h.old, i = 0;
  while (i < L.length) {
    if (L[i].t === ' ') {
      out += `<div class="split-row mono">${side(L[i], old)}${side(L[i], L[i].n)}</div>`;
      old++; i++;
      continue;
    }
    let j = i; while (j < L.length && L[j].t === '-') j++;
    let k = j; while (k < L.length && L[k].t === '+') k++;
    const row = (del, add) =>
      out += `<div class="split-row mono">${side(del, del?.n)}${side(add, add?.n)}</div>`;
    let a = j;
    for (let d = i; d < j; d++) {
      if (L[d].p == null) { row(L[d], null); continue; }
      while (a < L[d].p) row(null, L[a++]);
      row(L[d], L[a++]);
    }
    while (a < k) row(null, L[a++]);
    old += j - i; i = k;
  }
  return out;
}
