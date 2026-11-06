/* Merge-ek összecsukása: a csak egy merge 2. (vagy további) szülőjén át elérhető commitok a merge
   alá rejtve. Minden ref (ág, remote, tag, HEAD, stash, WIP) first-parent lánca látható marad. Az
   alapállapot a repó beállítása (`meta.collapseMerges`, a `settings` tool írja); merge-enként a
   nyíl felülírja — csak a lap memóriájában, az újratöltésig, a kapcsoló váltása törli. */
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

/* A gyökerek: ami ref-es, WIP, stash, worktree HEAD-je, vagy aminek nincs gyereke a listában. */
function roots() {
  const child = new Set(DATA.commits.flatMap(c => c.parents));
  const heads = new Set((DATA.meta.worktrees || []).map(w => w.head));
  return DATA.commits.filter(c => c.refs.length || c.uncommitted || c.stash || heads.has(c.sha) || !child.has(c.sha))
    .map(c => c.sha);
}

/* A `from`-ból elérhető commitok: az első szülő mentén, és a `through` merge-ek többi szülőjén át;
   a `stop`-ban lévőknél megáll (azok már látszanak). */
function walk(from, through, stop = new Set()) {
  const seen = new Set(), stack = [...from];
  while (stack.length) {
    const sha = stack.pop();
    if (seen.has(sha) || stop.has(sha)) continue;
    const c = commitBySha(sha);
    if (!c) continue;
    seen.add(sha);
    if (c.parents[0]) stack.push(c.parents[0]);
    if (isMerge(c) && through(c)) stack.push(...c.parents.slice(1));
  }
  return seen;
}

/* A refek first-parent láncai (`base`) és a gyökerek: csak az adattól függenek. */
let baseCache = null;
function base() {
  if (baseCache?.data !== DATA) {
    const from = roots();
    baseCache = { data: DATA, from, chains: walk(from, () => false) };
  }
  return baseCache;
}

let cache = null;
/* A látható commitok (`shown`), merge-enként a kibontáskor közvetlenül megjelenő sorok száma
   (`counts`), az összecsukható merge-ek (`foldable`: van, amit elrejtenének), és a rejtett commitok
   felfedője (`owner`: a látható, összecsukott merge, amely alatt — akár mélyebben — ül). */
export function layout() {
  if (cache?.data === DATA && cache.on === collapseOn() && cache.version === version) return cache;
  const { from, chains } = base();
  const shown = walk(from, c => isOpen(c.sha));
  const counts = new Map(), foldable = new Set(), owner = new Map();
  for (const c of DATA.commits) {
    if (!isMerge(c) || c.parents.slice(1).every(p => chains.has(p) || !commitBySha(p))) continue;
    foldable.add(c.sha);
    if (shown.has(c.sha) && !isOpen(c.sha)) {
      const extra = c.parents.slice(1);
      counts.set(c.sha, walk(extra, m => isOpen(m.sha), shown).size);
      for (const sha of walk(extra, () => true, shown)) if (!owner.has(sha)) owner.set(sha, c.sha);
    }
  }
  cache = { data: DATA, on: collapseOn(), version, shown, counts, foldable, owner };
  return cache;
}
export const hiddenSha = sha => Boolean(commitBySha(sha)) && !layout().shown.has(sha);

/* Rejtett commit felfedése: a tartalmazó merge-ek (kívülről befelé) kibontva. */
export function reveal(sha) {
  while (hiddenSha(sha)) {
    const owner = layout().owner.get(sha);
    if (!owner) return;
    setOpen(owner, true);
  }
}

/* Az él célja, ha a szülő rejtett: az első szülő láncán az első nem rejtett commit (null: nincs). */
export function visibleBelow(sha) {
  let c = commitBySha(sha);
  while (c && hiddenSha(c.sha)) c = commitBySha(c.parents[0]);
  return c ? c.sha : null;
}
