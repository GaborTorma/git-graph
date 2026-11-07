/* Merge-ek összecsukása: amit egy merge a 2. (vagy további) szülőjén át hozott be (`git log M^1..M`,
   a merge-ek „birtoka”), az a merge alá rejtve. A ref-es commitok (ág, remote, tag, HEAD, stash,
   WIP, worktree HEAD-je, gyerek nélküli commit) maguk látszanak, az alattuk lévő beolvasztott lánc
   nem: azt szaggatott él köti át. Az alapállapot a repó beállítása (`meta.collapseMerges`, a
   `settings` tool írja); merge-enként a gráfoszlop felülírja — csak a lap memóriájában, az
   újratöltésig, a kapcsoló váltása törli. */
import { commitBySha } from './model.js';
import { DATA } from './state.js';

/** @type {Map<string, boolean>} merge sha → kibontva (a kézi felülírás) */
const overrides = new Map();
let version = 0;                       // a felülírások változása (a `layout` gyorstárához)
export const collapseOn = () => DATA.meta.collapseMerges !== false;
export const isOpen = sha => overrides.get(sha) ?? !collapseOn();
export const setOpen = (sha, open) => { overrides.set(sha, open); version++; };
export const clearOverrides = () => { overrides.clear(); version++; };
export const isMerge = c => c.parents.length > 1;

/* A mindig látható commitok: ami ref-es, WIP, stash, worktree HEAD-je, vagy aminek nincs gyereke. */
function roots() {
  const child = new Set(DATA.commits.flatMap(c => c.parents));
  const heads = new Set((DATA.meta.worktrees || []).map(w => w.head));
  return new Set(DATA.commits.filter(c => c.refs.length || c.uncommitted || c.stash || heads.has(c.sha) || !child.has(c.sha))
    .map(c => c.sha));
}

/* Az első szülők láncai szakaszokra bontva: minden commit egy szakaszé (`seg`), azon belül
   lefelé nő a mélysége (`depth`); a szakasz alja után a lánc a `join` szakaszában folytatódik. */
function segments() {
  const seg = new Map(), depth = new Map(), join = [];
  for (const c of DATA.commits) {
    if (seg.has(c.sha)) continue;
    const id = join.length;
    let cur = c, d = 0;
    while (cur && !seg.has(cur.sha)) { seg.set(cur.sha, id); depth.set(cur.sha, d++); cur = commitBySha(cur.parents[0]); }
    join.push(cur ? cur.sha : null);
  }
  /* A `sha` a `from` első szülők láncán van (vagy maga a `from`). */
  const onChain = (from, sha) => {
    for (let cur = from; cur; cur = join[seg.get(cur)]) {
      if (seg.get(sha) === seg.get(cur) && depth.get(sha) >= depth.get(cur)) return true;
    }
    return false;
  };
  return onChain;
}

/* A merge-ek birtoka (`owner`: commit → az a merge, amely behozta) és merge-enként a közvetlen,
   nem ref-es commitok száma (`direct`): csak az adattól függ. A régebbi merge-ek előbb választanak,
   így a beágyazott merge a saját ágát birtokolja, a külső a belső merge-et és a saját ágát. */
let baseCache = null;
function base() {
  if (baseCache?.data === DATA) return baseCache;
  const fixed = roots(), onChain = segments(), owner = new Map(), direct = new Map();
  for (let i = DATA.commits.length - 1; i >= 0; i--) {
    const m = DATA.commits[i];
    if (!isMerge(m)) continue;
    let n = 0;
    const stack = m.parents.slice(1);
    while (stack.length) {
      const sha = stack.pop();
      const c = commitBySha(sha);
      if (!c || owner.has(sha) || onChain(m.sha, sha)) continue;
      owner.set(sha, m.sha);
      if (!fixed.has(sha)) n++;
      stack.push(...c.parents);
    }
    if (n) direct.set(m.sha, n);
  }
  baseCache = { data: DATA, fixed, owner, direct };
  return baseCache;
}

let cache = null;
/* A látható commitok (`shown`), merge-enként a kibontáskor megjelenő sorok száma (`counts`), az
   összecsukható merge-ek (`foldable`: van, amit elrejtenének) és a birtok (`owner`). */
export function layout() {
  if (cache?.data === DATA && cache.on === collapseOn() && cache.version === version) return cache;
  const { fixed, owner, direct } = base();
  // A merge a birtoka fölött áll a listában: egy menetben eldől, ki látszik.
  const shown = new Set();
  for (const c of DATA.commits) {
    const m = owner.get(c.sha);
    if (fixed.has(c.sha) || !m || (shown.has(m) && isOpen(m))) shown.add(c.sha);
  }
  const counts = new Map();
  for (const [m, n] of direct) if (shown.has(m) && !isOpen(m)) counts.set(m, n);
  cache = { data: DATA, on: collapseOn(), version, shown, counts, foldable: new Set(direct.keys()), owner, fixed };
  return cache;
}
export const hiddenSha = sha => Boolean(commitBySha(sha)) && !layout().shown.has(sha);

/* Rejtett commit felfedése: a birtokló merge-ek láncán (belülről kifelé) mind kibontva, a
   legközelebbi mindig látható commitig. */
export function reveal(sha) {
  if (!hiddenSha(sha)) return;
  const { owner, fixed } = layout();
  for (let m = owner.get(sha); m; m = fixed.has(m) ? null : owner.get(m)) if (!isOpen(m)) setOpen(m, true);
}

/* Az él célja, ha a szülő rejtett: az első szülő láncán az első nem rejtett commit (null: nincs). */
export function visibleBelow(sha) {
  let c = commitBySha(sha);
  while (c && hiddenSha(c.sha)) c = commitBySha(c.parents[0]);
  return c ? c.sha : null;
}
