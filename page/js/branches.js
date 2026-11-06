/* Ágválasztó: a menü tartalma és szűrője. */
import { icon, tinted } from './icons.js';
import { fitChrome } from './layout.js';
import { anyRemoteHidden, branchColor, focusWt, lcStyle, linkedWts, refColor, remoteOf, remoteOff, remoteRefs, remoteShown, remotesOn, worktrees, wtColor } from './model.js';
import { distText } from './refs.js';
import { DATA } from './state.js';
import { esc, fold, queryWords } from './util.js';

/* Ágválasztó: saját listbox-menü. A kijelölés ref-nevek halmaza (helyi ág,
   upstream, csak remote ág); üres = minden ág. */
export const branchBtn = document.getElementById('branchBtn');
export const branchPop = document.getElementById('branchPop');
const branchAll = document.getElementById('branchAll');
const branchList = document.getElementById('branchList');
export const branchQuery = /** @type {HTMLInputElement} */ (document.getElementById('branchQuery'));
const branchView = document.getElementById('branchView');
export let branchSel = new Set();
export const setBranchSel = refs => { branchSel = new Set(refs); };

/* Az ágválasztó színes ikonjai. Egy ág színe: ha egy worktree-ben ki van véve
   (vagy leválasztott HEAD-del az app szerint az övé), a worktree színe, mint a
   chipjén; különben a csúcsa sávjáé. Az upstream felhője a helyi ágáé; teli csak
   az alapágé (default ág csak remote-on van). */

const cloudIc = (ref, color, size = undefined) => tinted(ref === DATA.meta.base ? 'cloudFill' : 'cloud', color, size);
/* Ág és upstream együtt (egy helyen állnak, vagy mindkettő kijelölve): egy ikon. */
const branchCloudIc = (ref, color, size = undefined) => tinted(ref === DATA.meta.base ? 'branchCloudFill' : 'branchCloud', color, size);
/* Egy helyi ág refjei a menüben: maga, és — remote ágakkal — az élő upstreamje (a szerver csak
   az azonos nevűt adja: `own_upstream`), ha a remote-ja nincs elrejtve. */
const blockRefs = (b, remote) => (remote && b.upstream && b.track !== 'gone' && remoteShown(b.upstream)
  ? [b.name, b.upstream] : [b.name]);
/* Egy worktree-hez tartozó ágak (`owner`). */
const ownedBy = w => DATA.branches.filter(b => !b.remote && b.owner === w.slug);
/* A gomb elemei a kijelölés sorrendjében: egy worktree összes ága (ha több van) egy elem a
   worktree-vel; egy blokk (ág és/vagy upstream) a kijelölt sorai ikonjával és az ág nevével;
   a csak remote ág a felhőjével. `at`: az elem első refjének helye a kijelölésben. */
function selItems() {
  const remote = remotesOn();
  const order = [...branchSel], left = new Set(branchSel), items = [];
  const at = refs => Math.min(...refs.map(r => order.indexOf(r)));
  if (linkedWts().length) {
    for (const w of worktrees()) {
      const own = ownedBy(w), refs = own.flatMap(b => blockRefs(b, remote));
      if (own.length < 2 || !refs.every(r => left.has(r))) continue;
      for (const r of refs) left.delete(r);
      items.push({ at: at(refs), kind: 'worktree', name: w.main ? 'main' : w.name,
        ic: tinted(w.main ? 'mainWorktree' : 'worktree', wtColor(w) || 'var(--fg-2)') });
    }
  }
  for (const b of DATA.branches.filter(x => !x.remote)) {
    const own = left.has(b.name), up = b.upstream && left.has(b.upstream) ? b.upstream : '';
    if (!own && !up) continue;
    const refs = own ? (up ? [b.name, up] : [b.name]) : [up];
    for (const r of refs) left.delete(r);
    const c = branchColor(b);
    items.push(own && up ? { at: at(refs), kind: 'branchCloud', name: b.name, ic: branchCloudIc(up, c) }
      : own ? { at: at(refs), kind: 'branch', name: b.name, ic: tinted('branch', c) }
      : { at: at(refs), kind: 'cloud', name: up, ic: cloudIc(up, c) });
  }
  for (const r of left) items.push({ at: order.indexOf(r), kind: 'cloud', name: r, ic: cloudIc(r, refColor(r)) });
  return items.sort((x, y) => x.at - y.at);
}
/* A gomb: kijelölés nélkül „Minden ág”; különben legfeljebb 6 elem, az első legfeljebb 3
   ikonnal és névvel — amennyi elfér: a gomb legfeljebb `BTN_MAX` széles, és a fejléc sorában a
   repó és az eszközök mellett marad (több elemnél egy név legfeljebb 160 px) —, a többi csak
   színes ikonnal (a neve a súgóban), utána `+N` (a kimaradtak neve soronként a súgóban). Ha egy
   remote rejtve van, a végén halvány áthúzott felhő. */
