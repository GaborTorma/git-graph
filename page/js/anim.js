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
const sizing = new WeakMap();   // elem → a futó nyílása / csukódása (a keretéé külön fut)
export function grow(el, change, settle) {
  sizing.get(el)?.cancel();
  const h0 = !change || el.hidden ? 0 : el.offsetHeight;
  change?.();
  const h1 = el.offsetHeight;
  settle?.();
  if (h0 === h1 || reducedMotion()) { drawGraph(); return; }
  const frames = h0 ? [{ height: `${h0}px` }, { height: `${h1}px` }] : [FLAT, fullBox(el)];
  el.style.overflow = 'hidden';
  const anim = el.animate(frames, { duration: ANIM_MS, easing: OPEN_EASE });
  sizing.set(el, anim);
  track(anim)
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
  const anim = el.animate([fullBox(el), FLAT], { duration: ANIM_MS, easing: CLOSE_EASE, fill: 'forwards' });
  sizing.set(el, anim);
  track(anim, follow)
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
/* Egy árnyéklista (a számolt, színnel kezdődő alak) rétegei átszínezve: a belsők (a keret
   vonalai) `line`, a külsők (az árnyék) `drop` színűek. */
const recolor = (shadow, line, drop) => shadow === 'none' ? 'none' : shadow.split(/,(?![^(]*\))/).map(l => {
  const layer = l.trim(), color = layer.match(/^(rgba?\([^)]*\)|#\w+|[a-z]+)/)?.[0] || '';
  return `${layer.includes('inset') ? line : drop}${layer.slice(color.length)}`;
}).join(', ');
/* A keret színe a nyitás felénél a hover színe (ha volt): így nem üt el a halványuló hovertől,
   és a végére éri el a valódi színét. Csukáskor ugyanez visszafelé. */
/** @returns {Keyframe[]} */
function frameKeys(shadow, border, hover) {
  const none = { boxShadow: recolor(shadow, 'transparent', 'transparent'), ...(border && { borderColor: 'transparent' }) };
  const mid = hover && { offset: .5, boxShadow: recolor(shadow, hover, 'transparent'), ...(border && { borderColor: hover }) };
  return [none, ...(mid ? [mid] : []), { boxShadow: shadow, ...(border && { borderColor: border }) }];
}

const fills = new WeakMap();   // fejléc → a nyitásának hover-rétege (csukáskor eltűnik)

/* Nyitás: a lenyíló rész a `grow`-val nő, a fejléc és a lenyíló rész kerete vele együtt jelenik
   meg. Ha a fejléc hover-színű volt (rajta az egér, vagy billentyűvel kijelölt), a teljes,
   növekvő mező is ezt a színt kapja, és a közepéről a széléig halványul — mind ugyanazon a
   görbén, egyszerre ér véget. A hover-réteg a fejléc mögött ül (`.hover-fill`, a szöveg alatt). */
export function openCard(head, el, before, change, settle) {
  for (const a of el.getAnimations()) a.cancel();   // egy félbehagyott csukás (a keretéé is)
  const box = getComputedStyle(el), border = box.borderColor, boxShadow = box.boxShadow, marginTop = box.marginTop;   // a végső keret
  grow(el, change, settle);
  if (reducedMotion()) return;
  // Egy félbehagyott csukás a fejlécen: a végállapotot a saját stílusából kell olvasni, ne az animációéból.
  for (const a of head.getAnimations()) a.cancel();
  const after = cardState(head), opts = { duration: ANIM_MS, easing: OPEN_EASE };
  const hover = clear(before.bg) ? '' : before.bg;
  // Az alsó sarka az első pillanattól egyenes: a keret vonala a lenyíló részébe fut, nem hajlik be.
  const headKeys = frameKeys(after.shadow, '', hover), top = r => r.split(' ')[0];
  headKeys[0].borderRadius = `${top(before.radius)} ${top(before.radius)} 0 0`;
  headKeys[headKeys.length - 1].borderRadius = after.radius;
  head.animate(headKeys, opts);
  el.animate(frameKeys(boxShadow, border, hover), opts);   // a `grow` keretét felülírja
  // A felső margója (a fejléc alá húzva) végig a végleges: törtpixelen a vágott árnyék széle
  // vonalként látszana a fejléc és a lenyíló rész közt.
  el.animate([{ marginTop }, { marginTop }], opts);
  // A tartalma 20 %-ról indul, és az idő felére teljesen látszik (a csukás tükre).
  for (const c of el.children) c.animate([{ opacity: .2 }, { offset: .5, opacity: 1 }, { opacity: 1 }], { duration: ANIM_MS });
  if (!hover) return;
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
  // Induláskor éppen a fejlécet fedi le: a növekvő mező közepe azonnal halványulni kezd.
  const spread = Math.ceil(head.offsetHeight / 2 + SOFT / 2);
  // A felső sarka a fejlécé (a hover 8 px-éből a keret 12 px-ébe), az alsó végig a lenyíló részé:
  // a növekvő mező alja nem lóg ki a kerek sarokból.
  const bottom = box.borderBottomLeftRadius;
  const anim = fill.animate([
    { boxShadow: `inset 0 0 ${SOFT}px ${spread}px ${hover}`, borderRadius: `${top(before.radius)} ${top(before.radius)} ${bottom} ${bottom}` },
    { boxShadow: `inset 0 0 0 0 ${hover}`, borderRadius: `${top(after.radius)} ${top(after.radius)} ${bottom} ${bottom}` }], opts);
  fills.set(head, anim);
  let frame = requestAnimationFrame(function tick() { place(); frame = requestAnimationFrame(tick); });
  const done = () => { cancelAnimationFrame(frame); fill.remove(); };
  anim.finished.then(done, done);
}

/* Csukás: a lenyíló rész a `shrink`-kel csukódik, a fejléc és a lenyíló rész kerete a hover
   színén át tűnik el, a fejléc háttere a mostani állapotába (hoverrel: a hover színébe) vált,
   ugyanazon a görbén. Ha közben az egér lemegy a sorról (vagy visszajön), a háttér onnan, ahol
   tart, az új állapotába megy tovább, és a csukódással együtt ér véget. A fejléc már csukott
   állapotú (`aria-expanded`), a `before` a nyitott állapota. */
export function closeCard(head, el, before, done, follow) {
  const box = getComputedStyle(el), border = box.borderColor, boxShadow = box.boxShadow, marginTop = box.marginTop;
  shrink(el, done, follow);
  if (reducedMotion()) return;
  // Csukás a nyitás közben: a nyitás animációi és a hover-rétege leállnak, a végállapot a fejléc
  // saját stílusa (különben a félúton lévő keret maradna meg a csukás végéig).
  fills.get(head)?.cancel();
  for (const a of head.getAnimations()) a.cancel();
  const after = cardState(head), opts = { duration: ANIM_MS, easing: CLOSE_EASE };
  const hover = clear(after.bg) ? '' : after.bg;
  // A keret árnyéka alul végig levágva (a panelébe fut): inline, nem animálva — a `clip-path`
  // animációja a compositoron indulna, egy képkockával a többi után.
  head.style.clipPath = before.clip;
  const headKeys = frameKeys(before.shadow, '', hover).reverse();
  headKeys[headKeys.length - 1] = { boxShadow: after.shadow };
  const frameAnim = head.animate(headKeys, opts);
  // Az alsó sarka csak a végén kerekedik vissza, amikor a lenyíló rész már (majdnem) csukva van.
  const top = r => r.split(' ')[0];
  head.animate([{ borderRadius: before.radius }, { offset: .85, borderRadius: `${top(after.radius)} ${top(after.radius)} 0 0` },
                { borderRadius: after.radius }], opts);
  const elKeys = frameKeys(boxShadow, border, hover).reverse();
  el.animate(elKeys, { ...opts, fill: 'forwards' });   // a `shrink` keretét felülírja
  el.animate([{ marginTop }, { marginTop }], { ...opts, fill: 'forwards' });   // mint nyitáskor
  // A tartalma az idő 2/3-ától 20 %-ig halványul (a keret külön tűnik el).
  for (const c of el.children) {
    c.animate([{ opacity: 1 }, { offset: 2 / 3, opacity: 1 }, { opacity: .2 }], { duration: ANIM_MS, fill: 'forwards' });
  }
  let bg = head.animate([{ backgroundColor: 'transparent' }, { backgroundColor: after.bg }], opts);
  const end = Number(document.timeline.currentTime) + ANIM_MS;
  const target = /** @type {HTMLElement} */ (head.closest('.row, .file'));
  const retarget = () => {
    if (bg.playState !== 'running') return;
    const now = getComputedStyle(head).backgroundColor;
    bg.cancel();
    bg = head.animate([{ backgroundColor: now }, { backgroundColor: getComputedStyle(head).backgroundColor }],
                      { duration: Math.max(0, end - Number(document.timeline.currentTime)) });
  };
  target?.addEventListener('mouseleave', retarget);
  target?.addEventListener('mouseenter', retarget);
  const finish = () => {
    head.style.clipPath = '';
    target?.removeEventListener('mouseleave', retarget);
    target?.removeEventListener('mouseenter', retarget);
  };
  frameAnim.finished.then(finish, finish);
}
