/* Nyílás, csukódás és görgetés animálva. */
import { drawGraph } from './graph.js';

/* Rövid, lassuló görgetés `delta` px-lel. Ha közben más görget (kerék,
   billentyű), az övé marad. */
const glides = new WeakMap();
export function glide(el, delta) {
  delta = Math.round(delta);
  if (!delta) return;
  cancelAnimationFrame(glides.get(el));
  const from = el.scrollTop, to = Math.max(0, Math.min(from + delta, el.scrollHeight - el.clientHeight));
  if (reducedMotion()) { el.scrollTop = to; return; }
  const t0 = performance.now();
  let last = from;
  const step = now => {
    if (Math.abs(el.scrollTop - last) > 1) return;
    const k = Math.min(1, (now - t0) / ANIM_MS);
    el.scrollTop = from + (to - from) * (1 - (1 - k) ** 3);
    last = el.scrollTop;
    if (k < 1) glides.set(el, requestAnimationFrame(step));
  };
  glides.set(el, requestAnimationFrame(step));
}

/* Nyílás és csukódás (commit-panel, diff, „több”): magasság-animáció. A gráf a
   sorok mért helyéből rajzol, ezért közben képkockánként újrarajzol (a vonal
   együtt nyúlik); a `follow` is képkockánként fut. A csukódás a nyílás görbéje
   időben visszafelé: a kettő ugyanaz a mozgás, két irányban. */
const ANIM_MS = 200;
const OPEN_EASE = 'cubic-bezier(.2, .7, .3, 1)', CLOSE_EASE = 'cubic-bezier(.7, 0, .8, .3)';
const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
// A keret (a panelé) is 0-ról nő és oda csukódik: a nyílással együtt ér véget.
const FLAT = { height: '0px', marginTop: '0px', marginBottom: '0px', paddingTop: '0px', paddingBottom: '0px',
               borderColor: 'transparent', boxShadow: 'none' };
function fullBox(el) {
  const cs = getComputedStyle(el);
  return { height: `${el.offsetHeight}px`, marginTop: cs.marginTop, marginBottom: cs.marginBottom,
           paddingTop: cs.paddingTop, paddingBottom: cs.paddingBottom, borderColor: cs.borderColor, boxShadow: cs.boxShadow };
}
function track(anim, follow) {
  let frame = requestAnimationFrame(function tick() { follow?.(); drawGraph(); frame = requestAnimationFrame(tick); });
  const stop = () => cancelAnimationFrame(frame);
  anim.finished.then(stop, stop);
  return anim.finished;
}

/* Nyílás: `change` (tartalomcsere, megjelenítés) előtti magasságból az utána
   lévőbe; frissen beszúrt (`change` nélkül) vagy rejtett elem 0-ról, margóval
   együtt. A `settle` a végső méretből számol (nézetbe hozás), és a végén még
   egyszer fut. */
export function grow(el, change, settle) {
  for (const a of el.getAnimations()) a.cancel();
  const h0 = !change || el.hidden ? 0 : el.offsetHeight;
  change?.();
  const h1 = el.offsetHeight;
  settle?.();
  if (h0 === h1 || reducedMotion()) { drawGraph(); return; }
  const frames = h0 ? [{ height: `${h0}px` }, { height: `${h1}px` }] : [FLAT, fullBox(el)];
  el.style.overflow = 'hidden';
  track(el.animate(frames, { duration: ANIM_MS, easing: OPEN_EASE }))
    .then(() => settle?.(), () => {})
    .finally(() => {
      if (!el.getAnimations().length) el.style.overflow = '';   // egy újabb animáció még tart
      drawGraph();
    });
}

/* Csukódás 0-ra, a végén `done` (eltávolít / elrejt) és a `follow`. Ha közben
   újra kinyílik (a `grow` megszakítja), `done` nem fut. */
