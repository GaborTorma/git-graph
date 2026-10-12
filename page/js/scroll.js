/* A lista görgetése: commitonként lépés, napfejlécek, a kijelölt elem a nézetben. */
import { OPEN_PANEL, pendingEl, rowsEl, scroller } from './dom.js';
import { hideOwnEdge } from './graph.js';

/* A kinyitott commit (sor + panel) egészben a nézetbe: ha elfér, úgy görget,
   hogy az egész látsszon; ha nem, `alignTall` esetén a sora kerül a
   napfejléc alá, különben marad, ahogy van. */
function commitInView(panel, alignTall) {
  const row = panel.previousElementSibling?.classList.contains('row') ? panel.previousElementSibling : null;
  const s = scroller.getBoundingClientRect();
  const top = (row || panel).getBoundingClientRect().top, bottom = panel.getBoundingClientRect().bottom;
  if (bottom - top > s.height - STEP_TOP) {
    if (alignTall) scroller.scrollTop -= Math.round(s.top + STEP_TOP - top);
    return;
  }
  if (top < s.top + STEP_TOP) scroller.scrollTop -= Math.round(s.top + STEP_TOP - top);
  else if (bottom > s.bottom) scroller.scrollTop += Math.round(bottom - s.bottom);
}

/* Lefelé haladva (görgetés, nyíl): ha a kinyitott commit sora előbukkan, de a
   panelje a nézet alá lógna, az egész commit kerül a nézetbe. */
function revealExpandedBelow() {
  const panel = rowsEl.querySelector(OPEN_PANEL);
  const row = panel?.previousElementSibling;
  if (!row?.classList.contains('row')) return;
  const s = scroller.getBoundingClientRect(), r = row.getBoundingClientRect();
  if (r.top < s.bottom && r.bottom > s.top && panel.getBoundingClientRect().bottom > s.bottom) {
    commitInView(panel, true);
  }
}

/* Egy commit sorához ugrik a lista (a napfejléc alá); a sor, vagy null, ha szűrés miatt
   nincs a listában. A `revealSha` rá is állítja a fókuszt. */
export function scrollToSha(sha) {
  const row = sha && rowsEl.querySelector(`.row[data-sha="${CSS.escape(sha)}"]`);
  if (!row) return null;
  const top = row.getBoundingClientRect().top - scroller.getBoundingClientRect().top + scroller.scrollTop;
  scroller.scrollTop = Math.max(0, Math.round(top - STEP_TOP));
  return row;
}
export const revealSha = sha => scrollToSha(sha)?.focus({ preventScroll: true });

export const rowOf = c => c && document.querySelector(`.row[data-sha="${CSS.escape(c.sha)}"]`);

/* A kijelölt elem látszódjon: a ragadós napfejléc alá, vagy az alsó szélhez. */
function ensureVisible(el) {
  // A panelen belül (fájl, blokk) a panel görget; maga a panel kifér a nézetbe.
  const panel = el.closest('.details');
  if (panel && panel !== el) {
    const p = panel.getBoundingClientRect(), r = el.getBoundingClientRect();
    if (r.top < p.top || r.height > p.height) panel.scrollTop -= Math.round(p.top - r.top);
    else if (r.bottom > p.bottom) panel.scrollTop += Math.round(r.bottom - p.bottom);
    if (scroller.contains(panel)) commitInView(panel, true);
    return;
  }
  if (!scroller.contains(el)) return;                    // a fix #pending sor
  const s = scroller.getBoundingClientRect(), r = el.getBoundingClientRect();
  // Ami nem fér ki (magas blokk), annak a teteje igazodik a fejléc alá.
  if (r.top < s.top + STEP_TOP || r.height > s.height - STEP_TOP) {
    scroller.scrollTop -= Math.round(s.top + STEP_TOP - r.top);
  }
  else if (r.bottom > s.bottom) scroller.scrollTop += Math.round(r.bottom - s.bottom);
}
export function select(el) {
  if (!el) return false;
  el.focus({ preventScroll: true });
  ensureVisible(el);
  // A kinyitott commit sorára lépve: ha a panelje a nézet alá lóg, az egész commit a nézetbe.
  if (el.getAttribute('aria-expanded') === 'true') revealExpandedBelow();
  return true;
}

/* A felül ragadó nap fejléce egyben tűnik el, amikor az alja eléri a
   következő nap fejlécét — nem csúszik ki fokozatosan, nem lóg rá a másikra. */
