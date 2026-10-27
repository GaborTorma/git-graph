/* Az adatból számolt nézet: a saját worktree, a halvány (idegen) commitok, színek,
   keresőtáblák, elérhetőség, a friss commitok. */
import { DATA, SLUG, branchKeep } from './state.js';

// Sáv-paletta: a CDS `chart-categorical` 1–8 (page.css: `--lane-<n>`, témánként), a 9.
// sávtól elölről. A szín CSS-változó: témaváltáskor a gráf magától átszíneződik.
const LANES = 8;

// Friss commitok: a legújabbtól visszafelé, amíg a szomszédok közt ≤ 10 mp telt
// el — és csak 5 percig. Egy újabb sorozat így magától leváltja az előzőt.
const FRESH_GAP_MS = 10 * 1000, FRESH_FOR_MS = 5 * 60 * 1000;
export let fresh = new Set();
let freshTimer = 0;

/* ── A „saját” worktree ───────────────────────────────────────────────────
   A worktree-k közös lapot látnak, és az app ezt az egy keretet mutatja
   minden sessionben. Hogy épp melyik session van előtérben, azt a szerver
   tudja (a Claude app naplójából és session-fájljaiból, `focus` a
   `changes` válaszában): annak
   a worktree-je a saját. Kézzel nem választható — a HEAD ott van, ahol a
   session dolgozik, minden git-parancsa ott fut. */
export let focusAuto = null;        // { worktree, known } — a szervertől
export const setFocusAuto = focus => { focusAuto = focus; };
export const worktrees = () => DATA.meta.worktrees || [];
export const linkedWts = () => worktrees().filter(w => !w.main);
/* A remote ágak kapcsolója (alapból be): a távolságok, a badge-ek, az ágválasztó és a szűrés is ezt nézi. */
export const remotesOn = () => /** @type {HTMLInputElement} */ (document.getElementById('showRemotes'))?.checked ?? true;
/* Remote-onkénti szűrő (több remote-nál): a rejtett remote-ok nevei. Repónként megmarad
   (a lap tárolja, mint a témát; a kulcsban a repó slugja). */
const HIDDEN_KEY = `git-graph:hidden-remotes:${SLUG}`;
export let hiddenRemotes = (() => {
  try { return new Set(JSON.parse(localStorage.getItem(HIDDEN_KEY) || '[]')); } catch { return new Set(); }
})();
export function toggleRemote(name) {
  hiddenRemotes = new Set(hiddenRemotes);
  if (!hiddenRemotes.delete(name)) hiddenRemotes.add(name);
  try { localStorage.setItem(HIDDEN_KEY, JSON.stringify([...hiddenRemotes])); } catch { /* privát ablak: nem baj */ }
}
/* A remote ref remote-ja: a leghosszabb illeszkedő remote-név (a név maga is tartalmazhat `/`-t). */
const remoteOf = ref => (DATA.meta.remotes || []).filter(r => ref.startsWith(`${r}/`))
  .reduce((a, r) => (r.length > a.length ? r : a), '');
/* Rejtett-e a remote ref a remote-szűrő szerint (egy remote-nál nincs szűrő). */
export const remoteHidden = ref => (DATA.meta.remotes || []).length > 1 && hiddenRemotes.has(remoteOf(ref));
/* Látszik-e a remote ref: a kapcsoló be, és a remote-ja nincs elrejtve. */
export const remoteShown = ref => remotesOn() && !remoteHidden(ref);
/* A commit refjei a rejtett remote-ok refjei nélkül. */
export const shownRefs = refs => refs.filter(r => r.kind !== 'remote' || !remoteHidden(r.name));
/* A saját worktree; a fő checkout, ha a session nem egy worktree-ben dolgozik. */
export function focusWt() {
  const wts = worktrees();
  return wts.find(w => w.slug === focusAuto?.worktree) || wts.find(w => w.main) || wts[0];
}
/* Ami nem a saját worktree-é, halványabb (`.foreign`). A git nem jegyzi fel,
   hol hozták létre az ágat — a gazdátlan (sehol ki nem vett) ágak a fő
   checkouté, mint a sávokban is:
   - worktree-ből nézve: ami a saját HEAD-jéből nem érhető el (és nem a saját
     ál-sora) — más ág, a fő checkout és más worktree-k WIP-je;
   - a fő checkoutból nézve: csak a hozzáadott worktree-k saját commitjai (a
     HEAD-jükből elérhető, a fő checkoutéból nem) és az ál-soraik. */
/* Az ál-sor a worktree-jéé; a stash a gazdájáé (`owner`, a szervertől) — semmilyen
   HEAD-ből nem érhető el. */
const home = c => c.stash ? c.owner : c.worktree;
let foreignSet = null;
export function computeOwn() {
  const own = focusWt(), linked = linkedWts();
  foreignSet = null;
  if (!own || !linked.length) return;               // worktree nélkül nincs mit elválasztani
  const reach = head => reachable(head ? [head] : []);
  const mine = reach(own.head);
  if (own.main) {
    foreignSet = new Set();
    for (const w of linked) for (const sha of reach(w.head)) if (!mine.has(sha)) foreignSet.add(sha);
    for (const c of DATA.commits) if ((c.uncommitted || c.stash) && home(c) !== own.slug) foreignSet.add(c.sha);
  } else {
    foreignSet = new Set(DATA.commits.filter(c => !mine.has(c.sha) && home(c) !== own.slug).map(c => c.sha));
  }
}
export const foreign = c => Boolean(foreignSet) && foreignSet.has(c.sha);
/* A halvány pötty és vonal tömör, a háttérrel kevert szín — átlátszósággal
   a pöttyön átütne az alatta futó vonal. */
