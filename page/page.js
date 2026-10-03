
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

/* ── Ikonok ── stroke-os, 16×16-os rácson; a CSS `.ic` színezi. */
const ICONS = {
  branch: '<circle cx="5" cy="3.5" r="1.5"/><circle cx="5" cy="12.5" r="1.5"/><circle cx="11" cy="5.5" r="1.5"/><path d="M5 5v6M11 7c0 2.5-3 2.5-6 4"/>',
  tag: '<path d="M2.5 2.5h5l6 6-5 5-6-6z"/><circle cx="5.5" cy="5.5" r="1"/>',
  cloud: '<path d="M4.5 12.5h7a3 3 0 0 0 .4-6A4 4 0 0 0 4.3 7.6 2.5 2.5 0 0 0 4.5 12.5z"/>',
  commit: '<path d="M4 4v8"/><path d="M4 7h4a3 3 0 0 1 3 3v1"/><circle cx="4" cy="3" r="1.4" fill="currentColor"/><circle cx="11" cy="12.6" r="1.4" fill="currentColor"/>',
  parent: '<circle cx="8" cy="5" r="2.25"/><path d="M8 7.25v6.25M5.5 11 8 13.5 10.5 11"/>',
  open: '<path d="M9.5 2.5h4v4M13.5 2.5 7.5 8.5M12 9.5v3a1 1 0 0 1-1 1H3.5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h3"/>',
  copy: '<rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 5.5V3.5a1 1 0 0 0-1-1h-6a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2"/>',
  check: '<path d="m3.5 8.5 3 3 6-7"/>',
  file: '<path d="M4 1.5h5l3.5 3.5v9.5H4z"/><path d="M9 1.5V5h3.5"/>',
  chev: '<path d="M6.5 4.5 10 8l-3.5 3.5"/>',
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
  const laneCount = DATA.commits.reduce((m, c) => Math.max(m, c.lane), 0) + 1;
  graphW = Math.max(32, X0 * 2 + (laneCount - 1) * LANE_W);
  document.documentElement.style.setProperty('--graph-w', graphW + 'px');
  document.getElementById('repoName').textContent = DATA.meta.repo;
  document.getElementById('headName').textContent = DATA.meta.head;
  document.getElementById('headChip').hidden = !DATA.meta.head;
  fitChrome();                // a repó- és ágnév hossza dönt a kompakt fejlécről
}

/* ── Gráf rajzolása ──────────────────────────────────────────────────────── */
function laneX(l) { return X0 + l * LANE_W; }

/* A sorok Y-pozíciója a DOM-ból jön, nem sorszám × magasság: a napok fejléce
   és a kinyitott commit-panel az alattuk lévő sorokat lejjebb tolja, és a
   pöttyöknek velük kell menniük — közben a vonal egyszerűen hosszabb lesz. */
/* Az Uncommitted ál-sor a lista FÖLÖTT, a fix `#pending` sávban ül: a pontja
   ott van, a szaggatott vonala innen, a lista teteje fölül (negatív Y, az
   SVG túllóghat) fut le a HEAD-ig. */
