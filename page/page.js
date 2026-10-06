
/* A betöltő (az Artifact publikált lapja) adja: a repó slugja és neve, az MCP
   kliens. Az adatot a lap a Claude app host-hídján át a gépen futó
   `git-graph --mcp`-ből kéri (a SLUG repóét); induláskor csak az üres váz van. */
const CTX = globalThis.GIT_GRAPH;
const SLUG = CTX.slug;
const MCP_SERVER = CTX.server;
let DATA = { commits: [], edges: [], stats: {}, branches: [], avatars: {},
  meta: { repo: CTX.repo, repoUrl: '', head: '', totalCommits: 0, shown: 0, dirty: 0,
          generated: '', worktrees: [] } };

// Sáv-paletta: a 0. sáv a Claude narancs, a többi vele egyező telítettségű.
const LANE_COLORS = ['#d97757', '#5b8def', '#4fa564', '#a07ad6', '#cf9a2c',
                     '#2f9c9a', '#d0628f', '#8a9a3a', '#6a7fd1', '#c4573a'];
const ROW_H = 30, LANE_W = 14, X0 = 16, DOT_R = 4;
const EDGE_HUG = DOT_R + 1;   // a sávváltó vonal ennyit fut a commit sávjában, mielőtt elfordul
const STUB_GAP = 11;   // több worktree-csonk pöttyei közti függőleges távolság
// Friss commitok: a legújabbtól visszafelé, amíg a szomszédok közt ≤ 10 mp telt
// el — és csak 5 percig. Egy újabb sorozat így magától leváltja az előzőt.
const FRESH_GAP_MS = 10 * 1000, FRESH_FOR_MS = 5 * 60 * 1000;
let fresh = new Set();
let freshTimer = 0;

const rowsEl = document.getElementById('rows');
const svg = document.getElementById('lanes');
const counter = document.getElementById('counter');
const scroller = document.querySelector('.scroll');
let expanded = null;      // a kinyitott commit sha-ja
let visible = DATA.commits; // szűrés utáni lista

let graphW = 72;

/* ── A „saját” worktree ───────────────────────────────────────────────────
   A worktree-k közös lapot látnak, és az app ezt az egy keretet mutatja
   minden sessionben. Hogy épp melyik session van előtérben, azt a szerver
   tudja (a Claude app naplójából és session-fájljaiból, `focus` a
   fingerprintben): annak
   a worktree-je a saját. Kézzel nem választható — a HEAD ott van, ahol a
   session dolgozik, minden git-parancsa ott fut. */