export function stackDays() {
  scroller.classList.toggle('scrolled', scroller.scrollTop > 0);
  pendingEl.classList.toggle('scrolled', scroller.scrollTop > 0);
  hideOwnEdge();
  const days = [...rowsEl.querySelectorAll('.day')];
  const top = scroller.getBoundingClientRect().top, scrolled = scroller.scrollTop > 0;
  // Előbb minden mérés, aztán az írás: a görgetés minden képkockáján fut, a
  // váltakozó olvasás-írás napfejlécenként újratördelést kényszerítene.
  const ys = days.map(d => d.getBoundingClientRect().top), hs = days.map(d => d.offsetHeight);
  // A napfejléc mellett: a nap hány sora van a fejléc fölött (`↑`, alá csúszva) és
  // alatta (`↓`) — a kettő összege mindig a nap összes sora. Csak a nézetbe érő
  // napokat méri; a többinél minden sor a fejléc alatt van.
  const bottom = scroller.getBoundingClientRect().bottom;
  const counts = days.map((d, i) => {
    const rows = d.parentElement.getElementsByClassName('row');   // élő gyűjtemény: olcsó
    let up = 0;
    const group = d.parentElement.getBoundingClientRect();
    if (group.bottom > top && group.top < bottom) {
      const line = ys[i] + hs[i];
      for (const r of rows) if (r.getBoundingClientRect().top < line - 0.5) up++;
    }
    const down = rows.length - up;
    return [up && `↑${up}`, down && `↓${down}`].filter(Boolean).join(' ');
  });
  days.forEach((d, i) => {
    d.classList.toggle('gone', i + 1 < days.length && ys[i + 1] - ys[i] <= hs[i] + 0.5);
    // Felül ragadva (`.stuck`) a vonal nem kell, csak a felirat.
    d.classList.toggle('stuck', scrolled && ys[i] - top <= 0.5);
    const cnt = d.querySelector('.cnt'), text = counts[i] ? ` · ${counts[i]}` : '';
    if (cnt && cnt.textContent !== text) cnt.textContent = text;
  });
}
scroller.addEventListener('scroll', stackDays, { passive: true });

/* Commitonként görgetés: egy görgő-kattanás egy commit, trackpaden ~40 px
   egy commit. A sor a ragadós napfejléc alá (`STEP_TOP`) igazodik, így a fejléc
   sosem takarja. A CSS scroll-snap ezt nem tartja (a böngésző egy
   kattanással több sort is átugrik). Ha egy kinyitott commit-panel látszik,
   azon belül szabad a görgetés — a következő lépés újra sorhoz igazít. */
export const STEP_TOP = 16, TRACKPAD_STEP = 40, NOTCH = 50;

// Ennyi időn belül egy irány nem növekvő eseményei lecsengésnek számítanak.
const COAST_MS = 120;
let wheelAcc = 0, stepDir = 0;
const lastMag = { 1: 0, '-1': 0 }, lastAt = { 1: -1e9, '-1': -1e9 };
/* Egy lépés: azonnal, animáció nélkül (az animáció — a böngészőé és a saját
   ease-out is — darabosnak, irányváltáskor késlekedőnek tűnt). */
function stepRows(dir) {
  const base = scroller.getBoundingClientRect().top - scroller.scrollTop;
  const tops = [...rowsEl.querySelectorAll('.row')]
    .map(r => Math.max(0, Math.round(r.getBoundingClientRect().top - base - STEP_TOP)));
  stepDir = dir;
  const from = scroller.scrollTop;
  const max = scroller.scrollHeight - scroller.clientHeight;
  const target = dir > 0 ? (tops.find(t => t > from + 1) ?? max)
                         : ([...tops].reverse().find(t => t < from - 1) ?? 0);
  scroller.scrollTop = Math.min(target, max);
  if (dir > 0) revealExpandedBelow();
}
scroller.addEventListener('wheel', e => {
  if (e.ctrlKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
  const panel = rowsEl.querySelector(OPEN_PANEL);
  if (panel) {
    const r = panel.getBoundingClientRect(), s = scroller.getBoundingClientRect();
    if (r.top < s.bottom && r.bottom > s.top + STEP_TOP + 1) return;
  }
  e.preventDefault();
  const px = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaMode === 2 ? e.deltaY * scroller.clientHeight : e.deltaY;
  if (!px) return;
  const sgn = Math.sign(px), mag = Math.abs(px), now = performance.now();
  // Lecsengés: ugyanabban az irányban, rövid időn belül, nem növekvő nagyságú
  // esemény — a simító egérszoftver (BetterMouse) lendülete. Fordulás után ez a
  // régi irányból még az új irány eseményei KÖZÉ is beérkezhet.
  const coasting = now - lastAt[sgn] < COAST_MS && mag <= lastMag[sgn] * 1.15;
  lastMag[sgn] = mag;
  lastAt[sgn] = now;
  if (stepDir && sgn !== stepDir) {
    if (coasting) return;                 // a régi irány lendülete: nem fordít vissza
    // Valódi fordulás: azonnal lép (az új irány első eseményei kicsik, nem kell
    // kivárni a küszöböt), és a régi irány maradéka sem tartja fel.
    wheelAcc = 0;
    stepRows(sgn);
    return;
  }
  if (wheelAcc && Math.sign(px) !== Math.sign(wheelAcc)) wheelAcc = 0;
  wheelAcc += px;
  if (Math.abs(px) < NOTCH && Math.abs(wheelAcc) < TRACKPAD_STEP) return;
  const dir = Math.sign(wheelAcc);
  wheelAcc = 0;
  stepRows(dir);
}, { passive: false });