const MAX_ITEMS = 6, MAX_NAMED = 3, BTN_MAX = 500;
const chromeEl = /** @type {HTMLElement} */ (document.querySelector('.chrome'));
/* A gomb elemeinek helye: `BTN_MAX`-ig, amennyi a repó és az eszközök mellett szabad; ha ott
   alig van hely (a fejléc úgyis több sorba tör), a fejléc teljes szélessége. */
function selRoom() {
  const cs = getComputedStyle(chromeEl), gap = parseFloat(cs.columnGap) || 0;
  const inner = chromeEl.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  const extra = branchBtn.offsetWidth - branchView.offsetWidth;   // padding, nyíl
  const repo = /** @type {HTMLElement} */ (chromeEl.querySelector('.repo')).offsetWidth;
  const tools = /** @type {HTMLElement} */ (chromeEl.querySelector('.tools')).offsetWidth;
  const free = inner - repo - tools - 2 * gap;
  return Math.min(BTN_MAX, free >= 200 ? free : inner) - extra;
}
/* A legutóbbi elemek kulcsa (a hellyel) és a nevükkel álló elemek száma: változatlan kijelölésnél
   és szélességnél nincs újramérés (a gomb DOM-ja sem cserélődik); a betű betöltése után újra mér. */
let selKey = '', selNamed = 0;
function renderSel() {
  const before = branchView.innerHTML, items = selItems();
  const hidden = (DATA.meta.remotes || []).filter(remoteOff);
  const off = anyRemoteHidden()
    ? `<span class="cloud-off" data-tip="${esc(`Rejtett remote: ${hidden.join(', ')}`)}">${icon('cloudSlash')}</span>` : '';
  const shown = items.slice(0, MAX_ITEMS), rest = items.slice(MAX_ITEMS);
  const html = named => (!items.length ? `${icon('allBranches')}<span class="select-label">Minden ág</span>`
    : shown.map((it, i) => (i < named
      ? `<span class="sel-item" data-kind="${it.kind}">${it.ic}<span class="sel-name">${esc(it.name)}</span></span>`
      : `<span class="sel-item ic-only" data-kind="${it.kind}" data-tip="${esc(it.name)}">${it.ic}</span>`)).join('')
      + (rest.length ? `<span class="sel-more" data-tip="${esc(rest.map(it => it.name).join('\n'))}">+${rest.length}</span>` : ''))
    + off;
  const set = h => { if (branchView.innerHTML !== h) branchView.innerHTML = h; };
  branchView.classList.toggle('many', items.length > 1);
  branchBtn.classList.toggle('filtered', items.length > 0);   // kijelölt ág: lenyomott háttér (a rejtett remote nem)
  const room = selRoom();
  const key = `${Math.round(room)}|${html(MAX_NAMED)}`;
  if (key === selKey) {
    set(html(selNamed));
    return branchView.innerHTML !== before;
  }
  let named = Math.min(MAX_NAMED, shown.length);
  set(html(named));
  while (named > 1 && branchView.offsetWidth > room) set(html(--named));
  // Rejtett keretben (nulla szélesség) nem mért: legközelebb újra.
  [selKey, selNamed] = branchView.offsetWidth ? [key, named] : ['', 0];
  return branchView.innerHTML !== before;
}
const refit = () => { if (renderSel()) fitChrome(); };
document.fonts?.addEventListener('loadingdone', () => { selKey = ''; refit(); });
let chromeW = 0;
new ResizeObserver(() => { if (chromeEl.clientWidth !== chromeW) { chromeW = chromeEl.clientWidth; refit(); } }).observe(chromeEl);

