/* ── Képek a diffben ──
   A képfájl diffje (a két oldal data URI-ja, a `file_diff` `side`-dal oldalanként külön
   hívásban, hogy egy válasz a host-híd határa alatt maradjon; az `IMAGE_MAX` fölött csak a
   mérete — a CSP külső képet nem enged) és a markdown-nézet képei (`![alt](út)`: a lap
   képenként kéri, az `image` argumentummal, oldalanként a saját változatából). Az új vagy
   törölt kép egyedül, középen (a markdown-nézetben balra), színes bal csíkkal; a változott
   pár a középvonalon találkozik (a régi jobbra, az új balra igazítva), teljes színes
   kerettel, mindig egymás mellett. A változatlan (pl. átnevezett) kép egyszer, semleges
   kerettel. Az átlátszó kép mögött sakktábla (page.css).

   A kép legfeljebb természetes méretű, és a hasáb (a párnál a fél hasáb) szélességébe és
   a panel látható magasságába illeszkedik (`layout`). A változott pár három nézetben
   vethető össze (`imgMode`, a lap megjegyzi): Side-by-side, Swipe (a régi a vonaltól
   balra, az új jobbra) és Onion skin (az új áttetszősége); a két utóbbiban a pár közös
   léptékkel, középre igazítva fedi egymást. A kép nagyítható (`zoomTo`, legfeljebb
   1600%), a nagyított kivágás húzással mozog; a pár két oldala együtt. A vezérlő a kép
   alján, rámutatásra lebegő sáv (`placeBar`); a teljes lapos nézet (`openFull`) a lapot
   fedi, a sávja mindig látszik. */
import { icon } from './icons.js';
import { esc, fmtBytes } from './util.js';

export const IMAGE_RE = /\.(png|jpe?g|gif|webp|avif|svg|ico|bmp)$/i;
const GAP = 6;               // a pár köze (`.img-view`)
const ZMAX = 16;             // a legnagyobb nagyítás (1600%)
const STEPS = [0.25, 0.5, 1, 2, 4, 8, 16];   // a + / − gomb lépcsői
const LOW = 200;             // ennél alacsonyabb képnél a sáv a kép alatt lebeg, ha ott elfér
const FULL_PAD = 24;         // a teljes lapos nézet margója
const FULL_BAR = 56;         // ... és a sávnak hagyott hely alul
const MODES = { sbs: 'Side-by-side', swipe: 'Swipe', onion: 'Onion skin' };
const MODE_KEYS = { sbs: '2', swipe: 'S', onion: 'O' };   // a teljes lapos nézet billentyűi
const BAR_GAP = 12;          // a sáv és a kép alja között

/* A választott nézet: közös, a lap megjegyzi (mint az `svgCode`). */
const MODE_KEY = 'git-graph:imgMode';
export let imgMode = (() => {
  try { const m = localStorage.getItem(MODE_KEY); return m && m in MODES ? m : 'sbs'; } catch { return 'sbs'; }
})();
export function setImgMode(mode) {
  imgMode = mode;
  try { localStorage.setItem(MODE_KEY, mode); } catch { /* privát ablak: nem baj */ }
  document.querySelectorAll('.img-view[data-modes]').forEach(layout);
}

/* Egy oldal kerete: a kép, vagy ha túl nagy, a mérete, ha nincs meg, az alt szöveg. Az
   `alt` már HTML-biztos. */
function figHtml(side, cls, alt) {
  if (!side) return `<div class="img-fig img-miss${cls}"><span class="md-img">${alt}</span> <span class="img-note">nem található</span></div>`;
  if (!side.uri) return `<div class="img-fig img-big${cls}"><span class="img-note">Túl nagy kép (${fmtBytes(side.size)}).</span></div>`;
  return `<div class="img-fig${cls}"><div class="img-pane"><img src="${side.uri}" alt="${alt}" draggable="false"></div></div>`;
}