const PENDING_Y = -(4 + ROW_H / 2);   // 4: a .graph-wrap felső margója
function drawGraph() {
  const rowIndexBySha = new Map(visible.map((c, i) => [c.sha, i]));
  const topBySha = new Map([...rowsEl.querySelectorAll('.row')].map(el => [el.dataset.sha, el.offsetTop]));
  const rowY = i => visible[i].uncommitted ? PENDING_Y
    : (topBySha.get(visible[i].sha) ?? i * ROW_H) + ROW_H / 2;
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
    // A vonal annak a sávnak a színét kapja, amelyikben a hossza nagy részén fut:
    // a merge-vonal rögtön a cél sávjába fordul, a leágazó csak a szülő fölött.
    const color = LANE_COLORS[(e.merge ? e.toLane : e.fromLane) % LANE_COLORS.length];
    // A munkakönyvtár még nem commit: szaggatva lóg a HEAD-re (görgetve rejtve).
    const dash = DATA.commits[e.fromRow].uncommitted ? ' class="pend-edge" stroke-dasharray="3 3"' : '';
    out += `<path d="${edgePath(x1, y1, x2, y2, e.merge)}" fill="none" stroke="${color}" stroke-width="2"${dash}/>`;
  }
  visible.forEach((c, i) => {
    if (c.uncommitted) return;            // a pontja a #pending sávban van
    const color = LANE_COLORS[c.lane % LANE_COLORS.length];
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
  if (merge) {
    const bend = Math.min(y1 + ROW_H, y2);
    return `M ${x1} ${y1} C ${x1} ${bend}, ${x2} ${y1}, ${x2} ${bend} L ${x2} ${y2}`;
  }
  const bend = Math.max(y2 - ROW_H, y1);
  return `M ${x1} ${y1} L ${x1} ${bend} C ${x1} ${y2}, ${x2} ${bend}, ${x2} ${y2}`;
}

/* ── Dátum ── budapesti idő szerint, magyar formában. */
const TZ = 'Europe/Budapest';
const fmtParts = (iso, opts) => Object.fromEntries(new Intl.DateTimeFormat('hu-HU',
  { timeZone: TZ, ...opts }).formatToParts(new Date(iso)).map(p => [p.type, p.value]));
const dayKey = iso => { const p = fmtParts(iso, { year: 'numeric', month: '2-digit', day: '2-digit' });
  return `${p.year}-${p.month}-${p.day}`; };
const fmtTime = iso => { const p = fmtParts(iso, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
  return `${p.hour}:${p.minute}`; };
const clock = () => { const p = fmtParts(new Date().toISOString(),
  { hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' });
  return `${p.hour}:${p.minute}:${p.second}`; };
const fmtDate = iso =>`${dayKey(iso).replaceAll('-', '.')}. ${fmtTime(iso)}`;
function dayLabel(key) {
  const [y, m, d] = key.split('-').map(Number);
  const long = new Intl.DateTimeFormat('hu-HU', { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' })
    .format(new Date(Date.UTC(y, m - 1, d)));
  const today = dayKey(new Date().toISOString());
  const yesterday = dayKey(new Date(Date.now() - 864e5).toISOString());
  return key === today ? `Ma · ${long}` : key === yesterday ? `Tegnap · ${long}` : long;
}

/* ── Sorok ───────────────────────────────────────────────────────────────── */
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
   látszanak (`main | origin`); ha szétváltak, külön-külön. */
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
    out.push({ ...r, remotes: remotes.map(o => o.name.slice(0, -r.name.length - 1)) });
  }
  return out;
}

const REF_ICON = { head: 'branch', detached: 'commit', branch: 'branch', remote: 'cloud', tag: 'tag' };
function badges(c) {
  return mergedRefs(c.refs).map(r => {
    const title = (r.kind === 'head' ? 'HEAD → ' : r.kind + ': ') + r.name
      + (r.remotes.length ? ' = ' + r.remotes.map(o => `${o}/${r.name}`).join(', ') : '');
    const remotes = r.remotes.map(o => `<span class="div"></span><span class="origin">${esc(o)}</span>`).join('');
    return `<span class="badge ref-${r.kind}" title="${esc(title)}">${icon(REF_ICON[r.kind] || 'branch')}`
      + `${esc(r.name)}${remotes}</span>`;
  }).join('');
}

function rowHtml(c) {
  const color = fresh.has(c.sha) ? ` style="color:${LANE_COLORS[c.lane % LANE_COLORS.length]}"` : '';
  const st = DATA.stats[c.sha];
  const sum = st?.files.length
    ? `<span class="sum"><span class="a">+${st.add}</span><span class="d">−${st.del}</span></span>` : '';
  const meta = c.uncommitted ? '' : `<span class="meta">${sum}<span>${esc(c.author)}</span><span class="sep">·</span>`
    + `<span class="time">${fmtTime(c.date)}</span><span class="sep">·</span><span class="sha">${c.short}</span></span>`;
  const cls = ['row', c.uncommitted && 'uncommitted', c.parents.length > 1 && 'merge'].filter(Boolean).join(' ');
  return `<button class="${cls}" type="button" data-sha="${c.sha}" aria-expanded="false">
      <span class="row-in"><span class="desc"><span class="subject"${color}>${linkify(c.subject)}</span>${badges(c)}</span>${meta}</span>
    </button>`;
}

/* A legfelső nap fejléce, ha az a mai: alaphelyzetben nem foglal helyet és
   nem látszik (a lista teteje magától értetődően ma), csak görgetéskor jelenik
   meg fent. Ha a legfelső commit régebbi, a fejléce mindig látszik. */
/* Napi csoportok (`.day-group`): a ragadós fejléc csak a saját napja alatt
   marad fent, a következő nap fejléce kitolja — nem csúsznak egymásra. */
function render() {
  // A kijelölés (fókusz) az újrarajzolás után visszaáll: sor vagy fájl.
  const focused = document.activeElement;
  const keepSha = focused?.closest?.('.row')?.dataset.sha;
  const keepPath = (focused?.closest?.('.file') || focused?.closest?.('.diff')?.previousElementSibling)
    ?.dataset.path;               // blokkon állva a fájljára áll vissza
  let day = '', html = '';
  const today = dayKey(new Date().toISOString());
  renderPending(visible.find(c => c.uncommitted));
  for (const c of visible) {
    if (c.uncommitted) continue;          // a fix #pending sávban van
    const key = dayKey(c.date);
    if (key !== day) {
      const lead = !day && key === today ? ' lead' : '';
      html += `${day ? '</section>' : ''}<section class="day-group">`
        + `<div class="day${lead}"><span class="lbl">${dayLabel(key)}</span></div>`;
      day = key;
    }
    html += rowHtml(c);
  }
  if (day) html += '</section>';
  rowsEl.innerHTML = html || '<p class="empty">Nincs a szűrésnek megfelelő commit.</p>';
  drawGraph();
  const shown = visible.filter(c => !c.uncommitted).length;   // az ál-sor nem commit
  counter.innerHTML = DATA.meta.totalCommits ? `<b>${shown}</b> / ${DATA.meta.totalCommits} commit` : '';
  if (expanded && visible.some(c => c.sha === expanded)) open(expanded); else expanded = null;
  stackDays();
  const back = keepPath && expanded
    ? [...rowsEl.querySelectorAll('.details .file')].find(f => f.dataset.path === keepPath)
    : keepSha && document.querySelector(`.row[data-sha="${CSS.escape(keepSha)}"]`);
  back?.focus({ preventScroll: true });
}

/* Az Uncommitted ál-sor mindig látszik: a lista fölötti fix sávban, saját
   üres karikával és a lista felé futó szaggatott csonkkal (görgetve rejtve). */
const pendingEl = document.getElementById('pending');
function renderPending(c) {
  pendingEl.hidden = !c;
  if (!c) { pendingEl.innerHTML = ''; return; }
  const x = laneX(c.lane), color = LANE_COLORS[c.lane % LANE_COLORS.length];
  pendingEl.innerHTML = `<svg class="pend-lane" width="${graphW}" height="${ROW_H}" aria-hidden="true">`
    + `<path class="pend-edge" d="M ${x} ${ROW_H / 2 + DOT_R + 1} L ${x} ${ROW_H}" stroke="${color}" stroke-width="2" stroke-dasharray="3 3"/>`
    + `<circle cx="${x}" cy="${ROW_H / 2}" r="${DOT_R + 1}" fill="var(--bg)" stroke="${color}" stroke-width="2"/></svg>`
    + rowHtml(c);
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
  const avatar = DATA.avatars && DATA.avatars[c.email];
  const who = c.uncommitted ? '<span class="name">Munkakönyvtár</span>'
    : `${avatar ? `<img src="${esc(avatar)}" alt="">` : ''}<span class="name">${esc(c.author)}</span>`
      + `<span class="sep">·</span><span>${fmtDate(c.date)}</span>`;
  const parents = c.parents.map(p => `<button type="button" class="hash" data-jump="${p}" title="Ugrás a szülőre">${p.slice(0, 7)}</button>`
    + miniBtn('open', `Szülő megnyitása: ${p.slice(0, 7)}`, `data-jump="${p}"`)).join('');
  const parentChip = c.parents.length ? `<span class="chip" title="Szülő${c.parents.length > 1 ? 'k' : ''}">`
    + `${icon('parent')}${parents}</span>` : '';
  const commitChip = c.uncommitted ? '' : `<span class="chip">${icon('commit')}`
    + `<span class="hash plain">${c.short}</span>`
    + (c.pushed ? ghLink(commitUrl(c), icon('open'), 'mini', 'Commit megnyitása a GitHubon') : '')
    + miniBtn('copy', 'Hash másolása', `data-copy="${c.sha}"`) + '</span>';
  return `<div class="d-head"><span class="who">${who}</span><span class="chips">${parentChip}${commitChip}</span></div>`;
}

function open(sha) {
  document.querySelectorAll('.details').forEach(d => d.remove());
  const row = document.querySelector(`.row[data-sha="${CSS.escape(sha)}"]`);
  if (!row) return;
  document.querySelectorAll('.row').forEach(r => r.setAttribute('aria-expanded', 'false'));
  row.setAttribute('aria-expanded', 'true');

  const c = DATA.commits.find(x => x.sha === sha);
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
  // Az ál-sor a fix sávban ül: a panelje a lista tetejére kerül, nem a sávba.
  if (pendingEl.contains(row)) { rowsEl.prepend(el); scroller.scrollTop = 0; } else row.after(el);
  expanded = sha;
  // Újrarajzolás (élő adatcsere) után a korábban lenyitott fájlok nyitva maradnak.
  el.querySelectorAll('.file').forEach(f => {
    if (openFiles.has(sha + '\n' + f.dataset.path)) toggleFile(f, sha, true);
  });
  drawGraph();               // a panel alatti sorok lejjebb kerültek
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
  if (!panel) return;
  const row = panel.previousElementSibling?.classList.contains('row') ? panel.previousElementSibling : null;
  const s = scroller.getBoundingClientRect();
  const top = (row || panel).getBoundingClientRect().top, bottom = panel.getBoundingClientRect().bottom;
  if (bottom - top > s.height - STEP_TOP) return;            // nem fér ki: marad, ahogy van
  if (top < s.top + STEP_TOP) scroller.scrollTop -= Math.round(s.top + STEP_TOP - top);
  else if (bottom > s.bottom) scroller.scrollTop += Math.round(bottom - s.bottom);
}

/* Az ablak (Artifact-panel) átméretezése sortörést és nézetváltást hozhat: a
   sorok Y-pozíciója elmozdul, a gráfnak követnie kell. */
new ResizeObserver(() => drawGraph()).observe(rowsEl);

/* Kompakt fejléc: ha a kontroll-sor feliratokkal két sorba törne, a
   kapcsolók felirata helyett ikon jelenik meg (a felirat tooltipben marad). */
const chromeEl = document.querySelector('.chrome');
function fitChrome() {
  chromeEl.classList.remove('compact');
  const first = chromeEl.firstElementChild, last = chromeEl.lastElementChild;
  if (last.offsetTop > first.offsetTop + first.offsetHeight / 2) chromeEl.classList.add('compact');
}
new ResizeObserver(fitChrome).observe(chromeEl);

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
  } else open(row.dataset.sha);
}
rowsEl.addEventListener('click', onListClick);
pendingEl.addEventListener('click', onListClick);

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && expanded && !document.querySelector('.menu-pop:not([hidden])')) closeCommit();
});

