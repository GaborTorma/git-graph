/* A lista sorai napokra bontva, és a fix sáv WIP-sorai. */
import { avatarClass } from './avatars.js';
import { dayKey, dayLabel, fmtTime, pinnedTime } from './dates.js';
import { open } from './details.js';
import { OPEN_PANEL, counter, headChip, pendingEl, rowsEl } from './dom.js';
import { drawGraph, setOtherWip } from './graph.js';
import { fitRows } from './layout.js';
import { commitBySha, focusWt, foreign, fresh, headFiltered, laneColor, worktrees } from './model.js';
import { badges, linkify, subjectRefs, wtBadge } from './refs.js';
import { stackDays } from './scroll.js';
import { DATA, expanded, setExpanded, visible } from './state.js';
import { esc, fileCount } from './util.js';

/* A diff-címke száma legfeljebb 3 karakter: 999 fölött kerekített ezres (`1k`). */
const kilo = n => n < 1000 ? String(n) : `${Math.round(n / 1000)}k`;

/* A commit-sor diff-címkéje: fájlszám | zöld | piros, fix széles cellák, a
   pontos számok a tooltipben. A fájlszám 2 karakter: 99 fölött `99⁺`. */
const diffTag = (files, add, del) => `<span class="sum" data-tip="${files} fájl, +${add} −${del} sor"`
  + ` aria-label="${files} fájl, ${add} hozzáadott, ${del} törölt sor">`
  + `<span class="f">${files > 99 ? '99<sup>+</sup>' : files}</span>`
  + `<span class="a">${kilo(add)}</span><span class="d">${kilo(del)}</span></span>`;

/* `Gábor Torma` → `GT`: a név első két szavának kezdőbetűje. */
const initials = name => String(name || '?').trim().split(/\s+/).slice(0, 2)
  .map(w => [...w][0] || '').join('').toUpperCase();
/* A monogram színe: a CDS munkatárs-palettájának egyike (page.css: `--collab-<n>`), a
   szerző nevéből számolva — ugyanaz a szerző mindig ugyanazt kapja. */
const COLLABS = 6;
const collab = name => {
  let h = 0;
  for (const ch of String(name || '')) h = (h * 31 + /** @type {number} */ (ch.codePointAt(0))) >>> 0;
  return `var(--collab-${h % COLLABS})`;
};

function rowHtml(c) {
  const color = fresh.has(c.sha) ? ` style="color:${laneColor(c.lane)}"` : '';
  const st = DATA.stats[c.sha];
  const sum = st ? diffTag(fileCount(st), st.add, st.del) : '';   // üres commitnál is: 0 | 0 | 0
  // A szerző a soron csak arcként: avatar (`hydrateAvatars`), ha nincs, monogram;
  // a név hoverre (`data-tip`).
  const av = avatarClass.get(c.email);
  // idő · avatar · diff; a hash a lenyitott commit fejében (a keresés is megtalálja)
  // Más worktree WIP-je: elöl a worktree jele (`wtBadge`).
  const other = c.uncommitted && c.worktree !== focusWt()?.slug && worktrees().find(w => w.slug === c.worktree);
  // A WIP-badge a ref-badge-ek helyén ül: szűk sorban ugyanúgy a második sorba tördelődik;
  // egysoros elrendezésben a CSS a cím elé teszi (`order`).
  const refs = other ? `<span class="refs wip-lead">${wtBadge(other)}</span>`
    : (() => { const b = badges(c); return b ? `<span class="refs">${b}</span>` : ''; })();
  const subject = c.uncommitted ? c.subject : subjectRefs(c.subject).text;
  // A WIP-soron is: a fájlok utolsó módosítása, a gép git-felhasználója, a diff.
  // A saját WIP a rögzített sávban ül, napfejléc nélkül: nem mai időnél a nap is kell.
  const pinned = c.uncommitted && c.worktree === focusWt()?.slug;
  const meta = `<span class="meta"><span class="time">${pinned ? pinnedTime(c.date) : fmtTime(c.date)}</span>`
    + `<span class="author ${av || 'ini'}"${av ? '' : ` style="--ini:${collab(c.author)}"`} data-tip="${esc(c.author)}" aria-label="${esc(c.author)}">`
    + `${av ? '' : esc(initials(c.author))}</span>${sum}</span>`;
  const cls = ['row', c.uncommitted && 'uncommitted', c.parents.length > 1 && 'merge',
    foreign(c) && 'foreign', c.mirrorOf && 'mirror'].filter(Boolean).join(' ');
  return `<button class="${cls}" type="button" data-sha="${c.sha}" aria-expanded="false">
      <span class="row-in"><span class="desc"><span class="subject"${color}>${linkify(subject)}</span>`
    + `${refs ? '<span class="br"></span>' : ''}${refs}</span>${meta}</span>
    </button>`;
}