/* Worktree-k esetén worktree-nként egy fejléc (a saját a fejléc chipjének
   színével), alatta az ágai: amelyikben utoljára ki volt véve (`owner`, a
   worktree-k HEAD-reflogjából); a gazdátlanok utánuk, fejléc nélkül, a csak
   remote ágak a végén. A helyi ág és az upstreamje egy blokk, egy opció: a sorra
   kattintva mindkettő kijelölődik; egy kipipált sor pipájára kattintva csak az a
   ref kerül ki (a ki nem pipáltéra kattintva bekerül). Ha egy helyen állnak, egy
   sor a közös ikonnal (`branchCloud`); különben egymás alatt az ág és a felhő. A worktree fejlécére
   kattintva az összes ága kijelölődik. HEAD worktree-nként. Worktree nélkül csak
   az ágak. */
export function fillBranches() {
  const remote = remotesOn();
  const valid = new Set([...DATA.branches.map(b => b.name), ...[...remoteRefs()].filter(remoteShown)]);
  for (const n of branchSel) if (!valid.has(n)) branchSel.delete(n);
  const wts = worktrees(), multi = linkedWts().length > 0, own = focusWt();
  const base = DATA.meta.base || '', baseLocal = base.slice(base.indexOf('/') + 1);
  const local = DATA.branches.filter(b => !b.remote);
  const detachedOf = name => wts.find(w => !w.branch && w.appBranch === name);
  const isHead = b => Boolean(b.worktree) || Boolean(detachedOf(b.name))
    || (b.worktree === undefined && b.current);
  // HEAD elöl, aztán az alapág, a többi a git sorrendjében (név szerint).
  const rank = b => (isHead(b) ? 0 : b.name === baseLocal ? 1 : 2);
  const sorted = list => [...list].sort((x, y) => rank(x) - rank(y));
  const synced = b => { const up = DATA.meta.tracks?.[b.name]?.up; return up && !up[0] && !up[1]; };
  /* Egy sor: pipa (külön kattintható), egy ikon (ág, felhő, vagy a kettő együtt), név, és jobbra három
     távolság-oszlop. A szélső (`c1`): az egysoros blokk ↓-je, a két soros blokkban
     a ↕ jel helye; előtte (`c2`) a két soros blokk soronkénti ↓-je; legbelül (`c3`) minden
     sor ↑-ja. Egy cella: a nyíl elöl, a szám a cella végén — így a nyilak és a
     számvégek egy vonalban. */
  const line = (refs, ic, name, c3, c2, c1) => {
    const on = refs.every(r => branchSel.has(r));
    return `<span class="ln${on ? ' on' : ''}"><span class="ckc" data-refs="${esc(refs.join(' '))}"`
      + ` data-tip="${on ? 'kivesz' : 'hozzáad'}">${icon('check', 'ic ck', 'md')}</span>`
      + `<span class="col">${ic}</span>`
      + `<span class="name">${name}</span><span class="c3">${c3}</span><span class="c2">${c2}</span><span class="c1">${c1}</span></span>`;
  };
  // Az alapághoz mért távolság irányonként egy cellában (a távolság-szöveg a
  // tooltipben): `[↑, ↓]`.
  const cell = name => {
    const [a, d] = DATA.meta.tracks?.[name]?.base || [0, 0];
    const tip = esc(distText(name).trim());
    const one = (arrow, n) => `<span class="dc" data-tip="${tip}"><span>${arrow}</span><span>${n}</span></span>`;
    return [a ? one('↑', a) : '', d ? one('↓', d) : ''];
  };
  // A helyi ág és az upstreamje közti távolság (`↕`): a két sor közé, jobbra. Az
  // alapág helyi párjának előnye anomália (piros), mint a chipeken.
  const pairGap = b => {
    const [a, d] = DATA.meta.tracks?.[b.name]?.up || [0, 0];
    const odd = b.name === baseLocal && a > 0;
    const tip = [a && `↑${a}: a helyi ${b.name} ennyivel jár előrébb`, d && `↓${d}: a ${b.upstream} ennyivel jár előrébb`]
      .filter(Boolean).join('\n');
    // A jel a többi távolság ↑ és ↓ karaktere egymás fölött: a nyílhegyük ugyanaz.
    return `<span class="dc gap${odd ? ' warn' : ''}" data-tip="${esc(tip)}"><span class="ud" aria-hidden="true">`
      + `<span>↑</span><span>↓</span></span><span>${a && d ? `${a}/${d}` : a || d}</span></span>`;
  };
  const block = b => {
    const det = detachedOf(b.name);
    const name = (det ? `<i>${esc(b.name)}</i>` : esc(b.name))
      + (isHead(b) ? `<span class="cur" style="${lcStyle(branchColor(b))}">HEAD</span>` : '');
    const refs = blockRefs(b, remote), up = refs[1];
    const pair = up && !synced(b);
    // A leválasztott HEAD jele a szélen, a worktree-fejléc WIP-karikájának oszlopában.
    const detIc = det && `<span class="det" data-tip="leválasztott HEAD — az ágát a Claude app jegyzi">${icon('detached', 'ic', 'xs')}</span>`;
    const [ca, cd] = cell(b.name);
    const c = branchColor(b);
    // Két sornál a soronkénti távolság a belső oszlopban, a szélen a kettejük közti ↕.
    const lines = !pair
      ? line(refs, up ? branchCloudIc(up, c, 'md') : tinted('branch', c, 'md'), name, detIc ? '' : ca, '', detIc || cd)
      : line([b.name], tinted('branch', c, 'md'), name, detIc ? '' : ca, detIc || cd, '')
        + line([up], cloudIc(up, c, 'md'), esc(up), ...cell(up), '') + pairGap(b);
    return blockBtn(refs, lines);
  };
  const blockBtn = (refs, lines) => `<button type="button" class="option blk" role="option" data-refs="${esc(refs.join(' '))}"`
    + ` data-key="${esc(refs[0])}" aria-selected="${refs.every(r => branchSel.has(r))}">${lines}</button>`;
  const header = w => {
    const lc = wtColor(w) || 'var(--accent)';
    const ic = tinted(w.main ? 'mainWorktree' : 'worktree', lc, 'md');   // a worktree színe, mint a chipjén
    const name = esc(w.main ? 'main' : w.name);
    const wip = w.dirty ? `<span class="wip" style="color:${lc}" data-tip="nem commitolt változás"></span>` : '';
    const cur = w.slug === own?.slug;
    const body = `${ic}<span class="name${cur ? ' menu-wt-cur" data-tip="itt dolgozik az előtérben lévő session' : ''}">${name}</span>${wip}`;
    const refs = ownedBy(w).flatMap(b => blockRefs(b, remote));
    return refs.length
      ? `<button type="button" class="option menu-wt" role="option" data-refs="${esc(refs.join(' '))}" data-key="wt:${esc(w.slug)}"`
        + ` aria-selected="${refs.every(r => branchSel.has(r))}" data-tip="a worktree összes ága">${body}</button>`
      : `<div class="menu-wt">${body}</div>`;
  };
  /* Egy csoport: fejléc (worktree, remote; a szűrő a nevét is nézi) és az ágai. A `sep`
     csoport fölött vonal, ha előtte látszik egy csoport (CSS). */
  const group = (name, inner, sep, cls = '') => `<div class="menu-grp${sep ? ' sep' : ''}${cls ? ` ${cls}` : ''}" data-name="${esc(name)}">${inner}</div>`;
  branchAll.innerHTML = `<button type="button" class="option blk" role="option" data-refs="" data-key="" aria-selected="${!branchSel.size}">`
    + `<span class="ln${branchSel.size ? '' : ' on'}"><span class="ckc">${icon('check', 'ic ck', 'md')}</span>`
    + `<span class="col">${icon('allBranches', 'ic', 'md')}</span><span class="name">Minden ág</span></span></button>`;
  let html = '';
  if (multi) {
    const slugs = new Set(wts.map(w => w.slug));
    html += wts.map(w => group(w.main ? 'main' : w.name,
      header(w) + sorted(local.filter(b => b.owner === w.slug)).map(block).join(''))).join('');
    const orphans = local.filter(b => !slugs.has(b.owner));
    if (orphans.length) html += group('', sorted(orphans).map(block).join(''), true);
  } else if (local.length) {
    html += group('', sorted(local).map(block).join(''));
  }
  // Remote-onként egy fejléc (glóbusz, név, kapcsoló) — akkor is, ha nincs csak remote ága —,
  // alatta a csak remote ágai; kikapcsolva halvány, ágak nélkül. Csak a kapcsoló kattintható.
  for (const r of DATA.meta.remotes || []) {
    const on = !remoteOff(r);
    const list = on ? DATA.branches.filter(b => b.remote && remoteOf(b.name) === r) : [];
    html += group(r, `<div class="menu-wt menu-remote${on ? '' : ' off'}" data-remote="${esc(r)}">${icon('globe', 'ic', 'md')}`
      + `<span class="name">${esc(r)}</span><button type="button" class="option rsw" role="switch" data-keep`
      + ` data-remote="${esc(r)}" aria-checked="${on}" aria-label="${esc(r)} ágai"><span class="track"></span></button></div>`
      + list.map(b => {
        const [ca, cd] = cell(b.name);
        return blockBtn([b.name], line([b.name], cloudIc(b.name, refColor(b.name), 'md'), esc(b.name.slice(r.length + 1)), ca, '', cd));
      }).join(''), true, 'remote');
  }
  branchList.innerHTML = html;
  filterBranches();
  // A három távolság-oszlop szélessége külön-külön a saját leghosszabb számához igazodik
  // (1–4 jegy, üres oszlopnál 0); a ↕ jel a szélső oszlophoz tartozik.
  const longest = sel => Math.max(0, ...[...branchPop.querySelectorAll(sel)].map(e => e.textContent.length));
  branchPop.style.setProperty('--c1-digits', String(longest('.c1 .dc > :last-child, .gap > :last-child')));
  branchPop.style.setProperty('--c2-digits', String(longest('.c2 .dc > :last-child')));
  branchPop.style.setProperty('--c3-digits', String(longest('.c3 .dc > :last-child')));
  if (renderSel()) fitChrome();   // a hosszabb ágnév más sorbontást hozhat
}

