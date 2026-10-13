/* Közös legördülő menü (ágválasztó, téma, beállítások): nyíl-, Home/End-, Escape- és
   Tab-billentyű, kattintás kívülre csuk. `onPick` a választott opciót kapja. */

export function makeMenu(btn, pop, onPick, onOpen) {
  // A menü a látható részen belül marad (`--room`, a CSS max-height-jában): ami nem fér
  // ki, az görgethető. A lap nem görgethető, a kilógó rész különben elveszne.
  const fit = () => {
    if (pop.hidden) return;
    const r = pop.getBoundingClientRect();
    const room = pop.classList.contains('up') ? r.bottom : innerHeight - r.top;
    pop.style.setProperty('--room', `${Math.max(120, room - 8)}px`);
  };
  addEventListener('resize', fit);
  const toggle = open => {
    pop.hidden = !open;
    btn.setAttribute('aria-expanded', String(open));
    fit();
    if (open && onOpen) onOpen();     // a fókuszt is ő teszi a helyére
    else if (open) (pop.querySelector('[aria-selected="true"]') || pop.querySelector('.option'))?.focus();
  };
  btn.addEventListener('click', () => toggle(pop.hidden));
  btn.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); toggle(true); }
  });
  pop.addEventListener('click', e => {
    const o = e.target.closest('.option');
    if (!o) return;
    if (!('keep' in o.dataset)) {     // a kapcsoló-opció (`data-keep`) nyitva hagyja
      toggle(false);
      btn.focus();
    }
    onPick(o);
  });
  pop.addEventListener('keydown', e => {
    const items = [...pop.querySelectorAll('.option')].filter(o => !o.hidden);
    const i = items.indexOf(document.activeElement);
    if ((e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Home' || e.key === 'End') && !items.length) {
      e.preventDefault();             // szűrés után nincs látható opció
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const n = items.length, down = e.key === 'ArrowDown';
      // A fókusz nincs opción (a szűrőmezőben van): lefelé az első, felfelé az utolsó.
      items[i < 0 ? (down ? 0 : n - 1) : (i + (down ? 1 : n - 1)) % n].focus();
    } else if (e.key === 'Home' || e.key === 'End') {
      e.preventDefault();
      items[e.key === 'Home' ? 0 : items.length - 1].focus();
    } else if (e.key === 'Escape' || e.key === 'Tab') {
      e.stopPropagation();
      toggle(false);
      if (e.key === 'Escape') btn.focus();
    }
  });
  document.addEventListener('pointerdown', e => {
    if (!pop.hidden && !btn.parentElement.contains(e.target)) toggle(false);
  });
}