/* Napi csoportok (`.day-group`): a ragadós fejléc csak a saját napja alatt
   marad fent, a következő nap fejléce kitolja — nem csúsznak egymásra. */
export function render() {
  // A kijelölés (fókusz) az újrarajzolás után visszaáll: sor vagy fájl.
  const focused = /** @type {HTMLElement} */ (document.activeElement);
  const keepSha = focused?.closest?.('.row')?.dataset.sha;
  const keepPath = /** @type {HTMLElement} */ (focused?.closest?.('.file') || focused?.closest?.('.diff')?.previousElementSibling)
    ?.dataset.path;               // blokkon állva a fájljára áll vissza
  const panelTop = document.querySelector(OPEN_PANEL)?.scrollTop || 0;
  let day = '', html = '';
  const today = dayKey(new Date());
  // A saját worktree WIP-je a fix sávban; a többié a listában, a chipjükkel.
  const ownSlug = focusWt()?.slug;
  renderPending(visible.filter(c => c.uncommitted && c.worktree === ownSlug));
  // A többi worktree WIP-je a commitok közé kerül, a fájlok utolsó módosítása
  // szerint — de sosem a szülője (a stage-elt sor, ill. a HEAD) alá.
  const at = c => {
    const parent = commitBySha(c.parents[0]);
    const floor = !parent ? 0 : parent.uncommitted ? at(parent) : Date.parse(parent.date);
    return Math.max(Date.parse(c.date) || 0, parent ? floor + 1 : 0);
  };
  const others = visible.filter(c => c.uncommitted && c.worktree !== ownSlug).sort((a, b) => at(b) - at(a));
  setOtherWip(others.length > 0);
  const list = [];
  let k = 0;
  for (const c of visible) {
    if (c.uncommitted) continue;
    while (k < others.length && at(others[k]) >= Date.parse(c.date)) list.push(others[k++]);
    list.push(c);
  }
  list.push(...others.slice(k));
  for (const c of list) {
    const key = dayKey(c.date);
    if (key !== day) {
      const lead = !day && key === today ? ' lead' : '';
      html += `${day ? '</section>' : ''}<section class="day-group">`
        + `<div class="day${lead}"><span class="lbl">${dayLabel(key)}<span class="cnt"></span></span></div>`;
      day = key;
    }
    html += rowHtml(c);
  }
  if (day) html += '</section>';
  rowsEl.innerHTML = html || '<p class="empty">Nincs a szűrésnek megfelelő commit.</p>';
  // A saját HEAD-et az ágválasztó elrejti: a fejléc chipje halványabb (kattintásra minden ág).
  headChip.classList.toggle('head-off', headFiltered());
  fitRows();
  drawGraph();
  const shown = visible.filter(c => !c.uncommitted).length;   // az ál-sor nem commit
  counter.innerHTML = DATA.meta.totalCommits ? `<b>${shown}</b> / ${DATA.meta.totalCommits}` : '';
  counter.dataset.tip = `${shown} commit látszik, összesen ${DATA.meta.totalCommits}`;
  if (expanded && visible.some(c => c.sha === expanded)) {
    open(expanded);
    const panel = document.querySelector(OPEN_PANEL);   // a panel saját görgetése megmarad
    if (panel) panel.scrollTop = panelTop;
  } else setExpanded(null);
  stackDays();
  const back = keepPath && expanded
    ? [...document.querySelectorAll(`${OPEN_PANEL} .file`)].find(f => f.dataset.path === keepPath)
    : keepSha && document.querySelector(`.row[data-sha="${CSS.escape(keepSha)}"]`);
  back?.focus({ preventScroll: true });
}

/* Az Uncommitted ál-sorok (worktree-nként a nem stage-elt, alatta a stage-elt) mindig látszanak: a lista
   fölötti fix sávban, saját üres karikával és a lista felé futó szaggatott
   csonkkal; görgetve a többi worktree-é folytatódik a HEAD-ig. A karikák a sorok mért közepére kerülnek
   (`drawPending`, a `drawGraph` hívja): a sor kétsoros is lehet. */

function renderPending(list) {
  pendingEl.hidden = !list.length;
  pendingEl.innerHTML = list.length
    ? '<svg class="pend-lane" aria-hidden="true"></svg>' + list.map(rowHtml).join('') : '';
}