const FADE = 45;
export const fade = color => `color-mix(in srgb, ${color} ${FADE}%, var(--bg))`;
export const tint = (c, color) => foreign(c) ? fade(color) : color;
export const laneColor = lane => `var(--lane-${lane % LANES})`;
/* A chip színe (`--lc`) és a tint-hármasa (`--lc-bg`, `--lc-fg`, `--lc-bd`) inline stílusként:
   sávszínnél a sáv CDS-tintje; más színnél csak a `--lc`, a többi a CSS keveréke. */
export const lcStyle = color => {
  const lane = /^var\(--lane-(\d+)\)$/.exec(color)?.[1];
  return `--lc:${color}` + (lane ? `;--lc-bg:var(--lane-${lane}-bg);--lc-fg:var(--lane-${lane}-fg);--lc-bd:var(--lane-${lane}-bd)` : '');
};
/* Keresőtáblák az adatból (sha → commit, ref → csúcs-commit, worktree → csonk és
   ál-sor): a DATA cseréjekor egyszer épülnek, a sor- és ágválasztó-rajzolás nem
   pásztázza végig a commitokat. */
let indexed = null, index = null;
function idx() {
  if (indexed !== DATA) {
    indexed = DATA;
    index = { bySha: new Map(), refTip: new Map(), stub: new Map(), wip: new Map() };
    for (const c of DATA.commits) {
      index.bySha.set(c.sha, c);
      for (const r of c.refs) if (r.kind !== 'tag' && !index.refTip.has(r.name)) index.refTip.set(r.name, c);
      for (const t of c.stubs || []) if (!index.stub.has(t.worktree)) index.stub.set(t.worktree, t);
      if (c.worktree && !index.wip.has(c.worktree)) index.wip.set(c.worktree, c);
    }
  }
  return index;
}
export const commitBySha = sha => idx().bySha.get(sha);
/* Saját commit és WIP nélküli worktree leágazó csonkja (`stubs`, a szervertől). */
const stubOf = slug => idx().stub.get(slug);
/* A worktree színe a gráfban: a csonkja, az ál-sora, vagy a HEAD-je sávjáé. */
export function wtColor(w) {
  const c = stubOf(w.slug) || idx().wip.get(w.slug) || commitBySha(w.head);
  return c ? laneColor(c.lane) : '';
}
/* Egy ref színe a gráfban: a csúcs-commitja sávjáé (az ágválasztó ikonjaihoz). */
export function refColor(name) {
  const c = idx().refTip.get(name);
  return c ? laneColor(c.lane) : 'var(--fg-3)';
}

/* A friss sorozat sha-i; lejáratkor a lap magától újrarajzol (`onExpire`; a pollozás
   csak git-változásra rajzol). Az ál-sornak nincs `committed`-je: sosem friss. */
export function computeFresh(onExpire) {
  clearTimeout(freshTimer);
  const times = DATA.commits.filter(c => c.committed)
    .map(c => ({ sha: c.sha, t: Date.parse(c.committed) }))
    .sort((a, b) => b.t - a.t);
  fresh = new Set();
  if (!times.length) return;
  const left = times[0].t + FRESH_FOR_MS - Date.now();
  if (left <= 0) return;
  for (let i = 0; i < times.length; i++) {
    if (i && times[i - 1].t - times[i].t > FRESH_GAP_MS) break;
    fresh.add(times[i].sha);
  }
  freshTimer = setTimeout(() => { fresh = new Set(); onExpire(); }, left);
}

/* Remote ref-e a név: valamelyik helyi ág upstreamje, vagy csak remote ág. */
export const remoteRefs = () => new Set(DATA.branches.flatMap(b => b.remote ? [b.name] : b.upstream ? [b.upstream] : []));

export function branchColor(b) {
  const w = worktrees().find(x => (b.worktree && x.slug === b.worktree) || (!x.branch && x.appBranch === b.name));
  return (w && wtColor(w)) || refColor(b.name);
}

/* A kijelölt refek őseinek uniója (null, ha egyik csúcsa sincs a listában). */
export function ancestryOf(names) {
  const tips = DATA.commits.filter(c => c.refs.some(r => names.has(r.name) && r.kind !== 'tag'));
  return tips.length ? reachable(tips.map(c => c.sha)) : null;
}
/* A (rejtett) remote ágak nélkül: ami helyi ágból, HEAD-ből, tagből, WIP-ből vagy látható
   remote ágból elérhető. */
export const localReach = () => reachable(DATA.commits.filter(c => c.uncommitted
  || c.refs.some(r => r.kind !== 'remote' || remoteShown(r.name))).map(c => c.uncommitted ? c.parents[0] : c.sha));
function reachable(tips) {
  const keep = new Set(), stack = [...tips];
  const { bySha } = idx();
  while (stack.length) {
    const sha = stack.pop();
    if (keep.has(sha)) continue;
    keep.add(sha);
    (bySha.get(sha)?.parents || []).forEach(p => bySha.has(p) && stack.push(p));
  }
  return keep;
}

export const headFiltered = () => Boolean(branchKeep && !branchKeep.has(focusWt()?.head));