/* ── Szűrők ──────────────────────────────────────────────────────────────── */
/* Ágválasztó: saját listbox-menü. Az érték `''` = minden ág. */
const branchBtn = document.getElementById('branchBtn');
const branchPop = document.getElementById('branchPop');
const branchLabel = document.getElementById('branchLabel');
let branchValue = '';

/* `ahead 8, behind 3` → `↑8 ↓3` — a git felirata helyett rövid jel. */
const trackText = t => String(t || '').replace(/ahead (\d+)/, '↑$1').replace(/behind (\d+)/, '↓$1')
  .replace(/gone/, 'törölve').replace(/,\s*/, ' ');

/* A kiválasztott ágat megtartjuk, ha az adatcsere után is létezik. */
function fillBranches() {
  if (!DATA.branches.some(b => b.name === branchValue)) branchValue = '';
  const opt = (value, name, extra = '') => `<button type="button" class="option" role="option" data-value="${esc(value)}"`
    + ` aria-selected="${value === branchValue}">${icon('check')}<span class="name">${name}</span>${extra}</button>`;
  branchPop.innerHTML = opt('', 'Minden ág') + (DATA.branches.length ? '<div class="menu-sep"></div>' : '')
    + DATA.branches.map(b => opt(b.name, esc(b.name) + (b.current ? '<span class="cur">HEAD</span>' : ''),
      b.track ? `<span class="track">${esc(trackText(b.track))}</span>` : '<span></span>')).join('');
  branchLabel.textContent = branchValue || 'Minden ág';
}

