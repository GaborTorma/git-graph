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
   együtt nyúlik); a `follow` is képkockánként fut. */
const ANIM_MS = 180;
const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
const FLAT = { height: '0px', marginTop: '0px', marginBottom: '0px', paddingTop: '0px', paddingBottom: '0px', opacity: 0 };
function fullBox(el) {
  const cs = getComputedStyle(el);
  return { height: `${el.offsetHeight}px`, marginTop: cs.marginTop, marginBottom: cs.marginBottom,
           paddingTop: cs.paddingTop, paddingBottom: cs.paddingBottom, opacity: 1 };
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
  track(el.animate(frames, { duration: ANIM_MS, easing: 'cubic-bezier(.2, .7, .3, 1)' }))
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
  track(el.animate([fullBox(el), FLAT], { duration: ANIM_MS, easing: 'cubic-bezier(.4, 0, .6, 1)', fill: 'forwards' }), follow)
    .then(() => { done(); follow?.(); }, () => {});
}
