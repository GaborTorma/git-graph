/* ── Képek a diffben ──
   A képfájl diffje (a `file_diff` `image`-e: a két oldal data URI-ja, az `IMAGE_MAX`
   fölött csak a mérete — a CSP külső képet nem enged) és a markdown-nézet képei
   (`![alt](út)`: a lap képenként kéri, a `file_diff` `image` argumentumával, oldalanként
   a saját változatból). Az elrendezés a Mermaid-diagramoké (`.md-mmd-view`): az új vagy
   törölt kép egyedül, balra, színes bal csíkkal; a változott pár a középvonalon
   találkozik (a régi jobbra, az új balra igazítva), teljes színes kerettel, és ha nem
   fér el, egymás alá törik, mindkettő balra (`fitImages`). A változatlan (pl. átnevezett)
   kép egyszer, semleges kerettel. Az átlátszó kép mögött sakktábla (page.css). */
import { esc } from './util.js';

export const IMAGE_RE = /\.(png|jpe?g|gif|webp|avif|svg|ico|bmp)$/i;
const FRAME = 12;            // a keret belső margója és szegélye két oldalon (`.img-fig`)
const GAP = 6;               // a pár köze (`.img-view`)

const mb = n => `${(n / 1048576).toFixed(1).replace('.', ',')} MB`;

/* Egy oldal kerete: a kép, vagy ha túl nagy, a mérete, ha nincs meg, az alt szöveg. Az
   `alt` már HTML-biztos. */
function figHtml(side, cls, alt) {
  if (!side) return `<div class="img-fig img-miss${cls}"><span class="md-img">${alt}</span> <span class="img-note">nem található</span></div>`;
  if (!side.uri) return `<div class="img-fig img-big${cls}"><span class="img-note">Túl nagy kép (${mb(side.size)}).</span></div>`;
  return `<div class="img-fig${cls}"><img src="${side.uri}" alt="${alt}"></div>`;
}

/* A kép két oldala (`image_side`; `null`: azon az oldalon nincs meg) a páros
   elrendezésben. `had` / `has`: van-e régi / új oldal — új fájlnál, új bekezdésnél
   nincs régi, ott az egy kép zöld csíkkal; töröltnél piros. */
export function imagesHtml(old, now, alt, had = true, has = true) {
  const same = old?.uri ? old.uri === now?.uri : !old && !now;
  const figs = !had ? [figHtml(now, ' img-add img-whole', alt)]
    : !has ? [figHtml(old, ' img-del img-whole', alt)]
    : same ? [figHtml(now, '', alt)]
    : [figHtml(old, ' img-del', alt), figHtml(now, ' img-add', alt)];
  return `<div class="img-view">${figs.map(f => `<div class="img-half">${f}</div>`).join('')}</div>`;
}

/* A képfájl diffje: a kép, egy oldalon nincs meg, ha a commit hozzáadta / törölte. */
export function imageDiffHtml(d, path) {
  const { old, new: now } = d.image;
  if (!old && !now) return '<p class="diff-note">Nincs megjeleníthető változás.</p>';
  const name = path.replace(/\{[^{}]* => ([^{}]*)\}/, '$1').split(' => ').pop().split('/').pop();
  return imagesHtml(old, now, esc(name), !!old, !!now);
}

/* A pár egymás mellé fér-e: a keretek a kép természetes szélességéig nőnek (a fél
   legalább ekkora, ha a hely engedi), és ha együtt nem férnek el, egymás alá kerülnek,
   mindkettő balra (`img-stack`). A még be nem töltött kép a betöltése után igazít. */
function fit(view) {
  const halves = [...view.children].filter(h => h.classList.contains('img-half'));
  if (!halves.length) return;
  const widths = halves.map(h => {
    const fig = /** @type {HTMLElement} */ (h.firstElementChild), img = fig?.querySelector('img');
    if (img) return (img.naturalWidth || 150) + FRAME;
    fig.style.width = 'max-content';
    const w = fig.offsetWidth;
    fig.style.width = '';
    return w;
  });
  halves.forEach((h, i) => { /** @type {HTMLElement} */ (h).style.minWidth = `min(100%, ${widths[i]}px)`; });
  const room = view.clientWidth;
  view.classList.toggle('img-stack', room > 0 && halves.length > 1
    && widths.reduce((a, b) => a + b, 0) + GAP * (halves.length - 1) > room);
}
export function fitImages(root) {
  for (const view of root.querySelectorAll('.img-view')) {
    const pending = [...view.querySelectorAll('img')].filter(img => !img.complete);
    for (const img of pending) img.addEventListener('load', () => fit(view), { once: true });
    fit(view);
  }
}

/* A markdown-nézet képei: a `get(ref)` a hivatkozott kép két oldalát adja (`{ old, new }`).
   A csak képből álló bekezdés (`.md-pic`, `data-pic`: a régi és az új hivatkozása, az
   alt szöveg) a páros elrendezésben; a szövegbeli kép (`.md-img[data-img]`, `data-side`:
   melyik oldal) a helyén, a sorban. Ami nincs meg, az alt szövege marad, `nem található`
   jelöléssel. A szövegbeli kép betöltése után a `changed` fut (a side-by-side sormagasságai).
   */
export function loadImages(root, get, changed = () => {}) {
  const sides = new Map();
  const fetch = ref => {
    if (!sides.has(ref)) sides.set(ref, get(ref));
    return sides.get(ref);
  };
  for (const el of root.querySelectorAll('.md-pic[data-pic]')) {
    const p = JSON.parse(el.dataset.pic);
    delete el.dataset.pic;
    Promise.all([p.old != null ? fetch(p.old) : null, p.now != null ? fetch(p.now) : null]).then(([a, b]) => {
      if (!el.isConnected) return;
      el.innerHTML = imagesHtml(a?.old ?? null, b?.new ?? null, esc(p.alt), p.old != null, p.now != null);
      fitImages(el);
    }, () => {});
  }
  for (const el of root.querySelectorAll('.md-img[data-img]')) {
    const span = /** @type {HTMLElement} */ (el), ref = span.dataset.img;
    delete span.dataset.img;
    fetch(ref).then(r => {
      const side = span.dataset.side === '-' ? r.old : r.new;
      if (!span.isConnected) return;
      if (side?.uri) {
        const img = Object.assign(document.createElement('img'), { className: 'md-inl', src: side.uri, alt: span.textContent });
        img.addEventListener('load', changed, { once: true });
        span.replaceWith(img);
      } else {
        span.insertAdjacentHTML('afterend', ` <span class="img-note">${side ? `Túl nagy kép (${mb(side.size)}).` : 'nem található'}</span>`);
      }
    }, () => {});
  }
}