/* A sáv: a nézetek (csak a két képpel változott párnál), Onion skinnél az áttetszőség,
   a zoom és a teljes lapos nézet; a teljes lapos nézetben a bezárás. */
const barHtml = (modes, tag = 'div') => `<${tag} class="img-bar">${modes ? Object.entries(MODES).map(([m, label]) =>
  `<button class="mini" data-img-mode="${m}" aria-label="${label}" data-tip="${label}" data-kbd="${MODE_KEYS[m]}">${icon(`img-${m}`)}</button>`).join('')
  + '<input class="img-opacity" type="range" min="0" max="100" step="1" aria-label="Áttetszőség" data-tip="Áttetszőség">' : ''
}<button class="mini" data-img-zoom="-1" aria-label="Kicsinyítés" data-tip="Kicsinyítés" data-kbd="−">${icon('minus')}</button><span class="img-pct"></span
><button class="mini" data-img-zoom="1" aria-label="Nagyítás" data-tip="Nagyítás" data-kbd="+">${icon('plus')}</button
><button class="mini" data-img-full aria-label="Teljes lapos nézet" data-tip="Teljes lapos nézet">${icon('expand')}</button
><button class="mini" data-img-close aria-label="Bezárás" data-tip="Bezárás" data-kbd="Esc">${icon('close')}</button></${tag}>`;

/* A kép két oldala (`image_side`; `null`: azon az oldalon nincs meg) a páros
   elrendezésben. `had` / `has`: van-e régi / új oldal — új fájlnál, új bekezdésnél
   nincs régi, ott az egy kép zöld csíkkal; töröltnél piros. */
export function imagesHtml(old, now, alt, had = true, has = true) {
  const same = old?.uri ? old.uri === now?.uri : !old && !now;
  const figs = !had ? [figHtml(now, ' img-add img-whole', alt)]
    : !has ? [figHtml(old, ' img-del img-whole', alt)]
    : same ? [figHtml(now, '', alt)]
    : [figHtml(old, ' img-del', alt), figHtml(now, ' img-add', alt)];
  const modes = figs.length === 2 && old?.uri && now?.uri;
  const zoom = figs.some(f => f.includes('<img'));
  return `<div class="img-view${figs.length === 2 ? ' img-pair' : ''}"${modes ? ' data-modes' : ''}>${
    figs.map(f => `<div class="img-half">${f}</div>`).join('')}${
    modes ? '<div class="img-line"><span></span></div>' : ''}${zoom ? barHtml(modes) : ''}</div>`;
}

/* A képfájl diffje: a kép, egy oldalon nincs meg, ha a commit hozzáadta / törölte. */
export function imageDiffHtml(d, path) {
  const { old, new: now } = d.image;
  if (!old && !now) return '<p class="diff-note">Nincs megjeleníthető változás.</p>';
  const name = path.replace(/\{[^{}]* => ([^{}]*)\}/, '$1').split(' => ').pop().split('/').pop();
  return imagesHtml(old, now, esc(name), !!old, !!now);
}

/* A nézet állapota: a nagyítás (`z`: a természetes mérethez képest, `null`: illesztett),
   a kivágás közepe a kép arányában (`cx`, `cy`), a Swipe vonala és az áttetszőség (%). */
const states = new WeakMap();
function stateOf(view) {
  if (!states.has(view)) states.set(view, { z: null, cx: 0.5, cy: 0.5, swipe: 0, onion: 100, fit: 1 });
  return states.get(view);
}
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/* A kép helye: a hasáb szélessége és a panel látható magassága a fájlsor alatt, a diff dobozának
   keretén belül, úgy, hogy a következő fájl sora is látsszon (a `fitPanel` a panel legnagyobb
   magasságát írja ki); a teljes lapos nézetben az ablak. */
