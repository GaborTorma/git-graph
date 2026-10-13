/* A sorok, a commit-fej és a fejléc elrendezése a szélesség szerint. Az ablak
   (Artifact-panel) átméretezése sortörést és nézetváltást hozhat: a sorok
   Y-pozíciója elmozdul, a gráfnak követnie kell. */
import { OPEN_PANEL, rowsEl } from './dom.js';
import { drawGraph } from './graph.js';

/* Méretfigyelő: `fn` csak szélességváltozásra fut (a magasság a tördeléstől is
   változik, arra nem kell újramérni), `always` minden változásra. */
function onWidth(el, fn, always) {
  let width = 0;
  new ResizeObserver(() => {
    if (el.clientWidth !== width) { width = el.clientWidth; fn(); }
    always?.();
  }).observe(el);
}
onWidth(rowsEl, () => { fitRows(); fitWho(); }, drawGraph);

/* A kinyitott commit fejében a szerző neve elmarad, ha nem fér ki (nagyon
   hosszú név, keskeny panel): csak az avatar marad, a név tooltipben, és a
   dátum előtti pont sem kell. Avatar nélkül a név marad. */
export function fitWho() {
  const who = document.querySelector(`${OPEN_PANEL} .who`);
  const img = who?.querySelector('img');
  if (!img) return;
  who.classList.remove('face-only');
  img.removeAttribute('data-tip');
  if (who.scrollWidth > who.parentElement.clientWidth) {
    who.classList.add('face-only');
    img.dataset.tip = img.alt;
  }
}

/* A commit-sor elrendezése a szövegoszlop szélességétől (`.row-in`) függ, fix
   határokkal — így egy adott szélességen minden sima sor ugyanúgy néz ki:
     ≥ 480 px  egysoros: tárgy … idő · avatar · diff
     < 480 px  kétsoros (`.two`): fent a tárgy, lent jobbra idő · avatar · diff
   A lista nem szűkül 320 px alá (page.css: `.graph-wrap`). A badge-es sorokat
   mérni kell, mert a badge-ek hossza soronként más: ha a tárgy 260 px alá
   szorulna, vagy a lista kétsoros, kétsorosak (`.tight`: lent balra a badge-ek,
   jobbra a blokk); ha a blokk a badge-ek mellett nem fér el, egészben a
   harmadik sorba kerül (`.three`). Minden lépés előbb mér, aztán ír. */
const ROW_ONE = 480, SQUEEZE = 260;
const squeezed = r => {
  const s = r.querySelector('.subject');
  return s.scrollWidth > s.clientWidth && s.clientWidth < SQUEEZE;
};
export function fitRows() {
  const rows = [...rowsEl.querySelectorAll('.row')];
  for (const r of rows) r.classList.remove('two', 'tight', 'three');
  const width = rowsEl.querySelector('.row-in')?.clientWidth ?? 0;
  const one = width >= ROW_ONE;
  const tight = rows.filter(r => r.querySelector('.refs') && (!one || squeezed(r)));
  if (!one) for (const r of rows) if (!r.querySelector('.refs')) r.classList.add('two');
  for (const r of tight) r.classList.add('tight');
  // Ha a badge-ek mellett nem fér el az idő · avatar · diff blokk, a badge-ek
  // tördelődnek (`.three`): a blokk az utolsó sorukba, ha ott sincs hely, alá.
  // Zsúfolt: a badge-ek kilógnak, vagy egy badge neve már rövidülne (`…`) a blokk mellett.
  const crowded = r => {
    const f = r.querySelector('.refs');
    return f.scrollWidth > f.clientWidth
      || [...f.querySelectorAll('.badge-name')].some(n => n.scrollWidth > n.clientWidth + 1);
  };
  for (const r of tight.filter(crowded)) r.classList.replace('tight', 'three');
}

/* Fejléc: három csoport (repó, szűrők, eszközök), szélesség szerint 1–3
   sorban. A kapcsolók felirata helyett ikon (`compact`, a felirat tooltipben
   marad), ha a felirat miatt több sorba törne, vagy a szűrők sorából kilógna.
   Több sorban az ágválasztó tölti ki a szűrők sorát (a kapcsolók így jobbra
   kerülnek), három sorban a HEAD-chip is jobbra zár. A kereső mindig kitölti
   a saját sorát. */
const chromeEl = document.querySelector('.chrome');
const filtersEl = chromeEl.querySelector('.filters');
function chromeRows() {
  let rows = 0, bottom = -Infinity;
  for (const g of chromeEl.children) {
    const r = g.getBoundingClientRect();
    if (r.top >= bottom - 1) { rows++; bottom = r.bottom; } else bottom = Math.max(bottom, r.bottom);
  }
  return rows;
}
export function fitChrome() {
  chromeEl.classList.remove('compact', 'multi', 'rows-3');
  const labeled = chromeRows();
  let rows = labeled;
  if (labeled > 1) {
    chromeEl.classList.add('compact');
    rows = chromeRows();
    if (rows > 1 && rows === labeled) {           // így is törne: a felirat maradhat, ha kifér
      chromeEl.classList.remove('compact');
      if (filtersEl.scrollWidth > filtersEl.clientWidth) chromeEl.classList.add('compact');
    }
  }
  chromeEl.classList.toggle('multi', rows > 1);
  chromeEl.classList.toggle('rows-3', rows > 2);
}
onWidth(chromeEl, fitChrome);