export function shrink(el, done, follow) {
  for (const a of el.getAnimations()) a.cancel();
  if (el.hidden || reducedMotion()) { done(); follow?.(); return; }
  el.style.overflow = 'hidden';
  track(el.animate([fullBox(el), FLAT], { duration: ANIM_MS, easing: CLOSE_EASE, fill: 'forwards' }), follow)
    .then(() => { done(); follow?.(); }, () => {});
}

/* Lenyitott kártya (a fejléc és a lenyíló része egy keret: commit-sor + panel, fájl + diff).
   A váltás előtt a fejléc állapota (`cardState`) kell: a hover-háttere, a sarka, a kerete. */
export const cardState = head => {
  const cs = getComputedStyle(head);
  return { bg: cs.backgroundColor, radius: cs.borderRadius, shadow: cs.boxShadow, clip: cs.clipPath };
};
const SOFT = 60;   // a halványuló hover széle (px): színátmenet, nem éles vonal
const clear = c => c === 'rgba(0, 0, 0, 0)' || c === 'transparent';

/* Nyitás: a lenyíló rész a `grow`-val nő, a fejléc kerete vele együtt jelenik meg. Ha a
   fejléc hover-színű volt (rajta az egér, vagy billentyűvel kijelölt), a teljes, növekvő
   mező is ezt a színt kapja, és a közepéről a széléig halványul — mind ugyanazon a görbén,
   egyszerre ér véget. A hover-réteg a fejléc mögött ül (`.hover-fill`, a szöveg alatt). */
export function openCard(head, el, before, change, settle) {
  grow(el, change, settle);
  if (reducedMotion()) return;
  const after = cardState(head), opts = { duration: ANIM_MS, easing: OPEN_EASE };
  head.animate([{ boxShadow: 'none', borderRadius: before.radius }, { boxShadow: after.shadow, borderRadius: after.radius }], opts);
  if (clear(before.bg)) return;
  const host = /** @type {HTMLElement} */ (head.offsetParent);
  if (!host) return;
  const fill = document.createElement('div');
  fill.className = 'hover-fill';
  host.append(fill);
  const place = () => {
    const a = head.getBoundingClientRect(), b = el.getBoundingClientRect(), p = host.getBoundingClientRect();
    Object.assign(fill.style, { left: `${a.left - p.left - host.clientLeft + host.scrollLeft}px`,
      top: `${a.top - p.top - host.clientTop + host.scrollTop}px`, width: `${a.width}px`, height: `${b.bottom - a.top}px` });
  };
  place();
  const spread = Math.ceil((head.offsetHeight + el.scrollHeight) / 2 + SOFT / 2);
  const anim = fill.animate([
    { boxShadow: `inset 0 0 ${SOFT}px ${spread}px ${before.bg}`, borderRadius: before.radius },
    { boxShadow: `inset 0 0 0 0 ${before.bg}`, borderRadius: after.radius }], opts);
  let frame = requestAnimationFrame(function tick() { place(); frame = requestAnimationFrame(tick); });
  const done = () => { cancelAnimationFrame(frame); fill.remove(); };
  anim.finished.then(done, done);
}

/* Csukás: a lenyíló rész a `shrink`-kel csukódik (a kerete vele), a fejléc a keretből a
   mostani állapotába (hoverrel: a háttérszínébe) vált át, ugyanazon a görbén. A fejléc már
   csukott állapotú (`aria-expanded`), a `before` a nyitott állapota. */
export function closeCard(head, el, before, done, follow) {
  shrink(el, done, follow);
  if (reducedMotion()) return;
  const after = cardState(head);
  // A keret árnyéka alul végig levágva (a panelébe fut): inline, nem animálva — a `clip-path`
  // animációja a compositoron indulna, egy képkockával a többi után.
  head.style.clipPath = before.clip;
  const anim = head.animate([{ backgroundColor: 'transparent', boxShadow: before.shadow, borderRadius: before.radius },
                             { backgroundColor: after.bg, boxShadow: after.shadow, borderRadius: after.radius }],
                            { duration: ANIM_MS, easing: CLOSE_EASE });
  const unclip = () => { head.style.clipPath = ''; };
  anim.finished.then(unclip, unclip);
}