function room(view) {
  const full = view.closest('.img-full');
  if (full) return { w: full.clientWidth - 2 * FULL_PAD, h: full.clientHeight - FULL_PAD - FULL_BAR };
  const w = view.classList.contains('img-inline') ? view.parentElement.clientWidth : view.clientWidth;
  const panel = view.closest('.details');
  if (!panel) return { w, h: innerHeight };
  const box = /** @type {HTMLElement} */ (view.closest('.diff'));
  const next = /** @type {HTMLElement} */ (box?.nextElementSibling);   // a következő fájl sora: látsszon
  const frame = (el, padding = true) => {
    const cs = getComputedStyle(el);
    return (padding ? parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom) : 0)
      + parseFloat(cs.borderTopWidth) + parseFloat(cs.borderBottomWidth);
  };
  // A panel belső margója görgetéskor kimegy a tartalommal: csak a szegélye számít. A fájlok
  // közti sorköz (`gap`) a fájlsor és a doboz, a doboz és a következő sor között.
  const bs = box && getComputedStyle(box), vs = getComputedStyle(view);
  const gap = box ? parseFloat(getComputedStyle(box.parentElement).rowGap) || 0 : 0;
  const h = (parseFloat(panel.style.maxHeight) || panel.clientHeight) - frame(panel, false)
    - (/** @type {HTMLElement} */ (box?.previousElementSibling)?.offsetHeight || 0)
    - (box ? gap + frame(box) + parseFloat(bs.marginTop) + (next ? parseFloat(bs.marginBottom) + gap + next.offsetHeight : 0) : 0)
    - parseFloat(vs.marginTop) - parseFloat(vs.marginBottom);
  return { w, h };
}

const isSvg = img => img.src.startsWith('data:image/svg');
const halvesOf = view => /** @type {HTMLElement[]} */ ([...view.children].filter(h => h.classList.contains('img-half')));

/* A nézet elrendezése: a pane-ek (a kép látható kerete) mérete, benne a kép a nagyítással
   és a kivágással; Swipe / Onion skinnél a vonal és az áttetszőség. Ha egy kép még nem
   töltődött be, a betöltése után fut (`fitImages`). */