/* Közös legördülő menü (ágválasztó, téma): nyíl-, Home/End-, Escape- és
   Tab-billentyű, kattintás kívülre csuk. `onPick` a választott opciót kapja. */
function makeMenu(btn, pop, onPick) {
  const toggle = open => {
    pop.hidden = !open;
    btn.setAttribute('aria-expanded', String(open));
    if (open) (pop.querySelector('[aria-selected="true"]') || pop.querySelector('.option'))?.focus();
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
    const items = [...pop.querySelectorAll('.option')];
    const i = items.indexOf(document.activeElement);
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      items[(i + (e.key === 'ArrowDown' ? 1 : items.length - 1)) % items.length].focus();
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
  branchValue = o.dataset.value;
  fillBranches();
  applyFilters();
});

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

/* Keresés: minden szó (szóközzel elválasztva) szerepeljen a commit
   üzenetében, törzsében, szerzőjében, e-mail-címében, ref-neveiben — vagy a
   hash eleje legyen. Kis- és nagybetű, ékezet nem számít. */
const searchEl = document.getElementById('search');
const fold = s => String(s).toLowerCase().normalize('NFD').replace(/\p{M}/gu, '');
function matches(c, words) {
  if (!words.length) return true;
  const hay = fold([c.subject, c.body, c.author, c.email, ...c.refs.map(r => r.name)].join('\n'));
  return words.every(w => hay.includes(w) || c.sha.startsWith(w));
}

