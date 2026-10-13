
/* Tooltip a `data-tip` elemekre (avatar, diff-címke): egyetlen fix buborék a
   lap fölött, az elem fölé, jobbra zárva; ha fent nincs hely, alá. Késleltetve
   jön, hogy az átsuhanó egérre ne villanjon; görgetésre eltűnik. */
const TIP_DELAY = 350;
const tipEl = document.createElement('div');
tipEl.id = 'tip';
tipEl.setAttribute('role', 'tooltip');
document.body.append(tipEl);
let tipTimer = 0, tipFor = null;
function hideTip() {
  clearTimeout(tipTimer);
  tipFor = null;
  tipEl.classList.remove('on');
}
function showTip(el) {
  tipEl.textContent = el.dataset.tip;
  const r = el.getBoundingClientRect(), t = tipEl.getBoundingClientRect();
  const top = r.top - t.height - 6 >= 0 ? r.top - t.height - 6 : r.bottom + 6;
  tipEl.style.top = `${Math.round(top)}px`;
  tipEl.style.left = `${Math.round(Math.max(4, r.right - t.width))}px`;
  tipEl.classList.add('on');
}
document.addEventListener('mouseover', e => {
  const el = /** @type {HTMLElement} */ (e.target).closest?.('[data-tip]');
  if (el === tipFor) return;
  hideTip();
  if (!el) return;
  tipFor = el;
  tipTimer = setTimeout(() => showTip(el), TIP_DELAY);
});
document.addEventListener('scroll', hideTip, true);