let focusAuto = null;        // { worktree, known } — a szervertől
const worktrees = () => DATA.meta.worktrees || [];
const linkedWts = () => worktrees().filter(w => !w.main);
/* A remote ágak kapcsolója (alapból be): a távolságok, a badge-ek, az ágválasztó és a szűrés is ezt nézi. */
const remotesOn = () => document.getElementById('showRemotes')?.checked ?? true;
/* A saját worktree; a fő checkout, ha a session nem egy worktree-ben dolgozik. */
function focusWt() {
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
let foreignSet = null;
function computeOwn() {
  const own = focusWt(), linked = linkedWts();
  foreignSet = null;
  if (!own || !linked.length) return;               // worktree nélkül nincs mit elválasztani
  const reach = head => reachable(head ? [head] : []);
  const mine = reach(own.head);
  if (own.main) {
    foreignSet = new Set();
    for (const w of linked) for (const sha of reach(w.head)) if (!mine.has(sha)) foreignSet.add(sha);
    for (const c of DATA.commits) if (c.uncommitted && c.worktree !== own.slug) foreignSet.add(c.sha);
  } else {
    foreignSet = new Set(DATA.commits.filter(c => !mine.has(c.sha) && c.worktree !== own.slug).map(c => c.sha));
  }
}
const foreign = c => Boolean(foreignSet) && foreignSet.has(c.sha);
/* A halvány pötty és vonal tömör, a háttérrel kevert szín — átlátszósággal
   a pöttyön átütne az alatta futó vonal. */
const FADE = 45;
const fade = color => `color-mix(in srgb, ${color} ${FADE}%, var(--bg))`;
const tint = (c, color) => foreign(c) ? fade(color) : color;
const laneColor = lane => LANE_COLORS[lane % LANE_COLORS.length];
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
const commitBySha = sha => idx().bySha.get(sha);
/* Saját commit és WIP nélküli worktree leágazó csonkja (`stubs`, a szervertől). */
const stubOf = slug => idx().stub.get(slug);
/* A worktree színe a gráfban: a csonkja, az ál-sora, vagy a HEAD-je sávjáé. */
function wtColor(w) {
  const c = stubOf(w.slug) || idx().wip.get(w.slug) || commitBySha(w.head);
  return c ? laneColor(c.lane) : '';
}
/* Egy ref színe a gráfban: a csúcs-commitja sávjáé (az ágválasztó ikonjaihoz). */
function refColor(name) {
  const c = idx().refTip.get(name);
  return c ? laneColor(c.lane) : 'var(--fg-3)';
}
const wtLabel = w => w.branch || `HEAD ${String(w.head || '').slice(0, 7)}`;

/* ── Ikonok ── stroke-os, 16×16-os rácson; a CSS `.ic` színezi. */
const ICONS = {
  branch: '<circle cx="5" cy="3.5" r="1.5"/><circle cx="5" cy="12.5" r="1.5"/><circle cx="11" cy="5.5" r="1.5"/><path d="M5 5v6M11 7c0 2.5-3 2.5-6 4"/>',
  tag: '<path d="M2.5 2.5h5l6 6-5 5-6-6z"/><circle cx="5.5" cy="5.5" r="1"/>',
  cloud: '<path d="M4.5 12.5h7a3 3 0 0 0 .4-6A4 4 0 0 0 4.3 7.6 2.5 2.5 0 0 0 4.5 12.5z"/>',
  // teli felhő: az alapág (az origin/HEAD célja) — default ág csak remote-on van
  cloudFill: '<path fill="currentColor" d="M4.5 12.5h7a3 3 0 0 0 .4-6A4 4 0 0 0 4.3 7.6 2.5 2.5 0 0 0 4.5 12.5z"/>',
  parent: '<circle cx="8" cy="5" r="2.25"/><path d="M8 7.25v6.25M5.5 11 8 13.5 10.5 11"/>',
  open: '<path d="M9.5 2.5h4v4M13.5 2.5 7.5 8.5M12 9.5v3a1 1 0 0 1-1 1H3.5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h3"/>',
  issue: '<circle cx="8" cy="8" r="5.75"/><circle cx="8" cy="8" r="1.1" fill="currentColor"/>',
  pr: '<circle cx="4" cy="3.5" r="1.5"/><circle cx="4" cy="12.5" r="1.5"/><circle cx="12" cy="12.5" r="1.5"/><path d="M4 5v6M12 11V6.5a2 2 0 0 0-2-2H7.5M9 3 7.5 4.5 9 6"/>',
  // a GitHub-jel (Octicons mark-github, MIT): telt, nem vonalas
  github: '<path fill="currentColor" stroke="none" d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"/>',
  copy: '<rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 5.5V3.5a1 1 0 0 0-1-1h-6a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2"/>',
  check: '<path d="m3.5 8.5 3 3 6-7"/>',
  file: '<path d="M4 1.5h5l3.5 3.5v9.5H4z"/><path d="M9 1.5V5h3.5"/>',
  chev: '<path d="M6.5 4.5 10 8l-3.5 3.5"/>',
  // a worktree-jel: mappa, benne egy kör (a kivett állapot) — saját rajz a készlet vonalvastagságával
  worktree: '<path class="wt-ic" d="M3 13a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h2.5L7 4.5h6a1 1 0 0 1 1 1V12a1 1 0 0 1-1 1z"/>'
    + '<circle class="wt-ic" cx="8" cy="9" r="1.5" fill="currentColor"/>',
  // a fő checkout: ugyanaz a mappa, pötty nélkül — maga a repó, nem egy kivett másolat
  mainWorktree: '<path class="wt-ic" d="M3 13a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h2.5L7 4.5h6a1 1 0 0 1 1 1V12a1 1 0 0 1-1 1z"/>',
  // ág és upstream egy helyen: felhő, az alsó vonala közepén csomópont, onnan ág két
  // csomópontra; a teli változat (alapág) a csomópont körül kivágva. A Fejlesztő
  // rajza (CorelDRAW), 16-os rácsra méretezve, a készlet 1,5-ös vonalával.
  branchCloud: '<path d="M12.07 9.06c1.16-0.4 2-1.5 2-2.79 0-1.55-1.2-2.84-2.75-2.94-0.64-1.4-2.03-2.29-3.57-2.29-1.95 0-3.61 1.44-3.89 3.37-1.1 0.26-1.88 1.25-1.88 2.39 0 0.97 0.57 1.83 1.42 2.23"/><circle cx="7.73" cy="8.4" r="1.6"/><path d="M7.73 10.81l0 2.56m-3.73 0l7.47 0"/><circle cx="2.4" cy="13.37" r="1.6"/><circle cx="13.6" cy="13.37" r="1.6"/>',
  branchCloudFill: '<path fill="currentColor" stroke="none" d="M12.07 9.06c1.16-0.4 2-1.5 2-2.79 0-1.55-1.2-2.84-2.75-2.94-0.64-1.4-2.03-2.29-3.57-2.29-1.95 0-3.61 1.44-3.89 3.37-1.1 0.26-1.88 1.25-1.88 2.39 0 0.97 0.57 1.83 1.42 2.22 0.06-2.35 1.98-4.23 4.34-4.23 2.38 0 4.3 1.91 4.34 4.28z"/><circle cx="7.73" cy="8.4" r="1.6"/><path d="M7.73 10.81l0 2.56m-3.73 0l7.47 0"/><circle cx="2.4" cy="13.37" r="1.6"/><circle cx="13.6" cy="13.37" r="1.6"/><path d="M12.07 9.06c1.16-0.4 2-1.5 2-2.79 0-1.55-1.2-2.84-2.75-2.94-0.64-1.4-2.03-2.29-3.57-2.29-1.95 0-3.61 1.44-3.89 3.37-1.1 0.26-1.88 1.25-1.88 2.39 0 0.97 0.57 1.83 1.42 2.22l0-0.7 0 0c0-2.4 1.94-4.34 4.34-4.34 2.4 0 4.34 1.94 4.34 4.34l0 0 0 0.75z"/>',
  // minden ág: két sáv, egy-egy üres csomóponttal, mint a branch-ikonon
  allBranches: '<path d="M5 2.5v6M5 11.5v2M11 2.5v2M11 7.5v6"/><circle cx="5" cy="10" r="1.5"/><circle cx="11" cy="6" r="1.5"/>',
  // leválasztott HEAD az ágválasztóban: szétkapcsolt lánc
  detached: '<path d="M6.5 9.5 4.8 11.2a2 2 0 0 1-2.8-2.8L3.7 6.7M9.5 6.5l1.7-1.7a2 2 0 0 1 2.8 2.8l-1.7 1.7M5.5 2.5V4M2.5 5.5H4M10.5 13.5V12M13.5 10.5H12"/>',
};
const icon = (name, cls = 'ic') => `<svg class="${cls}" viewBox="0 0 16 16" aria-hidden="true">${ICONS[name]}</svg>`;
// Fájltípus-ikon: a git-graph a fájlhoz rendelt Catppuccin-ikon SVG-jét adja
// (`fileIcons`, a színei a lap `--ic-*` tokenjei); régi szervernél az általános ikon.
const fileIcon = f => {
  const svg = DATA.fileIcons?.[f.icon];
  return svg ? svg.replace('<svg', '<svg class="fic" aria-hidden="true"') : icon('file', 'ic fic');
};

/* A friss sorozat sha-i; lejáratkor a lap magától újrarajzol (a pollozás csak
   git-változásra rajzol). Az ál-sornak nincs `committed`-je: sosem friss. */
function computeFresh() {
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
  freshTimer = setTimeout(() => { fresh = new Set(); render(); }, left);
}

/* Minden, ami a DATA-ból származik és adatcserekor újraszámolandó. */
function hydrate() {
  computeFresh();
  const laneCount = DATA.commits.reduce((m, c) => Math.max(m, c.lane, ...(c.stubs || []).map(t => t.lane)), 0) + 1;
  graphW = Math.max(32, X0 * 2 + (laneCount - 1) * LANE_W);
  document.documentElement.style.setProperty('--graph-w', graphW + 'px');
  document.getElementById('repoName').textContent = DATA.meta.repo;
  hydrateFocus();
  const base = DATA.meta.repoUrl;
  document.getElementById('footLinks').innerHTML = base
    ? ghLink(`${base}/issues`, icon('issue'), 'mini', 'Issue-k a GitHubon')
      + ghLink(`${base}/pulls`, icon('pr'), 'mini', 'Pull requestek a GitHubon')
      + ghLink(base, icon('github'), 'mini', 'A repó a GitHubon') : '';
  fitChrome();                // a repó- és ágnév hossza dönt a kompakt fejlécről
  hydrateAvatars();
}

/* A HEAD-chip a saját worktree ágát mutatja; több worktree-nél fölötte a
   worktree-pillek: ág, változások pöttye, ↑ahead. */
/* A fejléc chipje (a saját worktree-é): worktree-ikon,
   branch-ikon, az ág neve és az ág távolságai (`distSegs`). A commitolatlan
   változást a rögzített sáv WIP-sora mutatja. */
function wtChipInner(w) {
  const linked = !w.main;
  // A fő checkout üres mappát kap, ha vannak worktree-k (megkülönböztetésül).
  return (linked ? icon('worktree') : linkedWts().length ? icon('mainWorktree') : '')
    + (w.branch ? icon('branch') : '')   // ág nélkül: csak a HEAD és a hash
    + `<span class="chip-name">${esc(wtLabel(w))}</span>`
    + (w.branch ? distSegs(w.branch) : '');
}

/* Az ág távolságai (`DATA.meta.tracks`, csak a nem nulla irány): `↑a ↓b` az
   alapághoz (amire az origin/HEAD mutat) — ikon nélkül, a chip maga az ág —, és
   `☁ ↑c ↓d` az upstreamjéhez, csak ha nem egy helyen állnak (különben a chip a
   felhő-és-ág ikont kapja); a remote-only chipen utolsóként `⑂ ↑e ↓f` a helyi ágához.
   Ami a chipből már kiderül, annak nem jár újabb ikon. */
const arrows = ([a, b]) => [a && `↑${a}`, b && `↓${b}`].filter(Boolean).join(' ');
/* Ugyanez szövegesen, a tooltipbe (soronként egy viszony). */
function distText(name) {
  const tr = DATA.meta.tracks?.[name] || {};
  const base = (DATA.meta.base || 'main').replace(/^[^/]+\//, '');
  const lines = [];
  if (tr.base?.[0]) lines.push(`↑${tr.base[0]}: ennyi commit az ágon a ${base} óta`);
  if (tr.base?.[1]) lines.push(`↓${tr.base[1]}: ennyit haladt közben a ${base}`);
  if (tr.up?.[0]) lines.push(`☁ ↑${tr.up[0]}: pusholatlan commit`);
  if (tr.up?.[1]) lines.push(`☁ ↓${tr.up[1]}: a remote-on van, helyben nincs`);
  if (tr.local?.[0]) lines.push(`⑂ ↑${tr.local[0]}: ennyivel jár a helyi ág előtt`);
  if (tr.local?.[1]) lines.push(`⑂ ↓${tr.local[1]}: ennyivel van a helyi ág mögött`);
  return lines.length ? `\n${lines.join('\n')}` : '';
}
function distSegs(name) {
  const tr = DATA.meta.tracks?.[name] || {};
  // Remote ágak nélkül a remote-hoz mért szakaszok sem kellenek (☁ és a remote chip ⑂-je).
  const remote = remotesOn();
  // Az alapág helyi párján (pl. `main`) nem dolgozunk: ha előrébb jár a remote-jánál,
  // az anomália (teszt vagy tévedés) — figyelmeztető szín és magyarázat.
  const base = DATA.meta.base || '', local = base.slice(base.indexOf('/') + 1);
  const odd = base && name === local && tr.up?.[0] > 0;
  const warn = odd ? ` warn" data-tip="${esc(`A helyi ${name}-en ${tr.up[0]} pusholatlan commit van`)}` : '';
  return [[tr.base, '', ''], [remote && tr.up, icon('cloud'), warn], [remote && tr.local, icon('branch'), '']]
    .filter(([d]) => d && (d[0] || d[1]))
    .map(([d, ic, cls]) => `<span class="div"></span><span class="dist${cls}">${ic}${arrows(d)}</span>`).join('');
}
function hydrateFocus() {
  const wts = worktrees(), own = focusWt();
  const chip = document.getElementById('headChip');
  // A fejléc chipje a saját ág gráfbeli színét viseli; worktree-ben a worktree-ikonnal,
  // az előnnyel és — ha van commitolatlan változás — üres karikával, mint az ál-sor pontja.
  chip.style.setProperty('--lc', (own && wtColor(own)) || 'var(--accent)');
  chip.innerHTML = own ? wtChipInner(own) : icon('branch') + esc(DATA.meta.head || '');
  chip.hidden = !(own || DATA.meta.head);
  chip.title = !own ? '' : (own.main ? 'fő checkout: ' : 'worktree: ') + own.path
    + (wts.length < 2 ? ''
      : focusAuto?.known ? '\naz előtérben lévő session itt dolgozik'
      : '\nnincs ismert session a repóban — a fő checkout')
    + (own.branch ? distText(own.branch) : '');
  computeOwn();
}

/* Az avatarok (data URI, néhány KB) szerzőnként egyszer kerülnek a lapra, egy
   stíluslapba (`.av<n>` háttérkép); a sor csak az osztályt kapja — különben
   minden sor újra beágyazná a képet, és a render ezt sokszor újraépítené. */
const avatarStyle = document.head.appendChild(document.createElement('style'));
let avatarClass = new Map();          // e-mail → osztálynév
function hydrateAvatars() {
  const entries = Object.entries(DATA.avatars || {});
  avatarClass = new Map(entries.map(([email], i) => [email, `av${i}`]));
  avatarStyle.textContent = entries
    .map(([, url], i) => `.av${i}{background-image:url("${url.replace(/["\\\n]/g, '')}")}`).join('\n');
}
const avatarOf = c => DATA.avatars?.[c.email];

/* ── Gráf rajzolása ──────────────────────────────────────────────────────── */
function laneX(l) { return X0 + l * LANE_W; }

/* A sorok Y-pozíciója a DOM-ból jön, nem sorszám × magasság: a napok fejléce
   és a kinyitott commit-panel az alattuk lévő sorokat lejjebb tolja, és a
   pöttyöknek velük kell menniük — közben a vonal egyszerűen hosszabb lesz. */
/* Az Uncommitted ál-sorok a lista FÖLÖTT, a fix `#pending` sávban ülnek: a
   pontjuk ott van, a szaggatott vonaluk innen, a lista teteje fölül (negatív
   Y, az SVG túllóghat) fut le a HEAD-ig. */
const WRAP_TOP = 4;                   // a .graph-wrap felső margója
function drawGraph() {
  drawPending();
  const rowIndexBySha = new Map(visible.map((c, i) => [c.sha, i]));
  // A sor közepe: a kétsoros sor (`.two`) magasabb.
  const listRows = [...rowsEl.querySelectorAll('.row')];
  const midBySha = new Map(listRows.map(el => [el.dataset.sha, el.offsetTop + el.offsetHeight / 2]));
  const heightBySha = new Map(listRows.map(el => [el.dataset.sha, el.offsetHeight]));
  for (const el of pendingEl.querySelectorAll('.row')) {
    midBySha.set(el.dataset.sha, el.offsetTop + el.offsetHeight / 2 - pendingEl.offsetHeight - WRAP_TOP);
  }
  const rowY = i => midBySha.get(visible[i].sha) ?? i * ROW_H + ROW_H / 2;
  const h = Math.max(rowsEl.offsetHeight, visible.length * ROW_H);
  svg.setAttribute('width', graphW);
  svg.setAttribute('height', h);
  svg.setAttribute('viewBox', `0 0 ${graphW} ${h}`);

  // Az egyenesek előbb, a sávváltó vonalak felül: az elágazás a commit pöttyénél
  // is a saját színével indul, nem takarja el a sáv vonala.
  let out = '', bends = '';
  for (const e of DATA.edges) {
    const a = rowIndexBySha.get(DATA.commits[e.fromRow].sha);
    const b = rowIndexBySha.get(DATA.commits[e.toRow].sha);
    if (a === undefined || b === undefined) continue;   // szűrve
    const x1 = laneX(e.fromLane), y1 = rowY(a);
    const x2 = laneX(e.toLane),   y2 = rowY(b);
    // A vonal annak a sávnak a színét kapja, amelyikben a hossza nagy részén fut:
    // a merge-vonal rögtön a cél sávjába fordul, a leágazó csak a szülő fölött.
    const color = tint(DATA.commits[e.fromRow],
      laneColor(e.merge ? e.toLane : e.fromLane));
    // A munkakönyvtár még nem commit: szaggatva lóg a HEAD-re. Görgetve a sajátja
    // eltűnik, ha nincs alatta más WIP-sor, vagy ha a HEAD-je már a sáv alá csúszott
    // (`hideOwnEdge`); a többié látszik — különben nem tudni, hová tart.
    const from = DATA.commits[e.fromRow];
    const own = from.worktree === focusWt()?.slug ? ' own' : '';
    const dash = from.uncommitted ? ` class="pend-edge${own}" stroke-dasharray="3 3"` : '';
    const path = `<path d="${edgePath(x1, y1, x2, y2, e.merge)}" fill="none" stroke="${color}" stroke-width="2"${dash}/>`;
    if (x1 === x2) out += path; else bends += path;
  }
  out += bends;
  // A worktree csonkja: vonal a commitról a saját oszlopába, ott pötty. Több csonk
  // esetén a pöttyök a commit magassága körül, legyezőszerűen ágaznak le.
  visible.forEach((c, i) => {
    const stubs = c.stubs || [];
    if (!stubs.length) return;
    const y0 = rowY(i), x0 = laneX(c.lane), span = (heightBySha.get(c.sha) || ROW_H) - 8;
    // a pöttyök közepe a commit magassága, köztük legfeljebb STUB_GAP (a sor magasságán belül)
    const gap = Math.min(STUB_GAP, span / (stubs.length + 1));
    const ys = stubs.map((t, k) => y0 + (k - (stubs.length - 1) / 2) * gap);
    // a commit magasságától legtávolabbit rajzoljuk először: a közös szakaszon a közelebbi látszik
    const order = stubs.map((t, k) => k).sort((p, q) => Math.abs(ys[q] - y0) - Math.abs(ys[p] - y0));
    for (const k of order) {
      const t = stubs[k], y = ys[k], x = laneX(t.lane), dy = y - y0;
      const color = t.worktree === focusWt()?.slug ? laneColor(t.lane) : fade(laneColor(t.lane));
      // legyező: egyetlen sima ív a commit pöttyéből a csonk pöttyéig
      const d = !dy ? `M ${x0} ${y0} H ${x}`
        : `M ${x0} ${y0} C ${x0 + (x - x0) * 0.45} ${y0}, ${x0 + (x - x0) * 0.35} ${y}, ${x} ${y}`;
      out += `<path d="${d}" fill="none" stroke="${color}" stroke-width="2"/>`
        + `<circle cx="${x}" cy="${y}" r="${DOT_R}" fill="${color}" stroke="${color}" stroke-width="2"/>`;
    }
  });
  visible.forEach((c, i) => {
    if (c.uncommitted && c.worktree === focusWt()?.slug) return;   // a pontja a #pending sávban van
    const color = tint(c, laneColor(c.lane));
    const merge = c.parents.length > 1;
    // Az ál-sor pontja üres karika: a szaggatott vonal már jelzi, hogy nem
    // commit — a pöttyözött körvonal ezen a méreten csak elmosódna.
    const hollow = merge || c.uncommitted;
    if (fresh.has(c.sha)) out += `<circle cx="${laneX(c.lane)}" cy="${rowY(i)}" r="8" fill="${color}" opacity=".28"/>`;
    out += `<circle cx="${laneX(c.lane)}" cy="${rowY(i)}" r="${hollow ? DOT_R + 1 : DOT_R}"`
        +  ` fill="${hollow ? 'var(--bg)' : color}" stroke="${color}" stroke-width="2"/>`;
  });
  svg.innerHTML = out;
}

/* Sávváltásnál ott hajlik a vonal, ahol a git is: merge-nél rögtön a merge
   commit alatt, ág-leágazásnál pedig közvetlenül a szülő fölött. */
function edgePath(x1, y1, x2, y2, merge) {
  if (x1 === x2) return `M ${x1} ${y1} L ${x2} ${y2}`;
  // Legyező: a vonal a commit pöttyéből függőlegesen indul (fel vagy le), és a
  // worktree-csonk ívét elforgatva fordul a másik sávba egy soron belül.
  if (merge) {
    const bend = Math.min(y1 + ROW_H, y2);
    const s1 = Math.min(y1 + EDGE_HUG, bend), dy = bend - s1;
    return `M ${x1} ${y1} L ${x1} ${s1} C ${x1} ${s1 + dy * 0.45}, ${x2} ${s1 + dy * 0.35}, ${x2} ${bend} L ${x2} ${y2}`;
  }
  const bend = Math.max(y2 - ROW_H, y1);
  const s2 = Math.max(y2 - EDGE_HUG, bend), dy = bend - s2;
  return `M ${x1} ${y1} L ${x1} ${bend} C ${x1} ${s2 + dy * 0.35}, ${x2} ${s2 + dy * 0.45}, ${x2} ${s2} L ${x2} ${y2}`;
}

/* ── Dátum ── budapesti idő szerint, magyar formában. */
const TZ = 'Europe/Budapest';
const fmtParts = (iso, opts) => Object.fromEntries(new Intl.DateTimeFormat('hu-HU',
  { timeZone: TZ, ...opts }).formatToParts(new Date(iso)).map(p => [p.type, p.value]));
const dayKey = iso => { const p = fmtParts(iso, { year: 'numeric', month: '2-digit', day: '2-digit' });
  return `${p.year}-${p.month}-${p.day}`; };
const fmtTime = iso => { const p = fmtParts(iso, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
  return `${p.hour}:${p.minute}`; };
const clock = () => { const p = fmtParts(new Date(),
  { hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' });
  return `${p.hour}:${p.minute}:${p.second}`; };
/* Az idő a napjával, ha nem mai (a rögzített sávnak nincs napfejléce): `tegnap 23:30`, `okt. 3. 23:30`. */
function pinnedTime(iso) {
  if (dayKey(iso) === dayKey(new Date())) return fmtTime(iso);
  if (dayKey(iso) === dayKey(new Date(Date.now() - 864e5))) return `tegnap ${fmtTime(iso)}`;
  const p = fmtParts(iso, { month: 'short', day: 'numeric' });
  return `${p.month} ${p.day}. ${fmtTime(iso)}`;
}
const fmtDate = iso =>`${dayKey(iso).replaceAll('-', '.')}. ${fmtTime(iso)}`;
function dayLabel(key) {
  const [y, m, d] = key.split('-').map(Number);
  const long = new Intl.DateTimeFormat('hu-HU', { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' })
    .format(new Date(Date.UTC(y, m - 1, d)));
  const yesterday = dayKey(new Date(Date.now() - 864e5));
  return key === dayKey(new Date()) ? `Ma · ${long}` : key === yesterday ? `Tegnap · ${long}` : long;
}

/* ── Sorok ───────────────────────────────────────────────────────────────── */
const menuOpen = () => Boolean(document.querySelector('.menu-pop:not([hidden])'));
const esc = s => String(s).replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));

/* GitHub-linkek: valódi `<a target="_blank">` — az Artifact keretéből a Claude
   app csak ezt engedi át (mérve: a `window.open` el sem jutott hozzá). Commit
   és fájl csak pusholt commitnál (`pushed`, a Python jelöli): a helyi a
   GitHubon 404 lenne. A fájl-diff horgonyát (`anchor`) is a Python számolja. */
const ghLink = (href, html, cls = 'gh-link', label = '') =>
  `<a class="${cls}" href="${href}" target="_blank" rel="noopener"${label ? ` aria-label="${esc(label)}" title="${esc(label)}"` : ''}>${html}</a>`;

/* `#12` és `owner/repo#12` → issue/PR (a `/issues/N` a PR-ra átirányít).
   Előtte nem állhat szó- vagy URL-karakter: a `C#1` és a `lap.html#3` marad szöveg. */
const ISSUE_RE = /(^|[^\w./-])([\w.-]+\/[\w.-]+)?#(\d+)\b/g;
function linkify(s) {
  const text = esc(s), base = DATA.meta.repoUrl;
  if (!base) return text;
  return text.replace(ISSUE_RE, (m, pre, repo, n) =>
    pre + ghLink(`${repo ? 'https://github.com/' + repo : base}/issues/${n}`, `${repo || ''}#${n}`));
}
const commitUrl = c => `${DATA.meta.repoUrl}/commit/${c.sha}`;
const fileUrl = (c, f) => commitUrl(c) + (f.anchor ? '#diff-' + f.anchor : '');

/* Ha a helyi ág és a remote-ja ugyanazon a commiton áll, egy badge-ben
   látszanak (az ág neve után felhő-ikon); ha szétváltak, külön-külön. */
function mergedRefs(refs) {
  const names = new Set(refs.map(r => r.name));
  const used = new Set(), out = [];
  for (const r of refs) {
    if (used.has(r.name)) continue;
    const remotes = (r.kind === 'branch' || r.kind === 'head')
      ? refs.filter(o => o.kind === 'remote' && o.name.endsWith('/' + r.name)
          && names.has(o.name) && o.name.slice(0, -r.name.length - 1).indexOf('/') < 0)
      : [];
    remotes.forEach(o => used.add(o.name));
    out.push({ ...r, default: r.default || remotes.some(o => o.default),
      remotes: remotes.map(o => ({ name: o.name.slice(0, -r.name.length - 1), default: Boolean(o.default) })) });
  }
  return out;
}

/* A chipek sorrendje: a fő checkout HEAD-je, az ágak, a remote-ok, aztán a
   hozzáadott worktree-k HEAD-je és leválasztott HEAD-nél az águk (egymás után), végül
   a tag. */
/* A hozzáadott worktree, amelyhez a chip tartozik: a HEAD-je, vagy leválasztott
   HEAD-nél az az ág, amelyen a Claude app szerint a worktree állt (`appBranch`). */
function wtOfRef(r) {
  const linked = linkedWts();
  return r.worktree ? linked.find(w => w.slug === r.worktree)
    : r.kind === 'branch' ? linked.find(w => w.appBranch === r.name) : null;
}
function sortRefs(refs) {
  const linked = linkedWts();
  const rank = r => {
    if (r.kind === 'tag') return [9, 0];
    const w = wtOfRef(r);
    if (w) return [3 + linked.indexOf(w) * 0.01, r.worktree ? 0 : 1];
    return [{ head: 0, detached: 0, branch: 1, remote: 2 }[r.kind] ?? 2, 0];
  };
  return refs.map((r, i) => ({ r, k: [...rank(r), i] }))
    .sort((a, b) => a.k[0] - b.k[0] || a.k[1] - b.k[1] || a.k[2] - b.k[2]).map(x => x.r);
}

/* A WIP-sor eleji worktree-jel: sima (nem HEAD-) badge a worktree színével, vékony
   körvonallal — az erős körvonal a HEAD-é, a HEAD pedig mindig commit. A fő checkout:
   üres mappa és az ága; a többi: a worktree jele és neve | az ága. Ág nélkül (leválasztott
   HEAD) mindkettő: jel, név (a fő checkouté „main”) | lánc. */
function wtBadge(w) {
  const lc = w.main ? laneColor(commitBySha(w.head)?.lane || 0) : wtColor(w) || LANE_COLORS[0];
  const tip = `${w.main ? 'fő checkout' : 'worktree'}: ${w.path}\n`
    + (w.branch ? `ág: ${w.branch}${distText(w.branch)}` : `ág nélkül, HEAD: ${String(w.head || '').slice(0, 7)}`);
  const branch = w.branch ? `${icon('branch')}<span class="badge-name">${esc(w.branch)}</span>${distSegs(w.branch)}` : '';
  const body = w.main && branch ? `<span class="synced wt-lead">${icon('mainWorktree')}</span>${branch}`
    : `${icon(w.main ? 'mainWorktree' : 'worktree')}<span class="badge-name">${esc(w.main ? 'main' : w.name)}</span>`
      + `<span class="div"></span>${branch || icon('detached')}`;
  return `<span class="badge ref-branch" style="--lc:${lc}" data-tip="${esc(tip)}" aria-label="${esc(tip)}">${body}</span>`;
}

const REF_ICON = { head: 'branch', branch: 'branch', remote: 'cloud', tag: 'tag' };   // a leválasztott HEAD ikon nélkül
function badges(c) {
  // A HEAD, az ág és a tag a commit sávjának színét kapja (`--lc`), mint a vonal; a
  // remote chip is: ha van helyi ága, annak a színét (mint az ágválasztóban), különben
  // a pöttyéét, amin áll.
  const lane = laneColor(c.lane);
  const showRemote = remotesOn();
  return sortRefs(mergedRefs(c.refs)).filter(r => showRemote || r.kind !== 'remote').map(r => {
    const wt = r.worktree && worktrees().find(w => w.slug === r.worktree);
    const linked = wt && !wt.main;
    // A fő checkout HEAD-je üres mappát kap elöl, ha vannak worktree-k (mint a fejléc chipje).
    const mainLead = wt?.main && linkedWts().length > 0;
    const dist = r.kind === 'tag' || r.kind === 'detached' ? '' : r.name;   // tagnek, leválasztott HEAD-nek nincs
    // Worktree leválasztott HEAD-je: ág nincs — a worktree jele és neve | lánc (az ág-ikon helyén).
    const orphan = r.kind === 'detached' && (linked || mainLead);
    const title = (orphan ? `${wt.main ? 'main' : wt.name}: leválasztott HEAD (ág nélkül)`
      : (r.kind === 'head' ? 'HEAD → ' : r.kind + ': ') + r.name)
      + (r.remotes.length ? ' = ' + r.remotes.map(o => `${o.name}/${r.name}`).join(', ') : '')
      + (r.default ? '\na remote alapértelmezett ága' : '')
      + (linked ? `\nworktree: ${wt.path}` : '')
      + distText(dist);
    // A remote alapértelmezett ága (`origin/HEAD` célja): teli felhő. Több
    // remote-nál remote-onként egy szakasz a nevével: `main | ☁ origin | ☁ upstream`.
    const cloudOf = on => icon('cloud', on ? 'ic filled' : 'ic');
    const cloud = cloudOf(r.default);
    const multi = (DATA.meta.remotes || []).length > 1;
    // Egy remote-nál a szinkronban lévő ág egyetlen felhő-és-ág ikont kap (lent, `synced`).
    const remotes = multi && showRemote
      ? r.remotes.map(o => `<span class="div"></span><span class="synced">${cloudOf(o.default)}${esc(o.name)}</span>`).join('')
      : '';
    // Worktree-ben kivett ág: elöl a worktree-jel (a fő checkouté csak, ha vannak worktree-k).
    const wtLead = linked || mainLead
      ? `<span class="synced wt-lead">${icon(linked ? 'worktree' : 'mainWorktree')}</span>` : '';
    // Egy remote-nál a helyi ág és a remote párja egy helyen: egyetlen felhő-és-ág ikon
    // (az alapágé teli) a branch-ikon és a felhő helyett, a worktree-jel mögött is.
    const synced = showRemote && r.remotes.length && !multi;
    const other = r.worktree && r.worktree !== focusWt()?.slug ? ' other' : '';
    // A csak remote-os chipen a felhő jelzi a remote-ot: egy remote-nál az
    // `origin/` előtag nem kell, többnél a név mondja meg, melyiké.
    const name = r.kind === 'remote' && !multi ? r.name.replace(/^origin\//, '') : r.name;
    const lead = r.kind === 'remote' ? cloud
      : orphan ? icon(linked ? 'worktree' : 'mainWorktree')
      : wtLead + (synced ? icon(r.default ? 'branchCloudFill' : 'branchCloud')
        : REF_ICON[r.kind] ? icon(REF_ICON[r.kind]) : '');
    // A tooltip a saját buborék (`data-tip`), mint az avataré — a natív `title` késik.
    // A hozzáadott worktree csoportja (HEAD-je, leválasztva az ága) a worktree színét
    // kapja: a csonkjáét, a WIP-soráét, vagy a HEAD-jéét (`wtColor`) — mint a fejléc chipje.
    const group = wtOfRef(r);
    const pair = r.kind === 'remote' && DATA.branches.find(b => !b.remote && b.upstream === r.name);
    const lc = ` style="--lc:${pair ? branchColor(pair) : (group && wtColor(group)) || lane}"`;
    return `<span class="badge ref-${r.kind}${other}"${lc} data-tip="${esc(title)}" aria-label="${esc(title)}">`
      + `${lead}<span class="badge-name">${esc(orphan ? (linked ? wt.name : 'main') : name)}</span>`
      + `${orphan ? `<span class="div"></span>${icon('detached')}` : ''}`
      + `${distSegs(dist)}${remotes}</span>`;
  }).join('');
}

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

function rowHtml(c) {
  const color = fresh.has(c.sha) ? ` style="color:${laneColor(c.lane)}"` : '';
  const st = DATA.stats[c.sha];
  const sum = st ? diffTag(st.files.length, st.add, st.del) : '';   // üres commitnál is: 0 | 0 | 0
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
  const subject = c.subject;
  // A WIP-soron is: a fájlok utolsó módosítása, a gép git-felhasználója, a diff.
  // A saját WIP a rögzített sávban ül, napfejléc nélkül: nem mai időnél a nap is kell.
  const pinned = c.uncommitted && c.worktree === focusWt()?.slug;
  const meta = `<span class="meta"><span class="time">${pinned ? pinnedTime(c.date) : fmtTime(c.date)}</span>`
    + `<span class="author ${av || 'ini'}" data-tip="${esc(c.author)}" aria-label="${esc(c.author)}">`
    + `${av ? '' : esc(initials(c.author))}</span>${sum}</span>`;
  const cls = ['row', c.uncommitted && 'uncommitted', c.parents.length > 1 && 'merge',
    foreign(c) && 'foreign'].filter(Boolean).join(' ');
  return `<button class="${cls}" type="button" data-sha="${c.sha}" aria-expanded="false">
      <span class="row-in"><span class="desc"><span class="subject"${color}>${linkify(subject)}</span>`
    + `${refs ? '<span class="br"></span>' : ''}${refs}</span>${meta}</span>
    </button>`;
}

/* Napi csoportok (`.day-group`): a ragadós fejléc csak a saját napja alatt
   marad fent, a következő nap fejléce kitolja — nem csúsznak egymásra. */
function render() {
  // A kijelölés (fókusz) az újrarajzolás után visszaáll: sor vagy fájl.
  const focused = document.activeElement;
  const keepSha = focused?.closest?.('.row')?.dataset.sha;
  const keepPath = (focused?.closest?.('.file') || focused?.closest?.('.diff')?.previousElementSibling)
    ?.dataset.path;               // blokkon állva a fájljára áll vissza
  let day = '', html = '';
  const today = dayKey(new Date());
  // A saját worktree WIP-je a fix sávban; a többié a listában, a chipjükkel.
  const ownSlug = focusWt()?.slug;
  renderPending(visible.filter(c => c.uncommitted && c.worktree === ownSlug));
  // A többi worktree WIP-je a commitok közé kerül, a fájlok utolsó módosítása
  // szerint — de sosem a saját HEAD-je alá.
  const at = c => {
    const head = commitBySha(c.parents[0]);
    return Math.max(Date.parse(c.date) || 0, head ? Date.parse(head.date) + 1 : 0);
  };
  const others = visible.filter(c => c.uncommitted && c.worktree !== ownSlug).sort((a, b) => at(b) - at(a));
  otherWip = others.length > 0;
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
  fitRows();
  drawGraph();
  const shown = visible.filter(c => !c.uncommitted).length;   // az ál-sor nem commit
  counter.innerHTML = DATA.meta.totalCommits ? `<b>${shown}</b> / ${DATA.meta.totalCommits}` : '';
  counter.title = `${shown} commit látszik, összesen ${DATA.meta.totalCommits}`;
  if (expanded && visible.some(c => c.sha === expanded)) open(expanded); else expanded = null;
  stackDays();
  const back = keepPath && expanded
    ? [...document.querySelectorAll('.details .file')].find(f => f.dataset.path === keepPath)
    : keepSha && document.querySelector(`.row[data-sha="${CSS.escape(keepSha)}"]`);
  back?.focus({ preventScroll: true });
}

/* Az Uncommitted ál-sorok (worktree-nként egy) mindig látszanak: a lista
   fölötti fix sávban, saját üres karikával és a lista felé futó szaggatott
   csonkkal; görgetve a többi worktree-é folytatódik a HEAD-ig. A karikák a sorok mért közepére kerülnek
   (`drawPending`, a `drawGraph` hívja): a sor kétsoros is lehet. */
const pendingEl = document.getElementById('pending');
function renderPending(list) {
  pendingEl.hidden = !list.length;
  pendingEl.innerHTML = list.length
    ? '<svg class="pend-lane" aria-hidden="true"></svg>' + list.map(rowHtml).join('') : '';
}
/* Van-e a listában más worktree WIP-sora (a saját szaggatott vonala ilyenkor átfut rajtuk). */
let otherWip = false;
/* A saját WIP szaggatott vonala görgetve eltűnik, ha nincs alatta más WIP-sor, vagy ha
   a HEAD-je már a lista teteje fölé csúszott (köztük commit van, a vonal nem vezet sehova). */
function hideOwnEdge() {
  const head = focusWt()?.head;
  const row = head && rowsEl.querySelector(`.row[data-sha="${head}"]`);
  const past = row && row.getBoundingClientRect().bottom <= scroller.getBoundingClientRect().top;
  const hide = scroller.scrollTop > 0 && (!otherWip || Boolean(past));
  scroller.classList.toggle('hide-own', hide);
  pendingEl.classList.toggle('hide-own', hide);
}
function drawPending() {
  const lane = pendingEl.querySelector('.pend-lane');
  if (!lane) return;
  // A lista görgetősávja szűkíti a sorokat: a sáv ugyanennyivel beljebb zár, hogy
  // az idő · avatar · diff oszlopban álljon a lista soraival.
  pendingEl.style.paddingRight = `${scroller.offsetWidth - scroller.clientWidth}px`;
  const h = pendingEl.offsetHeight;
  lane.setAttribute('width', graphW);
  lane.setAttribute('height', h);
  lane.innerHTML = [...pendingEl.querySelectorAll('.row')].map(row => {
    const c = commitBySha(row.dataset.sha);
    if (!c) return '';
    const x = laneX(c.lane), y = row.offsetTop + row.offsetHeight / 2;
    const color = tint(c, laneColor(c.lane));
    const own = c.worktree === focusWt()?.slug ? ' own' : '';
    return `<path class="pend-edge${own}" d="M ${x} ${y + DOT_R + 1} L ${x} ${h}" stroke="${color}" stroke-width="2" stroke-dasharray="3 3"/>`
      + `<circle cx="${x}" cy="${y}" r="${DOT_R + 1}" fill="var(--bg)" stroke="${color}" stroke-width="2"/>`;
  }).join('');
}

/* ── Commit-részletek ────────────────────────────────────────────────────── */
const miniBtn =(name, label, attrs = '') =>
  `<button class="mini" type="button" aria-label="${esc(label)}" title="${esc(label)}" ${attrs}>${icon(name)}</button>`;

/* Változásjelölő: 6 szegmens, a hozzáadás / törlés arányában. */
function bars(f) {
  const total = f.add + f.del;
  if (!total) return '';
  const a = Math.round(6 * f.add / total);
  return `<span class="bars" aria-hidden="true">${Array.from({ length: 6 },
    (_, i) => `<i class="${i < a ? 'a' : 'd'}"></i>`).join('')}</span>`;
}

function headHtml(c) {
  if (c.uncommitted) return '';   // a WIP-nek nincs szerzője, dátuma; a szülője a HEAD, a gráf mutatja
  const avatar = avatarOf(c);
  const who = `${avatar ? `<img src="${esc(avatar)}" alt="${esc(c.author)}">` : ''}<span class="name">${esc(c.author)}</span>`
      + `<span class="sep">·</span><span>${fmtDate(c.date)}</span>`;
  const parents = c.parents.map(p => `<button type="button" class="hash" data-jump="${p}" title="Ugrás a szülőre">${p.slice(0, 7)}</button>`
    + miniBtn('open', `Szülő megnyitása: ${p.slice(0, 7)}`, `data-jump="${p}"`)).join('');
  const parentChip = c.parents.length ? `<span class="chip" title="Szülő${c.parents.length > 1 ? 'k' : ''}">`
    + `${icon('parent')}${parents}</span>` : '';
  const commitChip = '<span class="chip">'
    + `<span class="hash plain">${c.short}</span>`
    + (c.pushed ? ghLink(commitUrl(c), icon('open'), 'mini', 'Commit megnyitása a GitHubon') : '')
    + miniBtn('copy', 'Hash másolása', `data-copy="${c.sha}"`) + '</span>';
  return `<div class="d-head"><span class="who">${who}</span><span class="chips">${parentChip}${commitChip}</span></div>`;
}

function open(sha, animate = false) {
  document.querySelectorAll('.details').forEach(d => d.remove());
  const row = document.querySelector(`.row[data-sha="${CSS.escape(sha)}"]`);
  if (!row) return;
  document.querySelectorAll('.row').forEach(r => r.setAttribute('aria-expanded', 'false'));
  row.setAttribute('aria-expanded', 'true');

  const c = commitBySha(sha);
  const st = DATA.stats[sha] || { files: [], add: 0, del: 0 };

  const el = document.createElement('div');
  el.className = 'details';
  el.innerHTML = `
    ${headHtml(c)}
    ${c.body ? `<p class="body-text">${linkify(c.body)}</p>` : ''}
    <div class="files">
      <div class="files-head">Fájlok<span class="n">${st.files.length}</span>
        <span class="a" style="color:var(--add)">+${st.add}</span>
        <span class="d" style="color:var(--del)">−${st.del}</span></div>
      ${st.files.map(f => `<div class="file" tabindex="-1" data-path="${esc(f.path)}" aria-expanded="false">
        <span class="chev">${icon('chev')}</span>${fileIcon(f)}
        <span class="path">${esc(f.path)}</span>
        <span class="churn">${f.new ? '<span class="tag">új</span>' : f.bin ? '<span class="tag">bin</span>'
          : `<span class="a">+${f.add}</span><span class="d">−${f.del}</span>${bars(f)}`}</span>
        ${c.pushed ? ghLink(fileUrl(c, f), icon('open'), 'mini', 'Fájl megnyitása a GitHubon') : '<span></span>'}</div>
        <div class="diff" hidden></div>`).join('')}
    </div>`;
  // Az ál-sor a fix sávban ül: a panelje is ott, a saját sora alatt (több
  // worktree WIP-je közül a megfelelő alatt), korlátozott magasságban.
  row.after(el);
  fitWho();
  expanded = sha;
  // Újrarajzolás (élő adatcsere) után a korábban lenyitott fájlok nyitva maradnak.
  el.querySelectorAll('.file').forEach(f => {
    if (openFiles.has(sha + '\n' + f.dataset.path)) toggleFile(f, sha, true);
  });
  drawGraph();               // a panel alatti sorok lejjebb kerültek
  if (animate) unfold(el);
}

/* Lenyílás: a panel magassága 0-ról nő. A gráf a sorok mért helyéből rajzol,
   ezért az animáció alatt képkockánként újrarajzol (a vonal együtt nyúlik). */
const UNFOLD_MS = 180;
function unfold(el) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const cs = getComputedStyle(el);
  const anim = el.animate([
    { height: '0px', paddingTop: '0px', paddingBottom: '0px', opacity: 0 },
    { height: `${el.offsetHeight}px`, paddingTop: cs.paddingTop, paddingBottom: cs.paddingBottom, opacity: 1 },
  ], { duration: UNFOLD_MS, easing: 'cubic-bezier(.2, .7, .3, 1)' });
  el.style.overflow = 'hidden';
  let frame = requestAnimationFrame(function tick() { drawGraph(); frame = requestAnimationFrame(tick); });
  const done = () => { cancelAnimationFrame(frame); el.style.overflow = ''; drawGraph(); };
  anim.finished.then(done, done);
}

/* A vágólap az Artifact keretében tiltott lehet: akkor a régi `execCommand`. */
async function copyText(text, btn) {
  try { await navigator.clipboard.writeText(text); }
  catch {
    const t = Object.assign(document.createElement('textarea'), { value: text });
    document.body.append(t); t.select();
    try { document.execCommand('copy'); } finally { t.remove(); }
  }
  btn.classList.add('done');
  btn.innerHTML = icon('check');
  setTimeout(() => { btn.classList.remove('done'); btn.innerHTML = icon('copy'); }, 1200);
}

/* ── Fájl-diff ───────────────────────────────────────────────────────────────
   A diffet a lap lustán kéri, fájlonként (a file_diff toollal) —
   a teljes adatban nincs benne. A commitok diffje nem változik, gyorstárazzuk;
   az Uncommitted soré adatcserekor elavul (`stale`): a régi látszik, amíg az
   új meg nem jön, így a 2 mp-es frissítés nem villog. */
const openFiles = new Set();   // sha + '\n' + út
const diffCache = new Map();   // ugyanígy kulcsolva → { data, stale }
let SRC = null;                // az élő adatforrás (startLive állítja); az appon kívül nincs

function toggleFile(fileEl, sha, on) {
  const key = sha + '\n' + fileEl.dataset.path;
  const box = fileEl.nextElementSibling;
  fileEl.setAttribute('aria-expanded', on ? 'true' : 'false');
  box.hidden = !on;
  if (!on) { openFiles.delete(key); drawGraph(); showWholeCommit(fileEl); return; }
  openFiles.add(key);

  const lang = langOf(fileEl.dataset.path);
  const show = html => {
    if (!fileEl.isConnected || fileEl.getAttribute('aria-expanded') !== 'true') return;
    box.innerHTML = html;
    drawGraph();
  };
  const cached = diffCache.get(key);
  if (!SRC) return show('<p class="diff-note">A diff csak élő nézetben látszik '
    + '(az Artifact a Claude appban).</p>');
  show(cached ? diffHtml(cached.data, lang) : '<p class="diff-note loading">Betöltés…</p>');
  if (cached && !cached.stale) return;
  SRC.diff(sha, fileEl.dataset.path).then(
    d => { diffCache.set(key, { data: d }); show(diffHtml(d, lang)); },
    e => { if (!cached) show(`<p class="diff-note">A diff nem tölthető be: ${esc(
      e?.message || e?.code || e)}</p>`); });
}

/* Mindkét nézet elkészül (egymás alatti és side-by-side); hogy melyik látszik,
   azt a `.diff` szélessége dönti el egy container queryvel — átméretezéskor
   újrarenderelés nélkül vált. Ha a diffben csak hozzáadás vagy csak törlés van
   (új fájl, vagy beszúrás / kivágás a változatlan sorok közt), a side-by-side
   egyik oldala végig üres lenne: ott csak az egymás alatti nézet készül.
   Hunkok közt a kihagyott sorok száma a régi oldal sorszámaiból jön. */
function diffHtml(d, lang) {
  if (d.note) return `<p class="diff-note">${esc(d.note)}</p>`;
  if (d.binary) return '<p class="diff-note">Bináris fájl.</p>';
  if (!d.hunks.length) return '<p class="diff-note">Nincs megjeleníthető változás.</p>';
  let uni = '', split = '', oldEnd = 1;
  for (const h of d.hunks) {
    const gap = h.old - oldEnd;
    const gapHtml = gap > 0 ? `<p class="diff-gap" title="${gap} változatlan sor">···</p>` : '';
    // Egy blokk (hunk) a `···`-ig: fókuszálható, a nyilak blokkról blokkra lépnek.
    uni += gapHtml + '<div class="hunk" tabindex="-1">' + h.lines.map(l => `<div class="diff-line mono${KIND[l.t]}">`
      + diffCell(l, l.n, lang) + '</div>').join('') + '</div>';
    split += gapHtml + '<div class="hunk" tabindex="-1">' + splitRows(h, lang) + '</div>';
    oldEnd = h.old + h.lines.filter(l => l.t !== '+').length;
  }
  const kinds = new Set(d.hunks.flatMap(h => h.lines.map(l => l.t)));
  const oneSided = !(kinds.has('+') && kinds.has('-'));   // a változatlan sor nem számít
  return (oneSided ? `<div>${uni}</div>`
    : `<div class="diff-uni">${uni}</div><div class="diff-split">${split}</div>`)
    + (d.truncated ? '<p class="diff-note">… a diff túl hosszú, a vége le van vágva.</p>' : '');
}

const KIND = { ' ': '', '+': ' add', '-': ' del' };
const diffCell = (l, no, lang) => `<span class="no">${no ?? ''}</span>`
  + `<span class="sg">${l.t === ' ' ? '' : l.t === '-' ? '−' : '+'}</span>`
  + `<span class="tx">${highlight(l.s, l.hl, lang)}</span>`;

/* Side-by-side: a változatlan sor mindkét oldalon (balra a régi sorszámmal), a
   törölt blokk és az utána jövő hozzáadott blokk párjai (`p`, a Python
   `pair_lines`-a) egy sorba, a pár nélküliek egyedül, a párok közé —
   ugyanaz a párosítás, amiből a Python a szó-kiemelést számolja. */
function splitRows(h, lang) {
  const L = h.lines, side = (l, no) => l
    ? `<div class="half${KIND[l.t]}">${diffCell(l, no, lang)}</div>` : '<div class="half none"></div>';
  let out = '', old = h.old, i = 0;
  while (i < L.length) {
    if (L[i].t === ' ') {
      out += `<div class="split-row mono">${side(L[i], old)}${side(L[i], L[i].n)}</div>`;
      old++; i++;
      continue;
    }
    let j = i; while (j < L.length && L[j].t === '-') j++;
    let k = j; while (k < L.length && L[k].t === '+') k++;
    const row = (del, add) =>
      out += `<div class="split-row mono">${side(del, del?.n)}${side(add, add?.n)}</div>`;
    let a = j;
    for (let d = i; d < j; d++) {
      if (L[d].p == null) { row(L[d], null); continue; }
      while (a < L[d].p) row(null, L[a++]);
      row(L[d], L[a++]);
    }
    while (a < k) row(null, L[a++]);
    old += j - i; i = k;
  }
  return out;
}

/* ── Szintaxis-színezés ──────────────────────────────────────────────────
   Soronkénti, könnyű tokenizáló a gyakori nyelvcsaládokra: megjegyzés,
   string, kulcsszó, szám, függvényhívás, típus. Többsoros string és
   megjegyzés belseje sima szöveg marad — a diff soronként jön. A szó-kiemelés
   (`hl`, a Python számolja) a tokenek fölött, karakterpontosan fut. */
const KW = {
  py: 'and as assert async await break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return True try while with yield',
  js: 'async await break case catch class const continue default delete do else export extends false finally for from function if import in instanceof let new null of return static super switch this throw true try typeof undefined var void while yield',
  sh: 'case do done elif else esac export fi for function if in local return then until while',
  css: 'important',
};
const LANGS = {
  py: 'py', js: 'js', mjs: 'js', cjs: 'js', ts: 'js', tsx: 'js', jsx: 'js', json: 'json',
  css: 'css', html: 'html', md: 'md', sh: 'sh', bash: 'sh', zsh: 'sh', toml: 'sh', yml: 'sh', yaml: 'sh',
  swift: 'js', go: 'js', rs: 'js', java: 'js', kt: 'js', c: 'js', h: 'js', cpp: 'js',
};
function langOf(path) {
  const name = path.split('/').pop();
  const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : '';
  return LANGS[ext] || (name === 'git-graph' ? 'py' : '');
}
const TOKENIZERS = {};
function tokenizer(lang) {
  if (TOKENIZERS[lang]) return TOKENIZERS[lang];
  const comment = { py: '#.*$', sh: '#.*$', js: '//.*$|/\\*.*?(?:\\*/|$)', css: '/\\*.*?(?:\\*/|$)',
                    html: '<!--.*?(?:-->|$)' }[lang];
  const parts = [
    comment && `(?<cm>${comment})`,
    `(?<st>${lang === 'py' ? '[rbfuRBFU]{0,2}' : ''}"(?:[^"\\\\]|\\\\.)*"?|'(?:[^'\\\\]|\\\\.)*'?${lang === 'js' ? '|`(?:[^`\\\\]|\\\\.)*`?' : ''})`,
    KW[lang] && `(?<kw>\\b(?:${KW[lang].split(' ').join('|')})\\b)`,
    '(?<nu>\\b\\d[\\d_.]*(?:e[+-]?\\d+)?\\b|\\b0x[\\da-f]+\\b)',
    lang === 'css' ? '(?<fn>[\\w-]+(?=\\s*:))' : '(?<fn>\\b[A-Za-z_$][\\w$]*(?=\\s*\\())',
    lang !== 'css' && '(?<ty>\\b[A-Z][A-Za-z0-9_]*[a-z][A-Za-z0-9_]*\\b)',
  ].filter(Boolean);
  TOKENIZERS[lang] = new RegExp(parts.join('|'), lang === 'css' ? 'gi' : 'g');
  return TOKENIZERS[lang];
}
const MD_RE = /(?<kw>^#{1,6} .*$)|(?<st>`[^`]*`)|(?<ty>\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/g;
const HTML_RE = /(?<cm><!--.*?(?:-->|$))|(?<kw><\/?[\w-]+|\/?>)|(?<fn>\s[\w:-]+(?==))|(?<st>"[^"]*"?|'[^']*'?)/g;

function highlight(s, hl, lang) {
  const re = lang === 'md' ? MD_RE : lang === 'html' ? HTML_RE : lang ? tokenizer(lang) : null;
  const cls = new Array(s.length).fill('');
  if (re) {
    re.lastIndex = 0;
    for (const m of s.matchAll(re)) {
      const kind = Object.keys(m.groups).find(k => m.groups[k] !== undefined);
      const start = m.index + (kind === 'fn' && lang === 'html' ? 1 : 0);
      for (let i = start; i < m.index + m[0].length; i++) cls[i] = kind;
    }
  }
  const mark = new Array(s.length).fill(false);
  for (const [a, b] of hl || []) for (let i = a; i < b; i++) mark[i] = true;
  let out = '', i = 0;
  while (i < s.length) {
    let j = i;
    while (j < s.length && cls[j] === cls[i] && mark[j] === mark[i]) j++;
    let seg = esc(s.slice(i, j));
    if (cls[i]) seg = `<span class="s-${cls[i]}">${seg}</span>`;
    if (mark[i]) seg = `<mark>${seg}</mark>`;
    out += seg;
    i = j;
  }
  return out;
}

/* Fájl bezárása után: ha a teljes commit (sor + panel) kifér a képernyőre, de
   nem látszik egészben, a nézet úgy igazodik, hogy az egész látsszon — ne a
   bezárt fájl maradjon a tetején, a commit eleje kicsúszva. */
function showWholeCommit(fileEl) {
  const panel = fileEl.closest('.details');
  if (panel) commitInView(panel, false);
}

/* A kinyitott commit (sor + panel) egészben a nézetbe: ha elfér, úgy görget,
   hogy az egész látsszon; ha nem, `alignTall` esetén a sora kerül a
   napfejléc alá, különben marad, ahogy van. */
function commitInView(panel, alignTall) {
  const row = panel.previousElementSibling?.classList.contains('row') ? panel.previousElementSibling : null;
  const s = scroller.getBoundingClientRect();
  const top = (row || panel).getBoundingClientRect().top, bottom = panel.getBoundingClientRect().bottom;
  if (bottom - top > s.height - STEP_TOP) {
    if (alignTall) scroller.scrollTop -= Math.round(s.top + STEP_TOP - top);
    return;
  }
  if (top < s.top + STEP_TOP) scroller.scrollTop -= Math.round(s.top + STEP_TOP - top);
  else if (bottom > s.bottom) scroller.scrollTop += Math.round(bottom - s.bottom);
}

/* Lefelé haladva (görgetés, nyíl): ha a kinyitott commit sora előbukkan, de a
   panelje a nézet alá lógna, az egész commit kerül a nézetbe. */
function revealExpandedBelow() {
  const panel = rowsEl.querySelector('.details');
  const row = panel?.previousElementSibling;
  if (!row?.classList.contains('row')) return;
  const s = scroller.getBoundingClientRect(), r = row.getBoundingClientRect();
  if (r.top < s.bottom && r.bottom > s.top && panel.getBoundingClientRect().bottom > s.bottom) {
    commitInView(panel, true);
  }
}

/* Az ablak (Artifact-panel) átméretezése sortörést és nézetváltást hozhat: a
   sorok Y-pozíciója elmozdul, a gráfnak követnie kell. */
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
  const el = e.target.closest?.('[data-tip]');
  if (el === tipFor) return;
  hideTip();
  if (!el) return;
  tipFor = el;
  tipTimer = setTimeout(() => showTip(el), TIP_DELAY);
});
document.addEventListener('scroll', hideTip, true);

/* Méretfigyelő: `fn` csak szélességváltozásra fut (a magasság a tördeléstől is
   változik, arra nem kell újramérni), `always` minden változásra. */
function onWidth(el, fn, always) {
  let width = 0;
  new ResizeObserver(() => {
    if (el.clientWidth !== width) { width = el.clientWidth; fn(); }
    always?.();
  }).observe(el);
}
onWidth(rowsEl, () => { fitRows(); fitWho(); }, drawGraph);

/* A kinyitott commit fejében a szerző neve elmarad, ha nem fér ki (nagyon
   hosszú név, keskeny panel): csak az avatar marad, a név tooltipben, és a
   dátum előtti pont sem kell. Avatar nélkül a név marad. */
function fitWho() {
  const who = document.querySelector('.details .who');
  const img = who?.querySelector('img');
  if (!img) return;
  who.classList.remove('face-only');
  img.removeAttribute('data-tip');
  if (who.scrollWidth > who.parentElement.clientWidth) {
    who.classList.add('face-only');
    img.dataset.tip = img.alt;
  }
}

/* A commit-sor elrendezése a szövegoszlop szélességétől (`.row-in`) függ, fix
   határokkal — így egy adott szélességen minden sima sor ugyanúgy néz ki:
     ≥ 480 px  egysoros: tárgy … idő · avatar · diff
     < 480 px  kétsoros (`.two`): fent a tárgy, lent jobbra idő · avatar · diff
   A lista nem szűkül 320 px alá (page.css: `.graph-wrap`). A badge-es sorokat
   mérni kell, mert a badge-ek hossza soronként más: ha a tárgy 260 px alá
   szorulna, vagy a lista kétsoros, kétsorosak (`.tight`: lent balra a badge-ek,
   jobbra a blokk); ha a blokk a badge-ek mellett nem fér el, egészben a
   harmadik sorba kerül (`.three`). Minden lépés előbb mér, aztán ír. */
const ROW_ONE = 480, SQUEEZE = 260;
const squeezed = r => {
  const s = r.querySelector('.subject');
  return s.scrollWidth > s.clientWidth && s.clientWidth < SQUEEZE;
};
function fitRows() {
  const rows = [...rowsEl.querySelectorAll('.row')];
  for (const r of rows) r.classList.remove('two', 'tight', 'three');
  const width = rowsEl.querySelector('.row-in')?.clientWidth ?? 0;
  const one = width >= ROW_ONE;
  const tight = rows.filter(r => r.querySelector('.refs') && (!one || squeezed(r)));
  if (!one) for (const r of rows) if (!r.querySelector('.refs')) r.classList.add('two');
  for (const r of tight) r.classList.add('tight');
  // Ha a badge-ek mellett nem fér el az idő · avatar · diff blokk, a badge-ek
  // tördelődnek (`.three`): a blokk az utolsó sorukba, ha ott sincs hely, alá.
  // Zsúfolt: a badge-ek kilógnak, vagy egy badge neve már rövidülne (`…`) a blokk mellett.
  const crowded = r => {
    const f = r.querySelector('.refs');
    return f.scrollWidth > f.clientWidth
      || [...f.querySelectorAll('.badge-name')].some(n => n.scrollWidth > n.clientWidth + 1);
  };
  for (const r of tight.filter(crowded)) r.classList.replace('tight', 'three');
}

/* Fejléc: három csoport (repó, szűrők, eszközök), szélesség szerint 1–3
   sorban. A kapcsolók felirata helyett ikon (`compact`, a felirat tooltipben
   marad), ha a felirat miatt több sorba törne, vagy a szűrők sorából kilógna.
   Több sorban az ágválasztó tölti ki a szűrők sorát (a kapcsolók így jobbra
   kerülnek), három sorban a HEAD-chip is jobbra zár. A kereső mindig kitölti
   a saját sorát. */
const chromeEl = document.querySelector('.chrome');
const filtersEl = chromeEl.querySelector('.filters');
function chromeRows() {
  let rows = 0, bottom = -Infinity;
  for (const g of chromeEl.children) {
    const r = g.getBoundingClientRect();
    if (r.top >= bottom - 1) { rows++; bottom = r.bottom; } else bottom = Math.max(bottom, r.bottom);
  }
  return rows;
}
function fitChrome() {
  chromeEl.classList.remove('compact', 'multi', 'rows-3');
  const labeled = chromeRows();
  let rows = labeled;
  if (labeled > 1) {
    chromeEl.classList.add('compact');
    rows = chromeRows();
    if (rows > 1 && rows === labeled) {           // így is törne: a felirat maradhat, ha kifér
      chromeEl.classList.remove('compact');
      if (filtersEl.scrollWidth > filtersEl.clientWidth) chromeEl.classList.add('compact');
    }
  }
  chromeEl.classList.toggle('multi', rows > 1);
  chromeEl.classList.toggle('rows-3', rows > 2);
}
onWidth(chromeEl, fitChrome);

function onListClick(e) {
  if (e.target.closest('a[href]')) return;   // GitHub-link: nyíljon, a sor ne csukódjon
  const copy = e.target.closest('[data-copy]');
  if (copy) { copyText(copy.dataset.copy, copy); return; }
  const jump = e.target.closest('[data-jump]');
  if (jump) {
    const target = rowsEl.querySelector(`.row[data-sha="${jump.dataset.jump}"]`);
    if (target) { open(jump.dataset.jump); target.scrollIntoView({ block: 'center' }); }
    return;
  }
  const file = e.target.closest('.file');
  if (file) { toggleFile(file, expanded, file.getAttribute('aria-expanded') !== 'true'); return; }
  if (e.target.closest('.details')) return;   // a panelben kattintás ne csukja be
  const row = e.target.closest('.row');
  if (!row) return;
  if (row.getAttribute('aria-expanded') === 'true') {
    row.setAttribute('aria-expanded', 'false');
    document.querySelectorAll('.details').forEach(d => d.remove());
    expanded = null;
    drawGraph();
  } else open(row.dataset.sha, true);
}
rowsEl.addEventListener('click', onListClick);
pendingEl.addEventListener('click', onListClick);

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && expanded && !menuOpen()) closeCommit();
});

/* ── Szűrők ──────────────────────────────────────────────────────────────── */
/* Ágválasztó: saját listbox-menü. A kijelölés ref-nevek halmaza (helyi ág,
   upstream, csak remote ág); üres = minden ág. */
const branchBtn = document.getElementById('branchBtn');
const branchPop = document.getElementById('branchPop');
const branchAll = document.getElementById('branchAll');
const branchList = document.getElementById('branchList');
const branchQuery = document.getElementById('branchQuery');
const branchLabel = document.getElementById('branchLabel');
const branchIc = document.getElementById('branchIc');
let branchSel = new Set();

/* Remote ref-e a név: valamelyik helyi ág upstreamje, vagy csak remote ág. */
const remoteRefs = () => new Set(DATA.branches.flatMap(b => b.remote ? [b.name] : b.upstream ? [b.upstream] : []));
/* Az ágválasztó színes ikonjai. Egy ág színe: ha egy worktree-ben ki van véve
   (vagy leválasztott HEAD-del az app szerint az övé), a worktree színe, mint a
   chipjén; különben a csúcsa sávjáé. Az upstream felhője a helyi ágáé; teli csak
   az alapágé (default ág csak remote-on van). */
const tinted = (name, color) => `<svg class="ic" style="color:${color}" viewBox="0 0 16 16" aria-hidden="true">${ICONS[name]}</svg>`;
function branchColor(b) {
  const w = worktrees().find(x => (b.worktree && x.slug === b.worktree) || (!x.branch && x.appBranch === b.name));
  return (w && wtColor(w)) || refColor(b.name);
}
const cloudIc = (ref, color) => tinted(ref === DATA.meta.base ? 'cloudFill' : 'cloud', color);
/* Ág és upstream együtt (egy helyen állnak, vagy mindkettő kijelölve): egy ikon. */
const branchCloudIc = (ref, color) => tinted(ref === DATA.meta.base ? 'branchCloudFill' : 'branchCloud', color);
/* Egy helyi ág refjei a menüben: maga, és — remote ágakkal — az élő upstreamje. */
const blockRefs = (b, remote) => (remote && b.upstream && b.track !== 'gone' ? [b.name, b.upstream] : [b.name]);
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
function fillBranches() {
  const remote = remotesOn();
  const valid = new Set([...DATA.branches.map(b => b.name), ...(remote ? remoteRefs() : [])]);
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
  /* Egy sor: pipa (külön kattintható), egy ikon (ág, felhő, vagy a kettő együtt), név, és jobbra két
     távolság-oszlop. A szélső (`c1`): az egysoros blokk távolsága, a két soros blokkban
     a ↕ jel helye; előtte (`c2`) a két soros blokk soronkénti távolsága. Egy cella: a
     nyíl elöl, a szám a cella végén — így a nyilak és a számvégek egy vonalban. */
  const line = (refs, ic, name, c2, c1) => {
    const on = refs.every(r => branchSel.has(r));
    return `<span class="ln${on ? ' on' : ''}"><span class="ckc" data-refs="${esc(refs.join(' '))}"`
      + ` title="${on ? 'kivesz' : 'hozzáad'}">${icon('check', 'ic ck')}</span>`
      + `<span class="col">${ic}</span>`
      + `<span class="name">${name}</span><span class="c2">${c2}</span><span class="c1">${c1}</span></span>`;
  };
  // Az alapághoz mért távolság egy cellában (a távolság-szöveg a tooltipben).
  const cell = name => {
    const [a, d] = DATA.meta.tracks?.[name]?.base || [0, 0];
    if (!a && !d) return '';
    const tip = esc(distText(name).trim());
    return a && d ? `<span class="dc" title="${tip}">↑${a} ↓${d}</span>`
      : `<span class="dc" title="${tip}"><span>${a ? '↑' : '↓'}</span><span>${a || d}</span></span>`;
  };
  // A helyi ág és az upstreamje közti távolság (`↕`): a két sor közé, jobbra. Az
  // alapág helyi párjának előnye anomália (piros), mint a chipeken.
  const pairGap = b => {
    const [a, d] = DATA.meta.tracks?.[b.name]?.up || [0, 0];
    const odd = b.name === baseLocal && a > 0;
    const tip = [a && `↑${a}: a helyi ${b.name} ennyivel jár előrébb`, d && `↓${d}: a ${b.upstream} ennyivel jár előrébb`]
      .filter(Boolean).join('\n');
    // A jel a többi távolság ↑ és ↓ karaktere egymás fölött: a nyílhegyük ugyanaz.
    return `<span class="dc gap${odd ? ' warn' : ''}" title="${esc(tip)}"><span class="ud" aria-hidden="true">`
      + `<span>↑</span><span>↓</span></span><span>${a && d ? `${a}/${d}` : a || d}</span></span>`;
  };
  const block = b => {
    const det = detachedOf(b.name);
    const name = (det ? `<i>${esc(b.name)}</i>` : esc(b.name))
      + (isHead(b) ? `<span class="cur" style="--lc:${branchColor(b)}">HEAD</span>` : '');
    const refs = blockRefs(b, remote), up = refs[1];
    const pair = up && !synced(b);
    // A leválasztott HEAD jele a szélen, a worktree-fejléc WIP-karikájának oszlopában.
    const end = det ? `<span class="det" title="leválasztott HEAD — az ágát a Claude app jegyzi">${icon('detached')}</span>`
      : cell(b.name);
    const c = branchColor(b);
    // Két sornál a soronkénti távolság a belső oszlopban, a szélen a kettejük közti ↕.
    const lines = !pair
      ? line(refs, up ? branchCloudIc(up, c) : tinted('branch', c), name, '', end)
      : line([b.name], tinted('branch', c), name, end, '')
        + line([up], cloudIc(up, c), esc(up), cell(up), '') + pairGap(b);
    return blockBtn(refs, lines);
  };
  const blockBtn = (refs, lines) => `<button type="button" class="option blk" role="option" data-refs="${esc(refs.join(' '))}"`
    + ` data-key="${esc(refs[0])}" aria-selected="${refs.every(r => branchSel.has(r))}">${lines}</button>`;
  const header = w => {
    const lc = wtColor(w) || 'var(--accent)';
    const ic = tinted(w.main ? 'mainWorktree' : 'worktree', lc);   // a worktree színe, mint a chipjén
    const name = esc(w.main ? 'main' : w.name);
    const wip = w.dirty ? `<span class="wip" style="color:${lc}" title="nem commitolt változás"></span>` : '';
    const cur = w.slug === own?.slug;
    const body = `${ic}<span class="name${cur ? ' menu-wt-cur" title="itt dolgozik az előtérben lévő session' : ''}">${name}</span>${wip}`;
    const refs = ownedBy(w).flatMap(b => blockRefs(b, remote));
    return refs.length
      ? `<button type="button" class="option menu-wt" role="option" data-refs="${esc(refs.join(' '))}" data-key="wt:${esc(w.slug)}"`
        + ` aria-selected="${refs.every(r => branchSel.has(r))}" title="a worktree összes ága">${body}</button>`
      : `<div class="menu-wt">${body}</div>`;
  };
  /* Egy csoport: fejléc (worktree, remote; a szűrő a nevét is nézi) és az ágai. A `sep`
     csoport fölött vonal, ha előtte látszik egy csoport (CSS). */
  const group = (name, inner, sep) => `<div class="menu-grp${sep ? ' sep' : ''}" data-name="${esc(name)}">${inner}</div>`;
  branchAll.innerHTML = `<button type="button" class="option blk" role="option" data-refs="" data-key="" aria-selected="${!branchSel.size}">`
    + `<span class="ln${branchSel.size ? '' : ' on'}"><span class="ckc">${icon('check', 'ic ck')}</span>`
    + `<span class="col">${icon('allBranches')}</span><span class="name">Minden ág</span></span></button>`;
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
  if (remote) for (const b of DATA.branches.filter(x => x.remote)) {
    const r = b.name.slice(0, b.name.indexOf('/'));
    byRemote.set(r, [...(byRemote.get(r) || []), b]);
  }
  for (const [r, list] of byRemote) {
    html += group(r, `<div class="menu-wt">${icon('cloud')}<span>${esc(r)}</span><span class="note">· csak remote</span></div>`
      + list.map(b => blockBtn([b.name], line([b.name], cloudIc(b.name, refColor(b.name)), esc(b.name.slice(r.length + 1)), '', cell(b.name)))).join(''), true);
  }
  branchList.innerHTML = html;
  filterBranches();
  // A két távolság-oszlop szélessége külön-külön a saját leghosszabb számához igazodik
  // (1–4 jegy); a ↕ jel a szélső oszlophoz tartozik.
  const longest = sel => Math.max(1, ...[...branchPop.querySelectorAll(sel)].map(e => e.textContent.length));
  branchPop.style.setProperty('--c1-digits', longest('.c1 .dc > :last-child, .gap > :last-child'));
  branchPop.style.setProperty('--c2-digits', longest('.c2 .dc > :last-child'));
  const [ics, label] = selView();
  if (branchIc.innerHTML !== ics) branchIc.innerHTML = ics;
  if (branchLabel.textContent !== label) {
    branchLabel.textContent = label;
    fitChrome();                // a hosszabb ágnév más sorbontást hozhat
  }
}

/* Az ágválasztó szűrője: minden szó (kis-nagybetű és ékezet nélkül) szerepeljen a
   blokk refjeiben vagy a csoportja nevében (worktree, remote) — a worktree nevére
   szűrve az összes ága látszik. A csoport (a fejlécével) csak akkor marad, ha legalább
   egy ága látszik; a „Minden ág” szűrés közben rejtve. */
function filterBranches() {
  const words = queryWords(branchQuery.value);
  branchAll.hidden = words.length > 0;
  let any = false;
  for (const grp of branchList.children) {
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

/* Közös legördülő menü (ágválasztó, téma): nyíl-, Home/End-, Escape- és
   Tab-billentyű, kattintás kívülre csuk. `onPick` a választott opciót kapja. */
function makeMenu(btn, pop, onPick, onOpen) {
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
    toggle(false);
    btn.focus();
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

makeMenu(branchBtn, branchPop, o => {
  branchSel = new Set(o.dataset.refs.split(' ').filter(Boolean));
  fillBranches();
  applyFilters();
}, () => {
  // Üres szűrővel nyílik; a teljes lista szélessége marad, szűréskor nem ugrik össze.
  branchQuery.value = '';
  filterBranches();
  branchPop.style.minWidth = '';      // a természetes szélesség méréséhez
  branchPop.style.minWidth = `${branchPop.offsetWidth}px`;
  branchQuery.focus();
});
/* A pipára kattintás csak azt a sort veszi ki vagy teszi be, a menü nyitva marad
   (a makeMenu kattintás-kezelője elé, rögzítő fázisban). */
branchPop.addEventListener('click', e => {
  const c = e.target.closest('.ckc[data-refs]');
  if (!c) return;
  e.stopPropagation();
  const refs = c.dataset.refs.split(' ');
  const on = refs.every(r => branchSel.has(r));
  for (const r of refs) on ? branchSel.delete(r) : branchSel.add(r);
  const key = c.closest('.option')?.dataset.key;
  fillBranches();
  applyFilters();
  branchPop.querySelector(`.option[data-key="${CSS.escape(key || '')}"]`)?.focus();
}, true);

/* A kijelölt refek őseinek uniója (null, ha egyik csúcsa sincs a listában). */
function ancestryOf(names) {
  const tips = DATA.commits.filter(c => c.refs.some(r => names.has(r.name) && r.kind !== 'tag'));
  return tips.length ? reachable(tips.map(c => c.sha)) : null;
}
/* A remote ágak nélkül: ami helyi ágból, HEAD-ből, tagből vagy WIP-ből elérhető. */
const localReach = () => reachable(DATA.commits.filter(c => c.uncommitted
  || c.refs.some(r => r.kind !== 'remote')).map(c => c.uncommitted ? c.parents[0] : c.sha));
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

/* Keresés: minden szó (szóközzel elválasztva) szerepeljen a commit
   üzenetében, törzsében, szerzőjében, e-mail-címében, ref-neveiben — vagy a
   hash eleje legyen. Kis- és nagybetű, ékezet nem számít. */
const searchEl = document.getElementById('search');
const fold = s => String(s).toLowerCase().normalize('NFD').replace(/\p{M}/gu, '');
const queryWords = s => fold(s).split(/\s+/).filter(Boolean);
function matches(c, words) {
  if (!words.length) return true;
  const hay = fold([c.subject, c.body, c.author, c.email, ...c.refs.map(r => r.name)].join('\n'));
  return words.every(w => hay.includes(w) || c.sha.startsWith(w));
}

function applyFilters() {
  const branch = branchSel.size ? branchSel : null;
  const remotes = remotesOn();
  const refsOnly = document.getElementById('onlyRefs').checked;
  const words = queryWords(searchEl.value);
  const keep = branch ? ancestryOf(branch) : null;
  const local = remotes ? null : localReach();

  visible = DATA.commits.filter(c => {
    // Állapot, nem commit: keresésnél nem kell; ágszűrésnél csak annak a worktree-nek
    // a WIP-je, amelyikben a szűrt ág van kivéve (nem elég, hogy a HEAD-je rajta van).
    if (c.uncommitted) {
      return !words.length && (!branch || worktrees().some(w => w.slug === c.worktree && branch.has(w.branch)));
    }
    if (keep && !keep.has(c.sha)) return false;
    // Remote ágak nélkül a helyi történet minden commitja marad (csak a remote-badge
    // tűnik el); ami csak remote ágból érhető el, az kimarad.
    if (local && !local.has(c.sha)) return false;
    if (refsOnly && !c.refs.some(r => remotes || r.kind !== 'remote')) return false;
    return matches(c, words);
  });
  render();
}
document.getElementById('onlyRefs').addEventListener('change', applyFilters);
// A remote-kapcsoló a fejléc chipjét is érinti (a ☁ szakasz).
document.getElementById('showRemotes').addEventListener('change', () => {
  // Remote ágak nélkül a kijelölt remote refek is kiesnek (üresen: minden ág).
  if (!remotesOn()) for (const r of remoteRefs()) branchSel.delete(r);
  hydrateFocus(); fillBranches(); applyFilters();
});
/* A keresés törlésekor (Escape, a mező ×-e vagy kitörölt szöveg) a szűrés
   megszűnik; ha van kinyitott commit, az a lista tetejére kerül (a napfejléc
   alá), hogy a visszajött sorok közt se vesszen el. */
let lastQuery = '';
function revealExpanded() {
  const row = expanded && rowsEl.querySelector(`.row[data-sha="${CSS.escape(expanded)}"]`);
  if (!row) return;
  const top = row.getBoundingClientRect().top - scroller.getBoundingClientRect().top + scroller.scrollTop;
  scroller.scrollTop = Math.max(0, Math.round(top - STEP_TOP));
}
searchEl.addEventListener('input', () => {
  const cleared = lastQuery && !searchEl.value;
  lastQuery = searchEl.value;
  applyFilters();
  if (cleared) revealExpanded();
});

/* ⌘F / Ctrl+F a keresőbe (a lap saját keresője helyett); Escape előbb a
   keresést üríti, aztán a kinyitott commitot csukja be. */
document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'f') {
    e.preventDefault();
    searchEl.focus();
    searchEl.select();
  } else if (e.key === 'Escape' && searchEl.value
             && !menuOpen()) {   // nyitott menüt a menü csuk
    e.stopImmediatePropagation();
    e.preventDefault();
    searchEl.value = '';
    lastQuery = '';
    applyFilters();
    revealExpanded();
  }
}, true);

/* ── Billentyűzetes navigáció ─────────────────────────────────────────────
   A kijelölés a billentyűzet-fókusz (sor- és fájl-elem), így az élő
   adatcsere után is visszaáll (`render`).
   Commit-szint:  ↑/↓ kijelölés (nem nyit), → kinyit és belép a fájlokba,
                  ← / Esc becsuk; ⌘/Ctrl+↓/↑ szülő / gyerek ugyanazon az ágon,
                  Shift-tel merge-nél a másik ág; H a HEAD (a ⌘H az appot rejti)
   Fájl-szint:    ↑/↓ a fájlokon, → kinyitja a diffet, ← becsukja; bezárt
                  fájlon ← vissza a commitra.
   Beviteli mezőben és nyitott menünél a billentyűk a saját dolgukat végzik. */
const rowOf = c => c && document.querySelector(`.row[data-sha="${CSS.escape(c.sha)}"]`);
/* Egy nyitott fájl blokkjai — csak a látható nézetéé (egymás alatti vagy
   side-by-side, a szélesség dönt). Bezárt fájlnál üres. */
const hunksOf = fileEl => fileEl?.getAttribute('aria-expanded') === 'true'
  ? [...fileEl.nextElementSibling.querySelectorAll('.hunk')].filter(h => h.offsetParent !== null) : [];
/* Fájl kinyitása után a kijelölés az első blokkra lép — ha a diff még
   töltődik, megvárja (legfeljebb 3 mp), amíg megjelenik. Ha közben máshová
   lépett a kijelölés, nem rántja vissza. */
function enterFirstHunk(fileEl) {
  const go = () => {
    const first = hunksOf(fileEl)[0];
    if (first && document.activeElement === fileEl) select(first);
    // kész: van blokk, vagy végleges üzenet jött (bináris, üres, hiba) — a betöltésre vár
    return Boolean(first) || fileEl.nextElementSibling.querySelector('.diff-note:not(.loading)') !== null;
  };
  if (go()) return;
  const box = fileEl.nextElementSibling;
  const obs = new MutationObserver(() => { if (go()) obs.disconnect(); });
  obs.observe(box, { childList: true, subtree: true });
  setTimeout(() => obs.disconnect(), 3000);
}
/* A nyitott commit alatti commit sora — az utolsó fájlról / blokkról lefelé ide lép. */
const belowCommit = () => {
  const i = visible.findIndex(c => c.sha === expanded);
  return i < 0 ? null : rowOf(visible[i + 1]);
};
const nextFile = fileEl => {
  const files = [...fileEl.parentElement.querySelectorAll('.file')];
  return files[files.indexOf(fileEl) + 1];
};
const commitOf = el => el && visible.find(c => c.sha === el.dataset.sha);

/* A kijelölt elem látszódjon: a ragadós napfejléc alá, vagy az alsó szélhez. */
function ensureVisible(el) {
  if (!scroller.contains(el)) return;                    // a fix #pending sor
  const s = scroller.getBoundingClientRect(), r = el.getBoundingClientRect();
  // Ami nem fér ki (magas blokk), annak a teteje igazodik a fejléc alá.
  if (r.top < s.top + STEP_TOP || r.height > s.height - STEP_TOP) {
    scroller.scrollTop -= Math.round(s.top + STEP_TOP - r.top);
  }
  else if (r.bottom > s.bottom) scroller.scrollTop += Math.round(r.bottom - s.bottom);
}
function select(el) {
  if (!el) return false;
  el.focus({ preventScroll: true });
  ensureVisible(el);
  // A kinyitott commit sorára lépve: ha a panelje a nézet alá lóg, az egész commit a nézetbe.
  if (el.getAttribute('aria-expanded') === 'true') revealExpandedBelow();
  return true;
}
function selectCommit(c) {
  return Boolean(c && visible.includes(c)) && select(rowOf(c));   // szűrve: nem látszik
}
function closeCommit() {
  const row = expanded && rowOf(visible.find(c => c.sha === expanded));
  document.querySelectorAll('.details').forEach(d => d.remove());
  document.querySelectorAll('.row').forEach(r => r.setAttribute('aria-expanded', 'false'));
  expanded = null;
  drawGraph();
  if (row) select(row);
}
function topVisible() {
  // Görgetés nélkül a legfelső sor 4 px-re van (nincs fölötte ragadós fejléc).
  const top = scroller.getBoundingClientRect().top + (scroller.scrollTop > 0 ? STEP_TOP : 0) - 1;
  const row = [...rowsEl.querySelectorAll('.row')].find(r => r.getBoundingClientRect().top >= top);
  return row && visible.find(c => c.sha === row.dataset.sha);
}
function relative(c, dir, other) {
  if (dir > 0) {                                    // lefelé: szülő
    const p = other ? c.parents[1] : c.parents[0];
    return p && commitBySha(p);
  }
  return DATA.commits.find(x => other ? x.parents.slice(1).includes(c.sha) : x.parents[0] === c.sha);
}
document.addEventListener('keydown', e => {
  if (e.altKey || e.target.closest('input, textarea, .menu-pop')
      || menuOpen()) return;
  const active = document.activeElement;
  const hunk = active?.closest?.('.hunk');
  const file = !hunk && active?.closest?.('.file');
  const row = !hunk && !file && active?.closest?.('.row');
  const cur = commitOf(row);
  const k = e.key, mod = e.metaKey || e.ctrlKey;
  let handled = true;

  if (e.shiftKey && !mod && (k === 'ArrowDown' || k === 'ArrowUp')) {   // ── csak görget, a kijelölés marad
    scroller.scrollTop += (k === 'ArrowDown' ? 1 : -1) * SHIFT_SCROLL;
  } else if (hunk) {                                     // ── blokk-szint (nyitott diff)
    const fileEl = hunk.closest('.diff').previousElementSibling;
    const blocks = hunksOf(fileEl), i = blocks.indexOf(hunk);
    if (k === 'ArrowDown' || k === 'ArrowRight') select(blocks[i + 1] || nextFile(fileEl));   // az utolsó fájl utolsó blokkján marad
    else if (k === 'ArrowUp') select(blocks[i - 1] || fileEl);
    else if (k === 'ArrowLeft') { toggleFile(fileEl, expanded, false); select(fileEl); }   // bezárja a fájlt
    else handled = false;
  } else if (file) {                                     // ── fájl-szint
    const files = [...file.parentElement.querySelectorAll('.file')];
    const isOpen = file.getAttribute('aria-expanded') === 'true';
    const prev = files[files.indexOf(file) - 1];
    if (k === 'ArrowDown') select((isOpen && hunksOf(file)[0]) || nextFile(file) || belowCommit());
    else if (k === 'ArrowUp') select((prev && hunksOf(prev).at(-1)) || prev || rowOf(visible.find(c => c.sha === expanded)));
    else if (k === 'ArrowRight' && !isOpen) { toggleFile(file, expanded, true); enterFirstHunk(file); }
    else if (k === 'ArrowRight') enterFirstHunk(file);          // már nyitva: az első blokkra
    else if (k === 'ArrowLeft' && isOpen) toggleFile(file, expanded, false);
    else if (k === 'ArrowLeft') select(rowOf(visible.find(c => c.sha === expanded)));
    else handled = false;
  } else if ((k === 'ArrowDown' || k === 'ArrowUp') && mod) {   // ── ág mentén
    handled = Boolean(cur) && (selectCommit(relative(cur, k === 'ArrowDown' ? 1 : -1, e.shiftKey)) || true);
  } else if ((k === 'ArrowDown' || k === 'ArrowUp') && !e.shiftKey) {
    handled = cur ? (selectCommit(visible[visible.indexOf(cur) + (k === 'ArrowDown' ? 1 : -1)]) || true)
                  : selectCommit(topVisible());
  } else if (k === 'ArrowRight' && cur) {                 // belép: kinyit, első fájl
    if (expanded !== cur.sha) open(cur.sha, true);
    const first = document.querySelector('.details .file');
    if (first) select(first); else select(rowOf(cur));
  } else if (k === 'ArrowLeft' && cur && expanded === cur.sha) {
    closeCommit();
  } else if ((k === 'h' || k === 'H') && !mod) {
    const isHead = r => r.kind === 'head' || r.kind === 'detached';
    const own = focusWt()?.slug;
    handled = selectCommit(visible.find(c => c.refs.some(r => isHead(r) && r.worktree === own))
      || visible.find(c => c.refs.some(isHead)));
  } else {
    handled = false;
  }
  if (handled) e.preventDefault();
});

/* ── Téma ── automatikus / világos / sötét, lenyíló menüből; a választás
   nézőnként megmarad (a betöltő is ebből indul, hogy ne villanjon). */
const THEME_KEY = 'git-graph:theme';
const THEMES = [
  ['auto', 'Automatikus', '<circle cx="8" cy="8" r="5.5"/><path d="M8 2.5a5.5 5.5 0 0 1 0 11z" fill="currentColor"/>'],
  ['light', 'Világos', '<circle cx="8" cy="8" r="2.75"/><path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1"/>'],
  ['dark', 'Sötét', '<path d="M13 9.5A5.5 5.5 0 0 1 6.5 3a5.5 5.5 0 1 0 6.5 6.5z"/>'],
];
const themeBtn = document.getElementById('themeBtn');
const themePop = document.getElementById('themePop');
/* A platform a Claude app választott témáját `data-theme`-mel adja (a
   „Rendszer” beállításnál semmit). Az „Automatikus” ezt követi, nem törli:
   a betöltő induláskor feljegyzi (`hostTheme`), menet közbeni váltását a
   figyelő veszi észre — ami nem a mi írásunk, az a platformé. */
const root = document.documentElement;
let themeMode = 'auto';
let hostTheme = root.dataset.hostTheme ?? root.getAttribute('data-theme') ?? '';
let ownTheme = root.getAttribute('data-theme');
function applyTheme() {
  ownTheme = themeMode === 'auto' ? hostTheme || null : themeMode;
  if (root.getAttribute('data-theme') === ownTheme) return;
  if (ownTheme) root.setAttribute('data-theme', ownTheme); else root.removeAttribute('data-theme');
}
new MutationObserver(() => {
  const value = root.getAttribute('data-theme');
  if (value === ownTheme) return;
  hostTheme = value || '';
  applyTheme();
}).observe(root, { attributes: true, attributeFilter: ['data-theme'] });
function setTheme(mode) {
  themeMode = mode;
  applyTheme();
  const [, label, svgPath] = THEMES.find(t => t[0] === mode) || THEMES[0];
  document.getElementById('themeIcon').innerHTML = svgPath;
  themeBtn.setAttribute('aria-label', `Téma: ${label.toLowerCase()}`);
  themeBtn.title = `Téma: ${label.toLowerCase()}`;
  themePop.innerHTML = THEMES.map(([value, name, path]) =>
    `<button type="button" class="option with-icon" role="option" data-value="${value}" aria-selected="${value === mode}">`
    + `<svg class="ic" viewBox="0 0 16 16" aria-hidden="true">${path}</svg>`
    + `<span class="name">${name}</span>${icon('check', 'ic ck')}</button>`).join('');
  try { localStorage.setItem(THEME_KEY, mode); } catch { /* privát ablak: nem baj */ }
}
makeMenu(themeBtn, themePop, o => setTheme(o.dataset.value));
setTheme((() => { try { return localStorage.getItem(THEME_KEY) || 'auto'; } catch { return 'auto'; } })());

hydrate();
fillBranches();
render();

/* ── Élő frissítés ───────────────────────────────────────────────────────
   A forrás a gépen futó `git-graph --mcp` (a Claude app host-hídján át). Az olcsó
   ujjlenyomatot pollozzuk, teljes adatot csak tényleges változásra kérünk: a
   lap helyben rajzol újra, a nyitott panel, a szűrők és a görgetés megmaradnak.
   A mért időket a lábléc élő-felirata tooltipben mutatja. */
const POLL_MS = 2000;
const SETTLE_MS = 250;      // méretváltás (session-váltás) után ennyit vár a kérdezéssel
const RETRY_MS = 400;       // átmeneti hiba után ennyi idővel csendben újra
const QUIET_RETRIES = 3;    // ennyi átmeneti hibát nem ír ki
const ARRIVAL_MS = 2000;    // ennyin belül a fókuszváltás az utolsó jelé (a tooltipben)
const FOCUS_WAIT_S = 50;    // a nyitva tartott hívás leghosszabb várakozása
const foot = document.getElementById('foot');
const liveText = document.getElementById('liveText');
const liveDot = document.getElementById('liveDot');
const versionEl = document.getElementById('version');
/* A felül ragadó nap fejléce egyben tűnik el, amikor az alja eléri a
   következő nap fejlécét — nem csúszik ki fokozatosan, nem lóg rá a másikra. */
function stackDays() {
  scroller.classList.toggle('scrolled', scroller.scrollTop > 0);
  pendingEl.classList.toggle('scrolled', scroller.scrollTop > 0);
  hideOwnEdge();
  const days = [...rowsEl.querySelectorAll('.day')];
  const top = scroller.getBoundingClientRect().top, scrolled = scroller.scrollTop > 0;
  // Előbb minden mérés, aztán az írás: a görgetés minden képkockáján fut, a
  // váltakozó olvasás-írás napfejlécenként újratördelést kényszerítene.
  const ys = days.map(d => d.getBoundingClientRect().top), hs = days.map(d => d.offsetHeight);
  // A napfejléc mellett: a nap hány sora van a fejléc fölött (`↑`, alá csúszva) és
  // alatta (`↓`) — a kettő összege mindig a nap összes sora. Csak a nézetbe érő
  // napokat méri; a többinél minden sor a fejléc alatt van.
  const bottom = scroller.getBoundingClientRect().bottom;
  const counts = days.map((d, i) => {
    const rows = d.parentElement.getElementsByClassName('row');   // élő gyűjtemény: olcsó
    let up = 0;
    const group = d.parentElement.getBoundingClientRect();
    if (group.bottom > top && group.top < bottom) {
      const line = ys[i] + hs[i];
      for (const r of rows) if (r.getBoundingClientRect().top < line - 0.5) up++;
    }
    const down = rows.length - up;
    return [up && `↑${up}`, down && `↓${down}`].filter(Boolean).join(' ');
  });
  days.forEach((d, i) => {
    d.classList.toggle('gone', i + 1 < days.length && ys[i + 1] - ys[i] <= hs[i] + 0.5);
    // Felül ragadva (`.stuck`) a vonal nem kell, csak a felirat.
    d.classList.toggle('stuck', scrolled && ys[i] - top <= 0.5);
    const cnt = d.querySelector('.cnt'), text = counts[i] ? ` · ${counts[i]}` : '';
    if (cnt && cnt.textContent !== text) cnt.textContent = text;
  });
}
scroller.addEventListener('scroll', stackDays, { passive: true });

/* Commitonként görgetés: egy görgő-kattanás egy commit, trackpaden ~40 px
   egy commit. A sor a ragadós napfejléc alá (`STEP_TOP`) igazodik, így a fejléc
   sosem takarja. A CSS scroll-snap ezt nem tartja (a böngésző egy
   kattanással több sort is átugrik). Ha egy kinyitott commit-panel látszik,
   azon belül szabad a görgetés — a következő lépés újra sorhoz igazít. */
const STEP_TOP = 16, TRACKPAD_STEP = 40, NOTCH = 50;
const SHIFT_SCROLL = 54;   // Shift+↑/↓: három diff-sornyit görget (a kijelölés marad)
// Ennyi időn belül egy irány nem növekvő eseményei lecsengésnek számítanak.
const COAST_MS = 120;
let wheelAcc = 0, stepDir = 0;
const lastMag = { 1: 0, '-1': 0 }, lastAt = { 1: -1e9, '-1': -1e9 };
/* Egy lépés: azonnal, animáció nélkül (az animáció — a böngészőé és a saját
   ease-out is — darabosnak, irányváltáskor késlekedőnek tűnt). */
function stepRows(dir) {
  const base = scroller.getBoundingClientRect().top - scroller.scrollTop;
  const tops = [...rowsEl.querySelectorAll('.row')]
    .map(r => Math.max(0, Math.round(r.getBoundingClientRect().top - base - STEP_TOP)));
  stepDir = dir;
  const from = scroller.scrollTop;
  const max = scroller.scrollHeight - scroller.clientHeight;
  const target = dir > 0 ? (tops.find(t => t > from + 1) ?? max)
                         : ([...tops].reverse().find(t => t < from - 1) ?? 0);
  scroller.scrollTop = Math.min(target, max);
  if (dir > 0) revealExpandedBelow();
}
scroller.addEventListener('wheel', e => {
  if (e.ctrlKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
  const panel = rowsEl.querySelector('.details');
  if (panel) {
    const r = panel.getBoundingClientRect(), s = scroller.getBoundingClientRect();
    if (r.top < s.bottom && r.bottom > s.top + STEP_TOP + 1) return;
  }
  e.preventDefault();
  const px = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaMode === 2 ? e.deltaY * scroller.clientHeight : e.deltaY;
  if (!px) return;
  const sgn = Math.sign(px), mag = Math.abs(px), now = performance.now();
  // Lecsengés: ugyanabban az irányban, rövid időn belül, nem növekvő nagyságú
  // esemény — a simító egérszoftver (BetterMouse) lendülete. Fordulás után ez a
  // régi irányból még az új irány eseményei KÖZÉ is beérkezhet.
  const coasting = now - lastAt[sgn] < COAST_MS && mag <= lastMag[sgn] * 1.15;
  lastMag[sgn] = mag;
  lastAt[sgn] = now;
  if (stepDir && sgn !== stepDir) {
    if (coasting) return;                 // a régi irány lendülete: nem fordít vissza
    // Valódi fordulás: azonnal lép (az új irány első eseményei kicsik, nem kell
    // kivárni a küszöböt), és a régi irány maradéka sem tartja fel.
    wheelAcc = 0;
    stepRows(sgn);
    return;
  }
  if (wheelAcc && Math.sign(px) !== Math.sign(wheelAcc)) wheelAcc = 0;
  wheelAcc += px;
  if (Math.abs(px) < NOTCH && Math.abs(wheelAcc) < TRACKPAD_STEP) return;
  const dir = Math.sign(wheelAcc);
  wheelAcc = 0;
  stepRows(dir);
}, { passive: false });

function mcpSource() {
  const mcp = CTX.mcp;
  const call = (tool, args) => mcp.callTool(MCP_SERVER, tool, { repo: SLUG, ...args },
    { cache: false }).then(r => r.payload);
  return { fingerprint: () => call('fingerprint'),
           waitFocus: cursor => call('fingerprint', { wait: FOCUS_WAIT_S, cursor }),
           data: () => call('graph_data'),
           diff: (sha, path) => call('file_diff', { sha, path }) };
}

/* Adat még nincs (MCP-lap induláskor): az üzenet a sorok helyére is kerül. */
function notice(text, stale = false) {
  if (!DATA.commits.length) rowsEl.innerHTML = `<p class="empty">${esc(text)}</p>`;
  foot.className = stale ? 'foot stale' : 'foot';
  liveText.textContent = text;
  liveText.title = text;
  liveDot.title = text;
  liveDot.setAttribute('aria-label', stale ? 'Hiba' : 'Kapcsolódás');
  fitFoot();
}

/* MCP-hibakód → teendő. A nem `retryable` hibák nem múlnak el maguktól:
   ott megáll a pollozás (újratöltés próbálja újra). */
function mcpProblem(e) {
  switch (e?.code) {
    case 'server_not_connected':
      return 'A lap nem éri el a gépeden futó git-graph-ot. Élő adat csak a Claude appban, a saját '
        + 'gépeden jön — és ott is csak, ha az app configjában benne van (a git-graph plugin teszi be; utána az app újraindítása).';
    case 'not_in_manifest': case 'cancelled':
      return 'A git-graph szervert nem engedélyezted ehhez a laphoz — töltsd újra, és engedd meg.';
    case 'tool_error':
      return 'A git-graph hibát jelzett: ' + e.message;
    default:
      return 'A git-graph nem válaszol (' + (e?.code || e) + ').';
  }
}

/* A futó git-graph verziója; ha a telepített más, a teendővel együtt — a futó
   `git-graph --mcp` a régi kódot futtatja, amíg az app újra nem indul. */
const PLUGIN_URL = 'https://github.com/GaborTorma/git-graph';   // = plugin.json `repository`
let versionKey = null;
function showVersion(f) {
  // 2 mp-enként hívódik: csak változáskor építi újra (és méri) a láblécet.
  const key = `${f.version}|${f.installed}`;
  if (key === versionKey) return;
  versionKey = key;
  const stale = f.version && f.installed && f.installed !== f.version && !f.version.includes('+');
  versionEl.className = stale ? 'ver warn' : 'ver';
  const name = `<span class="name">${ghLink(PLUGIN_URL, 'Git Graph', 'home', 'A Git Graph a GitHubon')} </span>`;
  versionEl.innerHTML = !f.version ? '' : stale
    ? `${name} v${esc(f.version)} fut, v${esc(f.installed)} telepítve — indítsd újra a Claude appot`
    : `${name} v${esc(f.version)}`;
  fitFoot();
}

/* A verzió csak egészben látszik: ha a „Git Graph” név nem fér ki, csak a
   verziószám marad, ha az sem, semmi. */
const liveEl = document.getElementById('live');
function fitFoot() {
  versionEl.classList.remove('short', 'cut');
  if (versionEl.classList.contains('warn')) return;
  for (const cls of ['short', 'cut']) {
    if (liveEl.scrollWidth <= liveEl.clientWidth) break;
    versionEl.classList.add(cls);
  }
}
new ResizeObserver(fitFoot).observe(document.getElementById('foot'));


function startLive(src) {
  let last = '';                            // a váz üres: az első kör adatot kér
  let change = '';                          // az utolsó változás: mikor, mennyi idő alatt
  let switched = '', arrival = null;        // az utolsó session-váltás: mi indította, mennyi idő alatt
  let version = null;                       // a szerver verziója, amikor a lap betöltött
  let timer = 0, busy = false, again = false, misses = 0;
  SRC = src;
  /* Rajzol-e most a lap: rejtett keretben a requestAnimationFrame nem fut. */
  const rendering = () => new Promise(done => {
    requestAnimationFrame(() => done(true));
    setTimeout(() => done(false), 250);
  });
  /* Az új fókusz; true, ha a saját worktree megváltozott (a hívó rajzol újra). */
  function setFocus(focus, how) {
    const before = focusWt()?.slug;
    focusAuto = focus ?? null;
    if (focusWt()?.slug === before) return false;
    const since = arrival && performance.now() - arrival.at;
    switched = `\nsession-váltás ${clock()}: ` + (how
      || (since < ARRIVAL_MS ? `${arrival.kind} után ${Math.round(since)} ms` : 'a rendes körben'));
    return true;
  }
  async function poll() {
    clearTimeout(timer);
    if (busy) { again = true; return; }       // fut egy kör: utána azonnal még egy
    busy = true;
    let wait = POLL_MS;
    try {
      const t0 = performance.now();
      const f = await src.fingerprint();
      const tf = performance.now() - t0;
      // A szerver frissült és újraindult (`restart`): a lap kódja is az övé,
      // újratöltve a betöltő az új `page_code`-ot kéri.
      if (version && f.version && f.version !== version) { location.reload(); return; }
      version = version || f.version;
      // A fókusz nem adatváltozás: a lap csak a kiemelést rajzolja újra.
      const { focus, ...state } = f;
      const key = JSON.stringify(state);
      if (setFocus(focus) && key === last) { hydrateFocus(); fillBranches(); render(); }
      if (key !== last) {
        const t1 = performance.now();
        DATA = await src.data();
        const td = performance.now() - t1;
        for (const [k, v] of diffCache) if (k.startsWith('*uncommitted')) v.stale = true;
        const top = scroller.scrollTop;
        hydrate();
        fillBranches();
        applyFilters();
        scroller.scrollTop = top;
        change = `\nutolsó változás ${clock()}: adat ${Math.round(td)} ms,`
          + ` kirajzolva ${Math.round(performance.now() - t1)} ms alatt`;
      }
      last = key;
      foot.className = 'foot on';
      if (liveText.textContent) {             // az „élő” jelzés a pulzáló zöld pötty
        liveText.textContent = '';
        fitFoot();                            // a hibaüzenet helyén a verzió is elfér
      }
      liveDot.title = `Élő · frissítve ${clock()}\nujjlenyomat ${Math.round(tf)} ms` + change + switched;
      liveDot.setAttribute('aria-label', 'Élő');
      showVersion(f);
      misses = 0;
    } catch (e) {
      // Session-váltás közben a keret nem látszik, és a host-híd nem válaszol
      // (mérve): ez nem hiba — a megjelenés (`arrive`) után kérdezünk újra.
      if (e?.retryable && !(await rendering())) {
        busy = false;
        misses = 0;
        timer = setTimeout(poll, POLL_MS);
        return;
      }
      // Az átmeneti hiba elsőre nem hiba: csendben, gyorsan újra.
      if (e?.retryable && ++misses <= QUIET_RETRIES) {
        busy = false;
        timer = setTimeout(poll, Math.max(RETRY_MS, e.retryAfterMs || 0));
        return;
      }
      notice(mcpProblem(e), true);
      if (!e?.retryable) { busy = false; return; }   // magától nem javul: nincs több kör
      wait = Math.max(POLL_MS, e.retryAfterMs || 0) * 2;
    }
    busy = false;
    if (again) { again = false; wait = 0; }
    timer = setTimeout(poll, wait);             // a következő kör az előző után
  }
  /* Session-váltáskor az app ezt az egy keretet átteszi a másik session
     paneljébe. Ha közben más Artifact látszott, a keret rejtve volt: a
     megjelenése után egyszer kérdezünk — a rövid várakozás az áthelyezést
     várja ki, közben a host-híd nem válaszol. Sűrű kérdezés nem kell, a host
     rövid idő alatt ~20 hívás után visszafogja (`rate_limited`, mérve). */
  let settle = 0;
  function arrive(kind, delay = SETTLE_MS) {    // az áthelyezés végét kivárva
    arrival = { kind, at: performance.now() };
    clearTimeout(settle);
    settle = setTimeout(poll, delay);
  }
  /* Rejtve a rajzolás szünetel, megjelenéskor az IntersectionObserver jelez (mérve). */
  new IntersectionObserver(es => { if (es[es.length - 1].isIntersecting) arrive('megjelenés'); })
    .observe(document.body);
  /* Ugyanazon Artifact sessionjei között a keret rejtés nélkül költözik, és
     egyforma panelméretnél semmilyen eseményt nem kap (mérve). Ezért a lap
     egy hívást nyitva tart: a szerver akkor válaszol, amikor az app
     naplójában session-váltás jelenik meg, és a válasz az új fókuszt is
     hozza — váltásonként egyetlen hívás. */
  (async function watchFocus() {
    let cursor = '';
    for (;;) {
      try {
        const r = await src.waitFocus(cursor);
        if (typeof r?.cursor !== 'string') return;   // régi szerver: csak a rendes kör marad
        if (r.switched && 'focus' in r) {
          if (last && setFocus(r.focus, 'várakozó hívás')) { hydrateFocus(); fillBranches(); render(); }
        } else if (r.switched) arrive('session-váltás', 0);
        cursor = r.cursor;
      } catch (e) {
        const pause = e?.retryable ? Math.max(1000, e.retryAfterMs || 0) : 10000;
        await new Promise(done => setTimeout(done, pause));
      }
    }
  })();
  poll();
}

notice('Kapcsolódás a gépeden futó git-graph-hoz…');
startLive(mcpSource());
