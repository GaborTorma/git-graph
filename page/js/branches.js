/* Ágválasztó: a menü tartalma és szűrője. */
import { icon, tinted } from './icons.js';
import { fitChrome } from './layout.js';
import { branchColor, focusWt, hiddenRemotes, lcStyle, linkedWts, refColor, remoteRefs, remoteShown, remotesOn, worktrees, wtColor } from './model.js';
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
const branchLabel = document.getElementById('branchLabel');
const branchIc = document.getElementById('branchIc');
export let branchSel = new Set();
export const setBranchSel = refs => { branchSel = new Set(refs); };

/* Az ágválasztó színes ikonjai. Egy ág színe: ha egy worktree-ben ki van véve
   (vagy leválasztott HEAD-del az app szerint az övé), a worktree színe, mint a
   chipjén; különben a csúcsa sávjáé. Az upstream felhője a helyi ágáé; teli csak
   az alapágé (default ág csak remote-on van). */

const cloudIc = (ref, color, size = undefined) => tinted(ref === DATA.meta.base ? 'cloudFill' : 'cloud', color, size);
/* Ág és upstream együtt (egy helyen állnak, vagy mindkettő kijelölve): egy ikon. */
const branchCloudIc = (ref, color, size = undefined) => tinted(ref === DATA.meta.base ? 'branchCloudFill' : 'branchCloud', color, size);
/* Egy helyi ág refjei a menüben: maga, és — remote ágakkal — az élő upstreamje, ha a
   remote-ja nincs elrejtve. */
const blockRefs = (b, remote) => (remote && b.upstream && b.track !== 'gone' && remoteShown(b.upstream)
  ? [b.name, b.upstream] : [b.name]);
/* Egy worktree-hez tartozó ágak (`owner`). */
const ownedBy = w => DATA.branches.filter(b => !b.remote && b.owner === w.slug);
/* A gomb ikonja és felirata a kijelölés szerint: minden ág; egy worktree összes ága
   (ha több van) a worktree-vel; egy blokk (ág és/vagy upstream) a kijelölt sorai
   ikonjával és az ág nevével; több ref: az első + a többi száma. */
function selView() {
  if (!branchSel.size) return [icon('allBranches'), 'Minden ág'];
  const remote = remotesOn();
  const names = [...branchSel];
  const same = refs => refs.length === names.length && refs.every(r => branchSel.has(r));
  for (const w of worktrees()) {
    const own = ownedBy(w);
    if (linkedWts().length && own.length > 1 && same(own.flatMap(b => blockRefs(b, remote)))) {
      return [tinted(w.main ? 'mainWorktree' : 'worktree', wtColor(w) || 'var(--fg-2)'), w.main ? 'main' : w.name];
    }
  }
  const b = DATA.branches.find(x => !x.remote && (x.name === names[0] || x.upstream === names[0]));
  if (b && names.every(n => n === b.name || n === b.upstream)) {
    const c = branchColor(b);
    const both = branchSel.has(b.name) && branchSel.has(b.upstream);
    return [both ? branchCloudIc(b.upstream, c) : branchSel.has(b.name) ? tinted('branch', c) : cloudIc(b.upstream, c),
      branchSel.has(b.name) ? b.name : b.upstream];
  }
  const lb = DATA.branches.find(x => !x.remote && x.name === names[0]);
  const first = lb ? tinted('branch', branchColor(lb)) : cloudIc(names[0], refColor(names[0]));
  return [first, names.length === 1 ? names[0] : `${names[0]} +${names.length - 1}`];
}

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
  const group = (name, inner, sep) => `<div class="menu-grp${sep ? ' sep' : ''}" data-name="${esc(name)}">${inner}</div>`;
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
  // Csak remote ágak, remote-onként egy fejléc.
  const byRemote = new Map();
  for (const b of DATA.branches.filter(x => x.remote && remoteShown(x.name))) {
    const r = b.name.slice(0, b.name.indexOf('/'));
    byRemote.set(r, [...(byRemote.get(r) || []), b]);
  }
  for (const [r, list] of byRemote) {
    html += group(r, `<div class="menu-wt">${icon('cloud', 'ic', 'md')}<span>${esc(r)}</span><span class="note">· csak remote</span></div>`
      + list.map(b => {
        const [ca, cd] = cell(b.name);
        return blockBtn([b.name], line([b.name], cloudIc(b.name, refColor(b.name), 'md'), esc(b.name.slice(r.length + 1)), ca, '', cd));
      }).join(''), true);
  }
  branchList.innerHTML = html;
  filterBranches();
  fillRemotes();
  // A három távolság-oszlop szélessége külön-külön a saját leghosszabb számához igazodik
  // (1–4 jegy, üres oszlopnál 0); a ↕ jel a szélső oszlophoz tartozik.
  const longest = sel => Math.max(0, ...[...branchPop.querySelectorAll(sel)].map(e => e.textContent.length));
  branchPop.style.setProperty('--c1-digits', String(longest('.c1 .dc > :last-child, .gap > :last-child')));
  branchPop.style.setProperty('--c2-digits', String(longest('.c2 .dc > :last-child')));
  branchPop.style.setProperty('--c3-digits', String(longest('.c3 .dc > :last-child')));
  const [ics, label] = selView();
  if (branchIc.innerHTML !== ics) branchIc.innerHTML = ics;
  if (branchLabel.textContent !== label) {
    branchLabel.textContent = label;
    fitChrome();                // a hosszabb ágnév más sorbontást hozhat
  }
}

