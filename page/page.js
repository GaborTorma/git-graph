
/* A betöltő (az Artifact publikált lapja) adja: a repó slugja és neve, az MCP
   kliens. Az adatot a lap a Claude app host-hídján át a gépen futó
   `git-graph --mcp`-ből kéri (a SLUG repóét); induláskor csak az üres váz van. */
const CTX = globalThis.GIT_GRAPH;
const SLUG = CTX.slug;
const MCP_SERVER = CTX.server;
let DATA = { commits: [], edges: [], stats: {}, branches: [],
  meta: { repo: CTX.repo, repoUrl: '', head: '', totalCommits: 0, shown: 0, dirty: 0,
          generated: '', worktrees: [] } };

// A Git Graph alap sáv-palettája: sávindex szerint ciklikusan.
const LANE_COLORS = ['#0085d9','#d9008f','#00d90a','#d9c000','#d90000',
                     '#4d00d9','#d94a00','#00d9cc','#e138e8','#85d900'];
const ROW_H = 24, LANE_W = 16, X0 = 12, DOT_R = 4;
// Friss commitok: a legújabbtól visszafelé, amíg a szomszédok közt ≤ 10 mp telt
// el — és csak 5 percig. Egy újabb sorozat így magától leváltja az előzőt.
const FRESH_GAP_MS = 10 * 1000, FRESH_FOR_MS = 5 * 60 * 1000;
let fresh = new Set();
let freshTimer = 0;

const rowsEl = document.getElementById('rows');
const svg = document.getElementById('lanes');
const counter = document.getElementById('counter');
let expanded = null;      // a kinyitott commit sha-ja
let visible = DATA.commits; // szűrés utáni lista

let graphW = 72;

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
  const laneCount = DATA.commits.reduce((m, c) => Math.max(m, c.lane), 0) + 1;
  // Csak annyi, amennyit a sávok kérnek — a fejlécben ikon van, nem felirat.
  graphW = Math.max(28, X0 * 2 + (laneCount - 1) * LANE_W);
  document.documentElement.style.setProperty('--graph-w', graphW + 'px');
  document.getElementById('repoName').textContent = DATA.meta.repo;
  document.getElementById('headRef').textContent = DATA.meta.head
    ? DATA.meta.head + ' · ' + DATA.meta.totalCommits + ' commit' : '';
}

/* ── Gráf rajzolása ──────────────────────────────────────────────────────── */
function laneX(l) { return X0 + l * LANE_W; }

/* A sorok Y-pozíciója a DOM-ból jön, nem sorszám × magasság: kinyitott
   commit-panel esetén az alatta lévő sorok lejjebb csúsznak, és a pöttyöknek
   velük kell menniük — a panel mellett a vonal egyszerűen hosszabb lesz. */