function applyFilters() {
  const branch = branchValue;
  const remotes = document.getElementById('showRemotes').checked;
  const refsOnly = document.getElementById('onlyRefs').checked;
  const words = fold(searchEl.value).split(/\s+/).filter(Boolean);
  const keep = branch ? ancestryOf(branch) : null;

  visible = DATA.commits.filter(c => {
    if (c.uncommitted) return !words.length;   // állapot, nem commit: keresésnél nem kell
    if (keep && !keep.has(c.sha)) return false;
    if (refsOnly && c.refs.length === 0) return false;
    if (!remotes && c.refs.length && c.refs.every(r => r.kind === 'remote')) return false;
    return matches(c, words);
  });
  render();
}
['showRemotes', 'onlyRefs'].forEach(id =>
  document.getElementById(id).addEventListener('change', applyFilters));
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
             && !document.querySelector('.menu-pop:not([hidden])')) {   // nyitott menüt a menü csuk
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
    return p && DATA.commits.find(x => x.sha === p);
  }
  return DATA.commits.find(x => other ? x.parents.slice(1).includes(c.sha) : x.parents[0] === c.sha);
}
document.addEventListener('keydown', e => {
  if (e.altKey || e.target.closest('input, textarea, .menu-pop')
      || document.querySelector('.menu-pop:not([hidden])')) return;
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
    if (k === 'ArrowDown') select((isOpen && hunksOf(file)[0]) || files[files.indexOf(file) + 1] || belowCommit());
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
    if (expanded !== cur.sha) open(cur.sha);
    const first = rowsEl.querySelector('.details .file');
    if (first) select(first); else select(rowOf(cur));
  } else if (k === 'ArrowLeft' && cur && expanded === cur.sha) {
    closeCommit();
  } else if ((k === 'h' || k === 'H') && !mod) {
    handled = selectCommit(visible.find(c => c.refs.some(r => r.kind === 'head' || r.kind === 'detached')));
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
function setTheme(mode) {
  const root = document.documentElement;
  if (mode === 'auto') root.removeAttribute('data-theme'); else root.setAttribute('data-theme', mode);
  const [, label, svgPath] = THEMES.find(t => t[0] === mode) || THEMES[0];
  document.getElementById('themeIcon').innerHTML = svgPath;
  themeBtn.setAttribute('aria-label', `Téma: ${label.toLowerCase()}`);
  themeBtn.title = `Téma: ${label.toLowerCase()}`;
  themePop.innerHTML = THEMES.map(([value, name, path]) =>
    `<button type="button" class="option with-icon" role="option" data-value="${value}" aria-selected="${value === mode}">`
    + `<svg class="ic ti" viewBox="0 0 16 16" aria-hidden="true">${path}</svg>`
    + `<span class="name">${name}</span>${icon('check')}</button>`).join('');
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
const foot = document.getElementById('foot');
const liveText = document.getElementById('liveText');
const versionEl = document.getElementById('version');
/* A felül ragadó nap fejléce egyben tűnik el, amikor az alja eléri a
   következő nap fejlécét — nem csúszik ki fokozatosan, nem lóg rá a másikra. */
function stackDays() {
  scroller.classList.toggle('scrolled', scroller.scrollTop > 0);
  pendingEl.classList.toggle('scrolled', scroller.scrollTop > 0);
  const days = rowsEl.querySelectorAll('.day');
  const top = scroller.getBoundingClientRect().top;
  for (let i = 0; i < days.length; i++) {
    const next = days[i + 1];
    const y = days[i].getBoundingClientRect().top;
    const touching = next && next.getBoundingClientRect().top - y <= days[i].offsetHeight + 0.5;
    days[i].classList.toggle('gone', Boolean(touching));
    // Felül ragadva (`.stuck`) a vonal nem kell, csak a felirat.
    days[i].classList.toggle('stuck', scroller.scrollTop > 0 && y - top <= 0.5);
  }
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
  return { fingerprint: () => call('fingerprint'), data: () => call('graph_data'),
           diff: (sha, path) => call('file_diff', { sha, path }) };
}

/* Adat még nincs (MCP-lap induláskor): az üzenet a sorok helyére is kerül. */
function notice(text, stale = false) {
  if (!DATA.commits.length) rowsEl.innerHTML = `<p class="empty">${esc(text)}</p>`;
  foot.className = stale ? 'foot stale' : 'foot';
  liveText.textContent = text;
  liveText.title = text;
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
function showVersion(f) {
  const stale = f.version && f.installed && f.installed !== f.version && !f.version.includes('+');
  versionEl.className = stale ? 'ver warn' : 'ver';
  versionEl.textContent = !f.version ? '' : stale
    ? `git-graph ${f.version} fut, ${f.installed} telepítve — indítsd újra a Claude appot`
    : `git-graph ${f.version}`;
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
        change = `\nutolsó változás ${clock()}: adat ${Math.round(td)} ms,`
          + ` kirajzolva ${Math.round(performance.now() - t1)} ms alatt`;
      }
      last = key;
      foot.className = 'foot on';
      liveText.textContent = `Élő · frissítve ${clock()}`;
      liveText.title = `ujjlenyomat ${Math.round(tf)} ms` + change;
      showVersion(f);
    } catch (e) {
      notice(mcpProblem(e), true);
      if (!e?.retryable) return;                // magától nem javul: nincs több kör
      wait = Math.max(POLL_MS, e.retryAfterMs || 0) * 2;
    }
    setTimeout(poll, wait);                     // a következő kör az előző után
  }
  poll();
}

notice('Kapcsolódás a gépeden futó git-graph-hoz…');
startLive(mcpSource());
