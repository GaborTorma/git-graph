/* A kinyitott commit panelje: méret, és ami a nézetbe kerül nyitáskor. */
import { glide } from './anim.js';
import { OPEN_PANEL, pendingEl, scroller } from './dom.js';
import { drawGraph } from './graph.js';
import { STEP_TOP } from './scroll.js';

/* A kinyitott panel legfeljebb akkora, hogy a saját sora, ő maga és a
   következő commit sora együtt kiférjen a nézetbe; a többi a panelen belül görget.
   A fix sávban (saját WIP) a panel alja a lap magasságának 80%-áig érhet. */
const PANEL_MIN = 120, PENDING_MAX = 0.8;
export function fitPanel() {
  const panel = document.querySelector(OPEN_PANEL);
  if (!panel) return;
  const keep = panel.scrollTop;
  let room;
  if (pendingEl.contains(panel)) {
    room = innerHeight * PENDING_MAX - panel.getBoundingClientRect().top;
  } else {
    // Az alatta lévő commit sora (másik napé: a napfejléccel együtt).
    const cs = getComputedStyle(panel);
    const next = rowAfter(panel);
    const near = next ? next.gap + next.row.offsetHeight : 0;
    room = scroller.clientHeight - STEP_TOP - /** @type {HTMLElement} */ (panel.previousElementSibling).offsetHeight
      - parseFloat(cs.marginTop) - parseFloat(cs.marginBottom) - near;
  }
  panel.style.maxHeight = `${Math.max(PANEL_MIN, Math.floor(room))}px`;
  panel.scrollTop = keep;
}
new ResizeObserver(() => { fitPanel(); drawGraph(); }).observe(scroller);

/* Lenyitáskor a commit (sor + panel) és a következő commit sora a nézetbe
   kerül; ha ehhez fel kell ugrania, a sora a napfejléc alá. A `fitPanel` a
   magasságot ehhez szabja, így együtt kiférnek. */
function rowAfter(panel) {
  if (panel.nextElementSibling?.classList.contains('row')) return { row: panel.nextElementSibling, gap: 0 };
  const row = panel.parentElement.nextElementSibling?.querySelector('.row');   // a következő napé
  return row ? { row, gap: STEP_TOP } : null;
}
export function revealCommit(panel, smooth = false) {
  if (!scroller.contains(panel)) return;
  const s = scroller.getBoundingClientRect();
  const next = rowAfter(panel)?.row;
  const top = panel.previousElementSibling.getBoundingClientRect().top;
  const bottom = (next || panel).getBoundingClientRect().bottom;
  const delta = top < s.top + STEP_TOP ? top - s.top - STEP_TOP
    : bottom > s.bottom ? Math.min(bottom - s.bottom, top - s.top - STEP_TOP) : 0;
  if (smooth) glide(scroller, delta); else scroller.scrollTop += Math.round(delta);
}

/* Egérrel lenyitott fájl (fejléc + diff) a panelen belül a nézetbe — ahogy a
   billentyűzettel az első blokkja; ha mellette a következő fájl sora is
   elfér, az is látszik. Ami nem fér el, annak a fejléce kerül felülre. */
export function revealFile(fileEl) {
  const panel = fileEl.closest('.details');
  if (!panel) return;
  const p = panel.getBoundingClientRect();
  const top = fileEl.getBoundingClientRect().top, next = nextFile(fileEl);
  let bottom = fileEl.nextElementSibling.getBoundingClientRect().bottom;
  if (next && next.getBoundingClientRect().bottom - top <= p.height) bottom = next.getBoundingClientRect().bottom;
  glide(panel, top < p.top ? top - p.top : bottom > p.bottom ? Math.min(bottom - p.bottom, top - p.top) : 0);
}

/* Ha a fix sáv panelje csukódik fel, a lista nézete nő: az új panel mérete
   és helye képkockánként ehhez igazodik. */
export function followPending(panel) {
  return () => { if (panel.isConnected) { fitPanel(); revealCommit(panel); } };
}

export const nextFile = fileEl => {
  const files = [...fileEl.parentElement.querySelectorAll('.file')];
  return files[files.indexOf(fileEl) + 1];
};