function drawGraph() {
  const rowIndexBySha = new Map(visible.map((c, i) => [c.sha, i]));
  const tops = [...rowsEl.querySelectorAll('.row')].map(el => el.offsetTop);
  const rowY = i => (tops[i] ?? i * ROW_H) + ROW_H / 2;
  const h = Math.max(rowsEl.offsetHeight, visible.length * ROW_H);
  svg.setAttribute('width', graphW);
  svg.setAttribute('height', h);
  svg.setAttribute('viewBox', `0 0 ${graphW} ${h}`);

  let out = '';
  for (const e of DATA.edges) {
    const a = rowIndexBySha.get(DATA.commits[e.fromRow].sha);
    const b = rowIndexBySha.get(DATA.commits[e.toRow].sha);
    if (a === undefined || b === undefined) continue;   // szűrve
    const x1 = laneX(e.fromLane), y1 = rowY(a);
    const x2 = laneX(e.toLane),   y2 = rowY(b);
    const color = LANE_COLORS[(e.merge ? e.fromLane : e.toLane) % LANE_COLORS.length];
    // A munkakönyvtár még nem commit: szaggatva lóg a HEAD-re.
    const dash = DATA.commits[e.fromRow].uncommitted ? ' stroke-dasharray="3 3"' : '';
    out += `<path d="${edgePath(x1, y1, x2, y2, e.merge)}" fill="none" stroke="${color}" stroke-width="2"${dash}/>`;
  }
  visible.forEach((c, i) => {
    const color = LANE_COLORS[c.lane % LANE_COLORS.length];
    const merge = c.parents.length > 1;
    // Az ál-sor pontja üres karika: a szaggatott vonal már jelzi, hogy nem
    // commit — a pöttyözött körvonal ezen a méreten csak elmosódna.
    const hollow = merge || c.uncommitted;
    if (fresh.has(c.sha)) out += `<circle cx="${laneX(c.lane)}" cy="${rowY(i)}" r="8" fill="${color}" opacity=".3"/>`;
    out += `<circle cx="${laneX(c.lane)}" cy="${rowY(i)}" r="${hollow ? DOT_R + 1 : DOT_R}"`
        +  ` fill="${hollow ? 'var(--bg)' : color}" stroke="${color}" stroke-width="2"/>`;
  });
  svg.innerHTML = out;
}

/* Sávváltásnál ott hajlik a vonal, ahol a git is: merge-nél rögtön a merge
   commit alatt, ág-leágazásnál pedig közvetlenül a szülő fölött. */
function edgePath(x1, y1, x2, y2, merge) {
  if (x1 === x2) return `M ${x1} ${y1} L ${x2} ${y2}`;
  if (merge) {
    const bend = Math.min(y1 + ROW_H, y2);
    return `M ${x1} ${y1} C ${x1} ${bend}, ${x2} ${y1}, ${x2} ${bend} L ${x2} ${y2}`;
  }
  const bend = Math.max(y2 - ROW_H, y1);
  return `M ${x1} ${y1} L ${x1} ${bend} C ${x1} ${y2}, ${x2} ${bend}, ${x2} ${y2}`;
}