/* Remote-szűrő (a „Remote ágak” kapcsoló mellett, csak több remote-nál): remote-onként
   egy opció, pipával; a kapcsoló kikapcsolva a gomb is tiltott. A gomb felirata a
   látható remote-ok neve, vagy „Minden remote”. */
export const remotesBtn = /** @type {HTMLButtonElement} */ (document.getElementById('remotesBtn'));
export const remotesPop = document.getElementById('remotesPop');
const remotesLabel = document.getElementById('remotesLabel');
function fillRemotes() {
  const names = DATA.meta.remotes || [];
  const focused = remotesPop.contains(document.activeElement) && /** @type {HTMLElement} */ (document.activeElement).dataset.key;
  remotesPop.innerHTML = names.map(n => `<button type="button" class="option with-icon" role="option" data-keep`
    + ` data-key="${esc(n)}" aria-selected="${!hiddenRemotes.has(n)}">${icon('cloud', 'ic', 'md')}`
    + `<span class="name">${esc(n)}</span>${icon('check', 'ic ck', 'md')}</button>`).join('');
  if (focused) remotesPop.querySelector(`.option[data-key="${CSS.escape(focused)}"]`)?.focus();
  remotesBtn.disabled = !remotesOn();
  const shown = names.filter(n => !hiddenRemotes.has(n));
  const label = shown.length === names.length ? 'Minden remote' : shown.join(', ') || 'Nincs remote';
  const wrap = remotesBtn.parentElement, hide = names.length < 2;
  if (wrap.hidden !== hide || remotesLabel.textContent !== label) {
    wrap.hidden = hide;
    remotesLabel.textContent = label;
    remotesBtn.dataset.tip = `Látható remote-ok: ${label.toLowerCase() === 'minden remote' ? 'mind' : label}`;
    fitChrome();
  }
}

/* Az ágválasztó szűrője: minden szó (kis-nagybetű és ékezet nélkül) szerepeljen a
   blokk refjeiben vagy a csoportja nevében (worktree, remote) — a worktree nevére
   szűrve az összes ága látszik. A csoport (a fejlécével) csak akkor marad, ha legalább
   egy ága látszik; a „Minden ág” szűrés közben rejtve. */
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
    grp.hidden = !shown;
    any ||= shown;
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