function layout(view) {
  if (!view.isConnected) return;
  if (!view.clientWidth && !view.closest('.img-full')) return;   // becsukott diff: nyitáskor újra
  const halves = halvesOf(view);
  // a betöltetlen kép a betöltése után; a dekódolhatatlan (`complete`, de mérete nincs) kimarad
  const imgs = halves.map(h => h.querySelector('img')).map(i => i && i.complete && !i.naturalWidth ? null : i);
  if (!imgs.some(Boolean) || imgs.some(i => i && !i.naturalWidth)) return;
  const st = stateOf(view);
  const mode = view.hasAttribute('data-modes') ? imgMode : 'sbs';
  const over = mode !== 'sbs';
  view.dataset.mode = mode;
  view.classList.toggle('img-over', over);
  view.querySelectorAll('[data-img-mode]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.imgMode === mode)));
  const fig = imgs.find(Boolean).closest('.img-fig'), fs = getComputedStyle(fig);
  const frameX = parseFloat(fs.paddingLeft) + parseFloat(fs.paddingRight) + parseFloat(fs.borderLeftWidth) + parseFloat(fs.borderRightWidth);
  const frameY = parseFloat(fs.paddingTop) + parseFloat(fs.paddingBottom) + parseFloat(fs.borderTopWidth) + parseFloat(fs.borderBottomWidth);
  const r = room(view);
  const maxW = Math.max(1, (over || halves.length < 2 ? r.w : (r.w - GAP) / 2) - frameX);
  const maxH = Math.max(1, r.h - frameY);
  // A „vászon”: Side-by-side-ban a kép maga, a fedő nézetekben a két kép közös kerete.
  const nat = imgs.map(i => i && [i.naturalWidth, i.naturalHeight]);
  const canvases = over
    ? nat.map(() => [Math.max(nat[0][0], nat[1][0]), Math.max(nat[0][1], nat[1][1])]) : nat;
  const fits = canvases.map(c => c && Math.min(1, maxW / c[0], maxH / c[1]));
  const main = imgs.length - 1 - [...imgs].reverse().findIndex(Boolean);   // az új oldal (ha van)
  Object.assign(st, { fit: fits[main], maxW, maxH });
  view.classList.toggle('img-zoomed', Boolean(st.z));
  imgs.forEach((img, i) => {
    if (!img) return;
    const s = st.z ?? fits[i], [cw, ch] = canvases[i].map(v => v * s);
    const pw = Math.floor(Math.min(maxW, cw)), ph = Math.floor(Math.min(maxH, ch));
    const left = cw <= pw ? (pw - cw) / 2 : clamp(pw / 2 - st.cx * cw, pw - cw, 0);
    const top = ch <= ph ? (ph - ch) / 2 : clamp(ph / 2 - st.cy * ch, ph - ch, 0);
    const pane = /** @type {HTMLElement} */ (img.parentElement), w = nat[i][0] * s, h = nat[i][1] * s;
    Object.assign(pane.style, { width: `${pw}px`, height: `${ph}px` });
    Object.assign(pane.dataset, { cw: cw, ch: ch, cl: left, ct: top, s });
    Object.assign(img.style, { width: `${w}px`, height: `${h}px`, maxWidth: 'none',
      transform: `translate(${left + (cw - w) / 2}px, ${top + (ch - h) / 2}px)` });
    img.classList.toggle('img-px', s > 1 && !isSvg(img));
    if (i === main && st.z) {                         // a vágott kivágás vissza az állapotba
      st.cx = cw <= pw ? 0.5 : (pw / 2 - left) / cw;
      st.cy = ch <= ph ? 0.5 : (ph / 2 - top) / ch;
    }
  });
  const pct = view.querySelector('.img-pct');
  if (pct) pct.textContent = `${Math.round((st.z ?? st.fit) * 100)}%`;
  blend(view);
  placeBar(view);
}

/* A Swipe vonala és vágása, az Onion skin áttetszősége (a húzás csak ezt frissíti). */
function blend(view) {
  const st = stateOf(view), mode = view.dataset.mode, [a, b] = halvesOf(view);
  if (!b) return;
  a.style.clipPath = mode === 'swipe' ? `inset(0 ${100 - st.swipe}% 0 0)` : '';
  b.style.clipPath = mode === 'swipe' ? `inset(0 0 0 ${st.swipe}%)` : '';
  a.style.opacity = mode === 'onion' ? String(1 - st.onion / 100) : '';
  b.style.opacity = mode === 'onion' ? String(st.onion / 100) : '';
  const range = /** @type {HTMLInputElement} */ (view.querySelector('.img-opacity'));
  if (range) range.value = String(st.onion);
  const line = /** @type {HTMLElement} */ (view.querySelector('.img-line'));
  if (line && mode === 'swipe') {
    const v = view.getBoundingClientRect(), f = b.firstElementChild.getBoundingClientRect();
    Object.assign(line.style, { left: `${f.left - v.left + f.width * st.swipe / 100}px`, top: `${f.top - v.top}px`,
      height: `${f.height}px` });
  }
}

/* A sáv helye: a kép (a párnál a két kép) alján, középen; a 200 px-nél alacsonyabb képnél
   a kép alatt, ha ott a panel látható részében elfér; a kilógó képnél a látható aljánál. Rögzített (`fixed`): a diff dobozának
   vágása nem érinti, görgetéskor a mutatott nézeté újra igazodik. A teljes lapos nézetben
   a CSS-é. */
function placeBar(view) {
  const bar = /** @type {HTMLElement} */ (view.querySelector(':scope > .img-bar'));
  if (!bar || view.closest('.img-full')) return;
  const figs = halvesOf(view).map(h => h.firstElementChild.getBoundingClientRect());
  const left = Math.min(...figs.map(f => f.left)), right = Math.max(...figs.map(f => f.right));
  const height = Math.max(...figs.map(f => f.height));
  const limit = Math.min(innerHeight, (view.closest('.details') || document.documentElement).getBoundingClientRect().bottom);
  const bottom = Math.min(limit, Math.max(...figs.map(f => f.bottom)));   // a kép látható alja
  const below = height < LOW && bottom + bar.offsetHeight + 6 <= limit;
  bar.classList.toggle('img-bar-below', below);
  Object.assign(bar.style, { left: `${(left + right) / 2}px`,
    top: `${bottom + (below ? 4 : -bar.offsetHeight - BAR_GAP)}px` });
}

/* Nagyítás `z`-re (a természetes mérethez képest; az illesztett alá nem) úgy, hogy a
   mutató alatti képpont (`at`: a pane és benne a pont, alapból a fő pane közepe) a helyén
   maradjon. */
function zoomTo(view, z, at = null) {
  const st = stateOf(view);
  z = Math.min(ZMAX, z);
  if (z <= st.fit + 1e-6) {
    Object.assign(st, { z: null, cx: 0.5, cy: 0.5 });
  } else {
    const pane = at?.pane || [...view.querySelectorAll('.img-pane')].pop();
    const d = pane.dataset, x = at ? at.x : pane.clientWidth / 2, y = at ? at.y : pane.clientHeight / 2;
    const u = (x - +d.cl) / +d.cw, w = (y - +d.ct) / +d.ch, k = z / +d.s;   // a pane saját léptéke
    const r = pane.getBoundingClientRect(), px = r.left + x, py = r.top + y;   // a pont a lapon
    st.cx = (pane.clientWidth / 2 - (x - u * +d.cw * k)) / (+d.cw * k);
    st.cy = (pane.clientHeight / 2 - (y - w * +d.ch * k)) / (+d.ch * k);
    st.z = z;
    layout(view);
    // A pane is nő (legfeljebb a helyéig), és az igazítása szerint el is mozdul: a pont
    // eltérését utólag a kivágásból vesszük le.
    const r2 = pane.getBoundingClientRect(), d2 = pane.dataset;
    st.cx += (r2.left + +d2.cl + u * +d2.cw - px) / +d2.cw;
    st.cy += (r2.top + +d2.ct + w * +d2.ch - py) / +d2.ch;
  }
  layout(view);
  keepInView(view);
}
/* A nagyítás (és a nézetváltás) a képet és vele a diff dobozát megnövelheti: a panel annyit
   görget, hogy a doboz és alatta a következő fájl sora látsszon (a `room` erre szabja a
   képet), de a fájl sora felül ne menjen ki (mint a `revealFile`). */
function keepInView(view) {
  const panel = view.closest('.details'), box = view.closest('.diff');
  if (!panel || !box || view.closest('.img-full')) return;
  const p = panel.getBoundingClientRect(), inTop = p.top + panel.clientTop, inBottom = inTop + panel.clientHeight;
  const bottom = (box.nextElementSibling || box).getBoundingClientRect().bottom;
  const top = box.previousElementSibling.getBoundingClientRect().top;
  if (bottom > inBottom) panel.scrollTop += Math.min(bottom - inBottom, top - inTop);
}
function zoomStep(view, dir) {
  const st = stateOf(view), cur = st.z ?? st.fit;
  const next = dir > 0 ? STEPS.find(s => s > cur * 1.001) ?? ZMAX : [...STEPS].reverse().find(s => s < cur * 0.999) ?? 0;
  zoomTo(view, next);
}

/* A pont a pane-ben (a zoom horgonya). */
const paneAt = (pane, e) => {
  const r = pane.getBoundingClientRect();
  return { pane, x: e.clientX - r.left, y: e.clientY - r.top };
};

const watching = new WeakSet();   // a kép, amelyre már vár egy `load` / `error` figyelő
export function fitImages(root) {
  for (const view of root.querySelectorAll('.img-view')) {
    const pending = [...view.querySelectorAll('img')].filter(img => !img.complete && !watching.has(img));
    for (const img of pending) {
      watching.add(img);
      img.addEventListener('load', () => layout(view), { once: true });
      img.addEventListener('error', () => layout(view), { once: true });
    }
    layout(view);
  }
}

/* A markdown-nézet képei: a `get(ref)` a hivatkozott kép két oldalát adja (`{ old, new }`).
   A csak képből álló bekezdés (`.md-pic`, `data-pic`: a régi és az új hivatkozása, az
   alt szöveg) a páros elrendezésben; a szövegbeli kép (`.md-img[data-img]`, `data-side`:
   melyik oldal) a helyén, a sorban, nézetgombok nélküli sávval. Ami nincs meg, az alt
   szövege marad, `nem található` jelöléssel. A szövegbeli kép betöltése után a `changed`
   fut (a side-by-side sormagasságai).
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
        const view = document.createElement('span');
        view.className = 'img-view img-inline';
        view.innerHTML = `<span class="img-half"><span class="img-fig img-bare"><span class="img-pane"></span></span></span>${barHtml(false, 'span')}`;
        const img = Object.assign(document.createElement('img'), { className: 'md-inl', src: side.uri, alt: span.textContent, draggable: false });
        img.addEventListener('load', () => { layout(view); changed(); }, { once: true });
        view.querySelector('.img-pane').append(img);
        span.replaceWith(view);
      } else {
        span.insertAdjacentHTML('afterend', ` <span class="img-note">${side ? `Túl nagy kép (${fmtBytes(side.size)}).` : 'nem található'}</span>`);
      }
    }, () => {});
  }
}

/* ── Teljes lapos nézet ── a nézet másolata a lapot fedő rétegen, ugyanabban a nézetben,
   illesztve; a sávja mindig látszik. Billentyűk: + − 0 1 2 S O, ← → (Shift: 1%), Esc. */
let full = null;
function openFull(view) {
  closeFull();
  const layer = document.createElement('div');
  layer.className = 'img-full';
  const copy = /** @type {HTMLElement} */ (view.cloneNode(true));
  copy.querySelector(':scope > .img-bar').removeAttribute('style');   // a diffbeli helye nem kell: a CSS-é
  const st = stateOf(view);
  states.set(copy, { ...stateOf(copy), swipe: st.swipe, onion: st.onion });
  layer.append(copy);
  document.body.append(layer);
  full = { layer, view: copy };
  addEventListener('keydown', fullKey, true);
  addEventListener('resize', fullResize);
  fitImages(layer);
}
function closeFull() {
  if (!full) return;
  full.layer.remove();
  full = null;
  removeEventListener('keydown', fullKey, true);
  removeEventListener('resize', fullResize);
}
const fullResize = () => full && layout(full.view);
function fullKey(e) {
  const view = full.view, st = stateOf(view), k = e.key;
  e.stopImmediatePropagation();          // a lap billentyűi (kijelölés, Esc: a commit csukása) állnak
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const modes = view.hasAttribute('data-modes');
  if (k === 'Escape') closeFull();
  else if (k === '+' || k === '=') zoomStep(view, 1);
  else if (k === '-' || k === '−') zoomStep(view, -1);
  else if (k === '0') zoomTo(view, 0);
  else if (k === '1') zoomTo(view, 1);
  else if (modes && /^[2so]$/i.test(k)) setImgMode({ 2: 'sbs', s: 'swipe', o: 'onion' }[k.toLowerCase()]);
  else if ((k === 'ArrowRight' || k === 'ArrowLeft') && modes && imgMode !== 'sbs') {
    const key = imgMode === 'swipe' ? 'swipe' : 'onion';
    st[key] = clamp(st[key] + (k === 'ArrowRight' ? 1 : -1) * (e.shiftKey ? 1 : 10), 0, 100);
    blend(view);
  } else return;
  e.preventDefault();
}

/* ── Egér ── a sáv gombjai, a teljes lapos nézetben a görgő, a húzás: a Swipe vonalán a
   vonal, nagyított képen a kivágás; a kattintás Swipe-ban a vonalat odaugratja. A diffben a
   görgő nem nagyít: a sima a panelé (`stepRows`), a ⌘/Ctrl+görgőt a Claude app elkapja. */
const viewOf = el => /** @type {HTMLElement} */ (el.closest?.('.img-view'));
document.addEventListener('click', e => {
  const t = /** @type {HTMLElement} */ (e.target), view = viewOf(t);
  if (!view) return;
  const btn = /** @type {HTMLElement} */ (t.closest('button'));
  if (!btn) return;
  if (btn.dataset.imgMode) { setImgMode(btn.dataset.imgMode); keepInView(view); }
  else if (btn.dataset.imgZoom) zoomStep(view, +btn.dataset.imgZoom);
  else if ('imgFull' in btn.dataset) openFull(view);
  else if ('imgClose' in btn.dataset) closeFull();
});
document.addEventListener('input', e => {
  const t = /** @type {HTMLInputElement} */ (e.target);
  if (!t.classList?.contains('img-opacity')) return;
  stateOf(viewOf(t)).onion = +t.value;
  blend(viewOf(t));
});
let hovered = null;
document.addEventListener('pointerover', e => {
  const view = viewOf(/** @type {HTMLElement} */ (e.target));
  if (view && view !== hovered) placeBar(view);
  hovered = view;
});
document.addEventListener('scroll', () => { if (hovered) placeBar(hovered); }, true);
document.addEventListener('wheel', e => {
  const t = /** @type {HTMLElement} */ (e.target), pane = /** @type {HTMLElement} */ (t.closest?.('.img-pane'));
  if (!pane || !t.closest('.img-full')) return;
  e.preventDefault();
  const px = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaMode === 2 ? e.deltaY * 400 : e.deltaY;
  const view = viewOf(pane), st = stateOf(view);
  zoomTo(view, (st.z ?? st.fit) * 2 ** (-px / 200), paneAt(pane, e));
}, { passive: false });
document.addEventListener('pointerdown', e => {
  const t = /** @type {HTMLElement} */ (e.target), view = viewOf(t);
  if (!view || e.button !== 0 || t.closest('.img-bar')) return;
  const line = t.closest('.img-line'), pane = /** @type {HTMLElement} */ (t.closest('.img-pane'));
  if (!line && !pane) return;
  e.preventDefault();
  const st = stateOf(view), swipe = view.dataset.mode === 'swipe';
  const fig = () => halvesOf(view)[1].firstElementChild.getBoundingClientRect();
  const setLine = x => { const f = fig(); st.swipe = clamp(Math.round((x - f.left) / f.width * 100), 0, 100); blend(view); };
  const x0 = e.clientX, y0 = e.clientY;
  // húzás közben a kurzor a lap egészén ugyanaz (a vonalról, a képről lecsúszva se ugráljon)
  const cursor = line || (swipe && !st.z) ? 'img-drag-ew' : st.z ? 'img-drag-grab' : '';
  if (cursor) document.documentElement.classList.add(cursor);
  let moved = false, px = x0, py = y0, frame = 0;
  const move = ev => {
    if (!moved && Math.hypot(ev.clientX - x0, ev.clientY - y0) < 3) return;
    moved = true;
    if (line) setLine(ev.clientX);
    else if (st.z) {
      const d = pane.dataset;
      st.cx -= (ev.clientX - px) / +d.cw;
      st.cy -= (ev.clientY - py) / +d.ch;
      if (!frame) frame = requestAnimationFrame(() => { frame = 0; layout(view); });   // képkockánként egyszer
    }
    px = ev.clientX;
    py = ev.clientY;
  };
  const up = ev => {
    removeEventListener('pointermove', move);
    removeEventListener('pointerup', up);
    removeEventListener('pointercancel', up);
    if (cursor) document.documentElement.classList.remove(cursor);
    if (frame) { cancelAnimationFrame(frame); frame = 0; layout(view); }
    if (!moved && swipe && !line && ev.type === 'pointerup') setLine(ev.clientX);
  };
  addEventListener('pointermove', move);
  addEventListener('pointerup', up);
  addEventListener('pointercancel', up);
});