/* ── Sorok ───────────────────────────────────────────────────────────────── */
const esc = s => String(s).replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
const pad = n => String(n).padStart(2, '0');
const fmtDate = iso => { const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} `
       + `${pad(d.getHours())}:${pad(d.getMinutes())}`; };

/* GitHub-linkek: valódi `<a target="_blank">` — az Artifact keretéből a Claude
   app csak ezt engedi át (mérve: a `window.open` el sem jutott hozzá). Commit
   és fájl csak pusholt commitnál (`pushed`, a Python jelöli): a helyi a
   GitHubon 404 lenne. A fájl-diff horgonyát (`anchor`) is a Python számolja. */
const ghLink = (href, html) =>
  `<a class="gh-link" href="${href}" target="_blank" rel="noopener">${html}</a>`;

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
const shaHtml = (c, text) => c.pushed ? ghLink(commitUrl(c), text) : text;
const pathHtml = (c, f) => c.pushed
  ? ghLink(commitUrl(c) + (f.anchor ? '#diff-' + f.anchor : ''), esc(f.path)) : esc(f.path);

function badges(c) {
  return c.refs.map(r => {
    const label = r.kind === 'head' ? r.name : r.name;
    const title = r.kind === 'head' ? 'HEAD → ' + r.name : r.kind + ': ' + r.name;
    return `<span class="badge ref-${r.kind}" title="${esc(title)}"><span class="dot"></span>${esc(label)}</span>`;
  }).join('');
}

function render() {
  rowsEl.innerHTML = visible.map((c, i) => `
    <button class="row${c.uncommitted ? ' uncommitted' : ''}" type="button" data-sha="${c.sha}" aria-expanded="false">
      <span class="cell"></span>
      <span class="cell desc">${badges(c)}<span class="subject"${fresh.has(c.sha)
        ? ` style="color:${LANE_COLORS[c.lane % LANE_COLORS.length]}"` : ''}>${linkify(c.subject)}</span></span>
      <span class="cell date">${fmtDate(c.date)}</span>
      <span class="cell author">${esc(c.author)}</span>
      <span class="cell sha mono">${shaHtml(c, c.short)}</span>
    </button>`).join('') || '<p class="empty">Nincs a szűrésnek megfelelő commit.</p>';
  drawGraph();
  const shown = visible.filter(c => !c.uncommitted).length;   // az ál-sor nem commit
  counter.innerHTML = `<b>${shown}</b> commit látszik / ${DATA.meta.totalCommits}`;
  if (expanded && visible.some(c => c.sha === expanded)) open(expanded); else expanded = null;
}

/* ── Commit-részletek ────────────────────────────────────────────────────── */
function open(sha) {
  document.querySelectorAll('.details').forEach(d => d.remove());
  const row = rowsEl.querySelector(`.row[data-sha="${sha}"]`);
  if (!row) return;
  rowsEl.querySelectorAll('.row').forEach(r => r.setAttribute('aria-expanded', 'false'));
  row.setAttribute('aria-expanded', 'true');

  const c = DATA.commits.find(x => x.sha === sha);
  const st = DATA.stats[sha] || { files: [], add: 0, del: 0 };
  const parents = c.parents.length
    ? c.parents.map(p => `<a data-jump="${p}">${p.slice(0, 7)}</a>`).join(' · ')
    : '—';

  const el = document.createElement('div');
  el.className = 'details';
  el.innerHTML = `
    <h2>${linkify(c.subject)}</h2>
    <dl class="meta">
      <dt>Commit</dt><dd class="mono">${shaHtml(c, c.sha)}</dd>
      <dt>Szülő</dt><dd class="mono">${parents}</dd>
      <dt>Szerző</dt><dd>${esc(c.author)}</dd>
      <dt>Dátum</dt><dd>${fmtDate(c.date)}</dd>
    </dl>
    ${c.body ? `<p class="body-text">${linkify(c.body)}</p>` : ''}
    <div class="files">
      <div class="files-head">${st.files.length} fájl ·
        <span style="color:var(--add)">+${st.add}</span>
        <span style="color:var(--del)">−${st.del}</span></div>
      ${st.files.map(f => `<div class="file" data-path="${esc(f.path)}" aria-expanded="false">
        <span class="chev" aria-hidden="true">›</span>
        <span class="path mono">${pathHtml(c, f)}</span>
        <span class="churn mono">${f.new ? 'új' : f.bin ? 'bin'
          : `<span class="a">+${f.add}</span> <span class="d">−${f.del}</span>`}</span></div>
        <div class="diff" hidden></div>`).join('')}
    </div>`;
  row.after(el);
  expanded = sha;
  // Újrarajzolás (élő adatcsere) után a korábban lenyitott fájlok nyitva maradnak.
  el.querySelectorAll('.file').forEach(f => {
    if (openFiles.has(sha + '\n' + f.dataset.path)) toggleFile(f, sha, true);
  });
  drawGraph();               // a panel alatti sorok lejjebb kerültek
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
  if (!on) { openFiles.delete(key); drawGraph(); return; }
  openFiles.add(key);

  const show = html => {
    if (!fileEl.isConnected || fileEl.getAttribute('aria-expanded') !== 'true') return;
    box.innerHTML = html;
    drawGraph();
  };
  const cached = diffCache.get(key);
  if (!SRC) return show('<p class="diff-note">A diff csak élő nézetben látszik '
    + '(az Artifact a Claude appban).</p>');
  show(cached ? diffHtml(cached.data) : '<p class="diff-note">Betöltés…</p>');
  if (cached && !cached.stale) return;
  SRC.diff(sha, fileEl.dataset.path).then(
    d => { diffCache.set(key, { data: d }); show(diffHtml(d)); },
    e => { if (!cached) show(`<p class="diff-note">A diff nem tölthető be: ${esc(
      (e && (e.message || e.code)) || e)}</p>`); });
}

/* Mindkét nézet elkészül (egymás alatti és side-by-side); hogy melyik látszik,
   azt a `.diff` szélessége dönti el egy container queryvel — átméretezéskor
   újrarenderelés nélkül vált. Ha a diffben csak hozzáadás vagy csak törlés van
   (új fájl, vagy beszúrás / kivágás a változatlan sorok közt), a side-by-side
   egyik oldala végig üres lenne: ott csak az egymás alatti nézet készül.
   Hunkok közt a kihagyott sorok száma a régi oldal sorszámaiból jön. */
function diffHtml(d) {
  if (d.note) return `<p class="diff-note">${esc(d.note)}</p>`;
  if (d.binary) return '<p class="diff-note">Bináris fájl.</p>';
  if (!d.hunks.length) return '<p class="diff-note">Nincs megjeleníthető változás.</p>';
  let uni = '', split = '', oldEnd = 1;
  for (const h of d.hunks) {
    const gap = h.old - oldEnd;
    const gapHtml = gap > 0 ? `<p class="diff-gap">${gap} változatlan sor</p>` : '';
    uni += gapHtml + h.lines.map(l => `<div class="diff-line mono${KIND[l.t]}">`
      + diffCell(l, l.n) + '</div>').join('');
    split += gapHtml + splitRows(h);
    oldEnd = h.old + h.lines.filter(l => l.t !== '+').length;
  }
  const kinds = new Set(d.hunks.flatMap(h => h.lines.map(l => l.t)));
  const oneSided = !(kinds.has('+') && kinds.has('-'));   // a változatlan sor nem számít
  return (oneSided ? `<div>${uni}</div>`
    : `<div class="diff-uni">${uni}</div><div class="diff-split">${split}</div>`)
    + (d.truncated ? '<p class="diff-note">… a diff túl hosszú, a vége le van vágva.</p>' : '');
}

const KIND = { ' ': '', '+': ' add', '-': ' del' };
const diffCell = (l, no) => `<span class="no">${no}</span>`
  + `<span class="sg">${l.t === ' ' ? '' : l.t === '-' ? '−' : '+'}</span>`
  + `<span class="tx">${marked(l.s, l.hl)}</span>`;

/* Side-by-side: a változatlan sor mindkét oldalon (balra a régi sorszámmal), a
   törölt blokk és az utána jövő hozzáadott blokk párjai (`p`, a Python
   `pair_lines`-a) egy sorba, a pár nélküliek egyedül, a párok közé —
   ugyanaz a párosítás, amiből a Python a szó-kiemelést számolja. */
function splitRows(h) {
  const L = h.lines, side = (l, no) => l
    ? `<div class="half${KIND[l.t]}">${diffCell(l, no)}</div>` : '<div class="half none"></div>';
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
      out += `<div class="split-row mono">${side(del, del && del.n)}${side(add, add && add.n)}</div>`;
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

/* Az ablak (Artifact-panel) átméretezése sortörést és nézetváltást hozhat: a
   sorok Y-pozíciója elmozdul, a gráfnak követnie kell. */
new ResizeObserver(() => drawGraph()).observe(rowsEl);

const marked = (s, hl) => {
  if (!hl || !hl.length) return esc(s);
  let out = '', at = 0;
  for (const [a, b] of hl) { out += esc(s.slice(at, a)) + `<mark>${esc(s.slice(a, b))}</mark>`; at = b; }
  return out + esc(s.slice(at));
};

rowsEl.addEventListener('click', e => {
  if (e.target.closest('a[href]')) return;   // GitHub-link: nyíljon, a sor ne csukódjon
  const file = e.target.closest('.file');
  if (file) { toggleFile(file, expanded, file.getAttribute('aria-expanded') !== 'true'); return; }
  const jump = e.target.closest('[data-jump]');
  if (jump) {
    const target = rowsEl.querySelector(`.row[data-sha="${jump.dataset.jump}"]`);
    if (target) { open(jump.dataset.jump); target.scrollIntoView({ block: 'center' }); }
    return;
  }
  const row = e.target.closest('.row');
  if (!row) return;
  if (row.getAttribute('aria-expanded') === 'true') {
    row.setAttribute('aria-expanded', 'false');
    document.querySelectorAll('.details').forEach(d => d.remove());
    expanded = null;
    drawGraph();
  } else open(row.dataset.sha);
});

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && expanded) {
    document.querySelectorAll('.details').forEach(d => d.remove());
    rowsEl.querySelectorAll('.row').forEach(r => r.setAttribute('aria-expanded', 'false'));
    expanded = null;
    drawGraph();
  }
});

/* ── Szűrők ──────────────────────────────────────────────────────────────── */
const branchSel = document.getElementById('branchSel');

/* A kiválasztott ágat megtartjuk, ha az adatcsere után is létezik. */
function fillBranches() {
  const keep = branchSel.value;
  branchSel.innerHTML = '<option value="">Minden ág</option>' +
    DATA.branches.map(b => `<option value="${esc(b.name)}"${b.current ? ' selected' : ''}>`
      + esc(b.name) + (b.track ? ` (${esc(b.track)})` : '') + '</option>').join('');
  branchSel.value = DATA.branches.some(b => b.name === keep) ? keep : '';
}

function ancestryOf(name) {
  const tip = DATA.commits.find(c => c.refs.some(r => r.name === name &&
    (r.kind === 'branch' || r.kind === 'head')));
  if (!tip) return null;
  const keep = new Set(), stack = [tip.sha];
  const bySha = new Map(DATA.commits.map(c => [c.sha, c]));
  while (stack.length) {
    const sha = stack.pop();
    if (keep.has(sha)) continue;
    keep.add(sha);
    (bySha.get(sha)?.parents || []).forEach(p => bySha.has(p) && stack.push(p));
  }
  return keep;
}

function applyFilters() {
  const branch = branchSel.value;
  const remotes = document.getElementById('showRemotes').checked;
  const refsOnly = document.getElementById('onlyRefs').checked;
  const keep = branch ? ancestryOf(branch) : null;

  visible = DATA.commits.filter(c => {
    if (c.uncommitted) return true;       // állapot, nem commit: mindig látszik
    if (keep && !keep.has(c.sha)) return false;
    if (refsOnly && c.refs.length === 0) return false;
    if (!remotes && c.refs.length && c.refs.every(r => r.kind === 'remote')) return false;
    return true;
  });
  render();
}
['branchSel', 'showRemotes', 'onlyRefs'].forEach(id =>
  document.getElementById(id).addEventListener('change', applyFilters));

/* ── Téma ────────────────────────────────────────────────────────────────── */
document.getElementById('themeBtn').addEventListener('click', () => {
  const root = document.documentElement;
  const dark = root.getAttribute('data-theme') === 'dark' ||
    (!root.hasAttribute('data-theme') && !matchMedia('(prefers-color-scheme: light)').matches);
  root.setAttribute('data-theme', dark ? 'light' : 'dark');
});

hydrate();
fillBranches();
render();

/* ── Élő frissítés ───────────────────────────────────────────────────────
   A forrás a gépen futó `git-graph --mcp` (a Claude app host-hídján át). Az olcsó
   ujjlenyomatot pollozzuk, teljes adatot csak tényleges változásra kérünk: a
   lap helyben rajzol újra, a nyitott panel, a szűrők és a görgetés megmaradnak.
   A lábléc a mért időket is mutatja (ujjlenyomat · adat). */
const POLL_MS = 2000;
const foot = document.getElementById('foot');
const scroller = document.querySelector('.scroll');

function mcpSource() {
  const mcp = CTX.mcp;
  const call = (tool, args) => mcp.callTool(MCP_SERVER, tool, { repo: SLUG, ...args },
    { cache: false }).then(r => r.payload);
  return { fingerprint: () => call('fingerprint'), data: () => call('graph_data'),
           diff: (sha, path) => call('file_diff', { sha, path }),
           where: 'a gépeden futó git-graph' };
}

/* Adat még nincs (MCP-lap induláskor): az üzenet a sorok helyére kerül. */
function notice(text, stale = false) {
  if (!DATA.commits.length) rowsEl.innerHTML = `<p class="empty">${esc(text)}</p>`;
  foot.className = stale ? 'foot stale' : 'foot';
  foot.textContent = text;
}

/* MCP-hibakód → teendő. A nem `retryable` hibák nem múlnak el maguktól:
   ott megáll a pollozás (újratöltés próbálja újra). */
function mcpProblem(e) {
  switch (e && e.code) {
    case 'server_not_connected':
      return 'A lap nem éri el a gépeden futó git-graph-ot. Élő adat csak a Claude appban, a saját '
        + 'gépeden jön — és ott is csak, ha az app configjában benne van (a git-graph plugin teszi be; utána az app újraindítása).';
    case 'not_in_manifest': case 'cancelled':
      return 'A git-graph szervert nem engedélyezted ehhez a laphoz — töltsd újra, és engedd meg.';
    case 'tool_error':
      return 'A git-graph hibát jelzett: ' + e.message;
    default:
      return 'A git-graph nem válaszol (' + ((e && e.code) || e) + ').';
  }
}

/* A futó git-graph verziója; ha a telepített más, a teendővel együtt — a futó
   `git-graph --mcp` a régi kódot futtatja, amíg az app újra nem indul. */
function versionText(f) {
  if (!f.version) return '';
  if (!f.installed || f.installed === f.version) return ` v${f.version}`;
  return ` v${f.version} fut, v${f.installed} telepítve — indítsd újra a Claude appot`;
}

function startLive(src) {
  let last = '';                            // a váz üres: az első kör adatot kér
  let change = '';                          // az utolsó változás: mikor, mennyi idő alatt
  let version = null;                       // a szerver verziója, amikor a lap betöltött
  SRC = src;
  async function poll() {
    let wait = POLL_MS;
    try {
      const t0 = performance.now();
      const f = await src.fingerprint();
      const tf = performance.now() - t0;
      // A szerver frissült és újraindult (`restart`): a lap kódja is az övé,
      // újratöltve a betöltő az új `page_code`-ot kéri.
      if (version && f.version && f.version !== version) { location.reload(); return; }
      version = version || f.version;
      const key = JSON.stringify(f);
      if (key !== last) {
        const t1 = performance.now();
        DATA = await src.data();
        const td = performance.now() - t1;
        for (const [k, v] of diffCache) if (k.startsWith('*uncommitted\n')) v.stale = true;
        const top = scroller.scrollTop;
        hydrate();
        fillBranches();
        applyFilters();
        scroller.scrollTop = top;
        change = ` · utolsó változás ${new Date().toLocaleTimeString()}: adat ${Math.round(td)} ms,`
          + ` kirajzolva ${Math.round(performance.now() - t1)} ms alatt`;
      }
      last = key;
      foot.className = 'foot';
      foot.textContent = `Élő · ${src.where}${versionText(f)} · ${new Date().toLocaleTimeString()}`
        + ` · ujjlenyomat ${Math.round(tf)} ms` + change;
    } catch (e) {
      notice(mcpProblem(e), true);
      if (!(e && e.retryable)) return;          // magától nem javul: nincs több kör
      wait = Math.max(POLL_MS, (e && e.retryAfterMs) || 0) * 2;
    }
    setTimeout(poll, wait);                     // a következő kör az előző után
  }
  poll();
}

notice('Kapcsolódás a gépeden futó git-graph-hoz…');
startLive(mcpSource());