/* Az ágválasztó szűrője: minden szó (kis-nagybetű és ékezet nélkül) szerepeljen a
   blokk refjeiben vagy a csoportja nevében (worktree, remote) — a worktree nevére
   szűrve az összes ága látszik. A csoport (a fejlécével) csak akkor marad, ha legalább
   egy ága látszik; a remote fejléce akkor is, ha a neve illik (üres szűrővel mindig: a
   kapcsolója ágak nélkül is kell). A „Minden ág” szűrés közben rejtve. */
export function filterBranches() {
  const words = queryWords(branchQuery.value);
  branchAll.hidden = words.length > 0;
  let any = false;
  for (const grp of /** @type {HTMLCollectionOf<HTMLElement>} */ (branchList.children)) {
    let shown = false;
    for (const el of grp.querySelectorAll('.blk')) {
      const text = fold(`${grp.dataset.name} ${el.dataset.refs}`);
      el.hidden = !words.every(w => text.includes(w));
      shown ||= !el.hidden;
    }
    grp.hidden = !shown && !(grp.classList.contains('remote') && words.every(w => fold(grp.dataset.name).includes(w)));
    any ||= !grp.hidden;
  }
  branchList.classList.toggle('empty', !any && words.length > 0);
}
branchQuery.addEventListener('input', filterBranches);
/* A mező billentyűi (a makeMenu kezelője előtt): Enter az első látható ágat
   választja, Escape előbb a szűrőt üríti; Home/End a kurzort mozgatja. A nyilak, a
   Tab és az üres mezőben az Escape a menüé. */
branchQuery.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    e.preventDefault();
    branchList.querySelector('.blk:not([hidden])')?.click();
  } else if (e.key === 'Escape' && branchQuery.value) {
    e.stopPropagation();
    branchQuery.value = '';
    filterBranches();
  } else if (e.key === 'Home' || e.key === 'End') e.stopPropagation();
});
