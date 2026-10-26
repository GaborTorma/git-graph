/* Chipek: ágak, tagek, worktree-k, hivatkozások (PR, issue, release) és az ágak
   távolságai. */
import { icon } from './icons.js';
import { branchColor, commitBySha, focusWt, laneColor, lcStyle, linkedWts, remoteShown, remotesOn, shownRefs, worktrees, wtColor } from './model.js';
import { DATA } from './state.js';
import { esc, ghLink } from './util.js';

/* A HEAD-chip a saját worktree ágát mutatja; több worktree-nél fölötte a
   worktree-pillek: ág, változások pöttye, ↑ahead. */
/* A fejléc chipje (a saját worktree-é): worktree-ikon,
   branch-ikon, az ág neve és az ág távolságai (`distSegs`). A commitolatlan
   változást a rögzített sáv WIP-sora mutatja. */
export function wtChipInner(w) {
  const linked = !w.main;
  // A fő checkout üres mappát kap, ha vannak worktree-k (megkülönböztetésül); a jel a
  // commit-chiphez hasonlóan az ág-ikonhoz tapad.
  const mark = linked ? 'worktree' : linkedWts().length ? 'mainWorktree' : '';
  // A HEAD commit-chipjének (`badges`) ága: a vele egy helyen álló remote párjai.
  const ref = w.branch && remotesOn()
    ? mergedRefs(shownRefs(commitBySha(w.head)?.refs || [])).find(x => x.name === w.branch) : null;
  const pairs = ref?.remotes || [];
  const multi = (DATA.meta.remotes || []).length > 1;
  // Egy remote-nál a szinkronban lévő ág felhő-és-ág ikont kap (az alapágé teli); többnél
  // remote-onként egy szakasz a nevével; ág nélkül lánc.
  const branchIc = !w.branch ? 'detached' : pairs.length && !multi ? syncedIcon(ref) : 'branch';
  // Leválasztott hozzáadott worktree: a neve is, mint a commit-chipen (név | lánc hash).
  const wtName = linked && !w.branch ? `${icon(mark)}<span class="chip-name">${esc(w.name)}</span><span class="div"></span>` : '';
  return (wtName || (mark ? `<span class="synced wt-lead">${icon(mark)}</span>` : '')) + icon(branchIc)
    + `<span class="chip-name">${esc(w.branch || String(w.head || '').slice(0, 7))}</span>`
    + distSegs(w.branch || '', wtTrack(w))
    + (multi ? remoteSegs(pairs) : '');
}

/* A remote alapértelmezett ága (`origin/HEAD` célja): teli felhő; több remote-nál
   remote-onként egy szakasz a nevével (`main | ☁ origin | ☁ upstream`); egy remote-nál
   a vele egy helyen álló ág felhő-és-ág ikont kap (az alapágé teli). */
const cloudOf = on => icon('cloud', on ? 'ic filled' : 'ic');
const remoteSegs = pairs => pairs.map(o => `<span class="div"></span><span class="synced">${cloudOf(o.default)}${esc(o.name)}</span>`).join('');
const syncedIcon = ref => ref.default ? 'branchCloudFill' : 'branchCloud';

/* Az ág távolságai (`DATA.meta.tracks`, csak a nem nulla irány): `↑a ↓b` az
   alapághoz (amire az origin/HEAD mutat) — ikon nélkül, a chip maga az ág —, és
   `☁ ↑c ↓d` az upstreamjéhez, csak ha nem egy helyen állnak (különben a chip a
   felhő-és-ág ikont kapja); a remote-only chipen utolsóként `⑂ ↑e ↓f` a helyi ágához.
   Közös ős nélkül (`unrelated`, pl. egy `git subtree push` remote-ja) az alapághoz
   mért szakasz helyén áthúzott lánc: a számok ott a két oldal összes commitja volnának.
   Ami a chipből már kiderül, annak nem jár újabb ikon. */
const arrows = ([a, b]) => [a && `↑${a}`, b && `↓${b}`].filter(Boolean).join(' ');
/* A worktree távolságai: az ágáé, leválasztott HEAD-nél (nincs ágkulcs) a worktree adja a
   HEAD-commit távolságát az alapágtól. */
export const wtTrack = w => (w?.branch ? DATA.meta.tracks?.[w.branch] : { base: w?.base }) || {};
/* Ugyanez szövegesen, a tooltipbe (soronként egy viszony). */
export function distText(name, tr = DATA.meta.tracks?.[name] || {}) {
  const base = (DATA.meta.base || 'main').replace(/^[^/]+\//, '');
  const lines = [];
  if (tr.unrelated) lines.push('Külön történet: nincs közös őse az alapággal');
  if (tr.base?.[0]) lines.push(`↑${tr.base[0]}: ennyi commit ${name ? 'az ágon' : 'a HEAD-ig'} a ${base} óta`);
  if (tr.base?.[1]) lines.push(`↓${tr.base[1]}: ennyit haladt közben a ${base}`);
  if (tr.up?.[0]) lines.push(`☁ ↑${tr.up[0]}: pusholatlan commit`);
  if (tr.up?.[1]) lines.push(`☁ ↓${tr.up[1]}: a remote-on van, helyben nincs`);
  if (tr.local?.[0]) lines.push(`⑂ ↑${tr.local[0]}: ennyivel jár a helyi ág előtt`);
  if (tr.local?.[1]) lines.push(`⑂ ↓${tr.local[1]}: ennyivel van a helyi ág mögött`);
  return lines.length ? `\n${lines.join('\n')}` : '';
}
function distSegs(name, tr = DATA.meta.tracks?.[name] || {}) {
  // Remote ágak nélkül a remote-hoz mért szakaszok sem kellenek (☁ és a remote chip ⑂-je).
  const remote = remotesOn();
  // Az alapág helyi párján (pl. `main`) nem dolgozunk: ha előrébb jár a remote-jánál,
  // az anomália (teszt vagy tévedés) — figyelmeztető szín és magyarázat.
  const base = DATA.meta.base || '', local = base.slice(base.indexOf('/') + 1);
  const odd = base && name === local && tr.up?.[0] > 0;
  const warn = odd ? ` warn" data-tip="${esc(`A helyi ${name}-en ${tr.up[0]} pusholatlan commit van`)}` : '';
  // Az upstream felhője teli, ha az az alapág (`origin/HEAD` célja), mint a remote chipen.
  const up = DATA.branches.find(b => !b.remote && b.name === name)?.upstream;
  const upShown = remote && (!up || remoteShown(up));        // a rejtett remote-hoz mért szakasz sem kell
  const unrelated = tr.unrelated ? `<span class="div"></span><span class="dist unrelated">${icon('linkOff')}</span>` : '';
  return unrelated + [[tr.base, '', ''], [upShown && tr.up, cloudOf(base && up === base), warn], [remote && tr.local, icon('branch'), '']]
    .filter(([d]) => d && (d[0] || d[1]))
    .map(([d, ic, cls]) => `<span class="div"></span><span class="dist${cls}">${ic}${arrows(/** @type {[number, number]} */ (d))}</span>`).join('');
}

/* `#12` és `owner/repo#12` → issue/PR (a `/issues/N` a PR-ra átirányít).
   Előtte nem állhat szó- vagy URL-karakter: a `C#1` és a `lap.html#3` marad szöveg. */
const ISSUE_RE = /(^|[^\w./-])([\w.-]+\/[\w.-]+)?#(\d+)\b/g;
export function linkify(s) {
  const text = esc(s), base = DATA.meta.repoUrl;
  if (!base) return text;
  return text.replace(ISSUE_RE, (m, pre, repo, n) =>
    pre + ghLink(`${repo ? 'https://github.com/' + repo : base}/issues/${n}`, `${repo || ''}#${n}`));
}
/* A tárgysor hivatkozásai chipként (`refChips`), a tárgyból kivéve: a
   `Merge pull request #N` és a squash-merge `(#N)` végződése PR, a
   `chore(release): vX.Y.Z` release, minden más `#N` issue. */
const RELEASE_RE = /^(\w+\(release\))!?:\s*(v?\d+\.\d+\.\d+\S*)\s*$/;
export function subjectRefs(s) {
  const refs = [];
  let text = s;
  const rel = s.match(RELEASE_RE);
  if (rel) { refs.push({ kind: 'release', name: rel[2] }); text = rel[1]; }
  text = text
    .replace(/^(Merge pull request) #(\d+)/, (m, pre, n) => { refs.push({ kind: 'pr', n }); return pre; })
    .replace(/\s*\(#(\d+)\)\s*$/, (m, n) => { refs.push({ kind: 'pr', n }); return ''; })
    .replace(ISSUE_RE, (m, pre, repo, n) => { refs.push({ kind: 'issue', n, repo }); return pre; })
    .replace(/\(\s*\)/g, '').replace(/\s{2,}/g, ' ').trim();
  return { text, refs };
}
const REF_TIP = { pr: 'pull request', issue: 'issue', release: 'release' };
function refChips(refs, lc) {
  const base = DATA.meta.repoUrl;
  return refs.map(r => {
    const name = r.kind === 'release' ? r.name : `${r.repo || ''}#${r.n}`;
    const repoUrl = r.repo ? 'https://github.com/' + r.repo : base;
    const href = !repoUrl ? ''
      : r.kind === 'release' ? `${repoUrl}/releases/tag/${encodeURIComponent(r.name)}`
      : `${repoUrl}/${r.kind === 'pr' ? 'pull' : 'issues'}/${r.n}`;
    const tip = esc(`${REF_TIP[r.kind]}: ${name}`);
    // A PR a subjectből jön, tehát beolvasztott: a merged színt viseli (nyitott, zárt nincs).
    const style = r.kind === 'pr' ? '--lc:var(--git-merged);--lc-fg:var(--git-merged)' : lcStyle(lc);
    const attrs = `class="badge ref-${r.kind}" style="${style}" data-tip="${tip}" aria-label="${tip}"`;
    const body = `${icon(r.kind)}<span class="badge-name">${esc(name)}</span>`;
    return href ? `<a ${attrs} href="${href}" target="_blank" rel="noopener">${body}</a>` : `<span ${attrs}>${body}</span>`;
  }).join('');
}
export const commitUrl = c => `${DATA.meta.repoUrl}/commit/${c.sha}`;
export const fileUrl = (c, f) => commitUrl(c) + (f.anchor ? '#diff-' + f.anchor : '');

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
export function wtBadge(w) {
  const lc = w.main ? laneColor(commitBySha(w.head)?.lane || 0) : wtColor(w) || laneColor(0);
  const tip = `${w.main ? 'fő checkout' : 'worktree'}: ${w.path}\n`
    + (w.branch ? `ág: ${w.branch}${distText(w.branch)}`
      : `ág nélkül, HEAD: ${String(w.head || '').slice(0, 7)}${distText('', wtTrack(w))}`);
  const branch = w.branch ? `${icon('branch')}<span class="badge-name">${esc(w.branch)}</span>${distSegs(w.branch)}` : '';
  const body = w.main && branch ? `<span class="synced wt-lead">${icon('mainWorktree')}</span>${branch}`
    : `${icon(w.main ? 'mainWorktree' : 'worktree')}<span class="badge-name">${esc(w.main ? 'main' : w.name)}</span>`
      + `<span class="div"></span>${branch || icon('detached') + distSegs('', wtTrack(w))}`;
  return `<span class="badge ref-branch" style="${lcStyle(lc)}" data-tip="${esc(tip)}" aria-label="${esc(tip)}">${body}</span>`;
}

// A leválasztott HEAD-en az ág-ikon helyén lánc (az ág nélküliség jele), utána „HEAD”.
const REF_ICON = { head: 'branch', branch: 'branch', remote: 'cloud', tag: 'tag', detached: 'detached', stash: 'stash' };
export function badges(c) {
  // A HEAD, az ág és a tag a commit sávjának színét kapja (`--lc`), mint a vonal; a
  // remote chip is: ha van helyi ága, annak a színét (mint az ágválasztóban), különben
  // a pöttyéét, amin áll.
  const lane = laneColor(c.lane);
  const showRemote = remotesOn();
  // A release chipje a tagjét is jelenti: az azonos nevű tag nem kap külön chipet.
  const sref = subjectRefs(c.subject).refs;
  const rel = new Set(sref.filter(r => r.kind === 'release').map(r => r.name));
  return sortRefs(mergedRefs(shownRefs(c.refs))).filter(r => (showRemote || r.kind !== 'remote')
    && !(r.kind === 'tag' && rel.has(r.name))).map(r => {
    const wt = r.worktree && worktrees().find(w => w.slug === r.worktree);
    const linked = wt && !wt.main;
    // A fő checkout HEAD-je üres mappát kap elöl, ha vannak worktree-k (mint a fejléc chipje).
    const mainLead = wt?.main && linkedWts().length > 0;
    const dist = ['tag', 'detached', 'stash'].includes(r.kind) ? '' : r.name;   // tagnek, stash-nek nincs
    // Leválasztott HEAD: az ág helyett a worktree adja a HEAD-commit távolságát (a fő checkouté ref-mező nélkül jön).
    const tr = r.kind === 'detached' ? wtTrack(wt || worktrees().find(w => w.main)) : undefined;
    // Worktree leválasztott HEAD-je: ág nincs — a worktree jele és neve | lánc (az ág-ikon helyén) HEAD.
    const orphan = r.kind === 'detached' && (linked || mainLead);
    const title = (orphan ? `${wt.main ? 'main' : wt.name}: leválasztott HEAD (ág nélkül)`
      : r.kind === 'stash' ? `félretett változások (git stash): ${r.name}`
      : r.kind === 'detached' ? 'leválasztott HEAD (ág nélkül)'
      : (r.kind === 'head' ? 'HEAD → ' : r.kind + ': ') + r.name)
      + (r.remotes.length ? ' = ' + r.remotes.map(o => `${o.name}/${r.name}`).join(', ') : '')
      + (r.default ? '\na remote alapértelmezett ága' : '')
      + (linked ? `\nworktree: ${wt.path}` : '')
      + distText(dist, tr);
    const multi = (DATA.meta.remotes || []).length > 1;
    const remotes = multi && showRemote ? remoteSegs(r.remotes) : '';
    // Worktree-ben kivett ág: elöl a worktree-jel (a fő checkouté csak, ha vannak worktree-k).
    const wtIc = linked ? 'worktree' : mainLead ? 'mainWorktree' : '';
    const wtLead = wtIc ? `<span class="synced wt-lead">${icon(wtIc)}</span>` : '';
    // Egy remote-nál a helyi ág és a remote párja egy helyen: egyetlen felhő-és-ág ikon
    // (az alapágé teli) a branch-ikon és a felhő helyett, a worktree-jel mögött is.
    const synced = showRemote && r.remotes.length && !multi;
    const other = r.worktree && r.worktree !== focusWt()?.slug ? ' other' : '';
    // A csak remote-os chipen a felhő jelzi a remote-ot: egy remote-nál az
    // `origin/` előtag nem kell, többnél a név mondja meg, melyiké.
    const name = r.kind === 'remote' && !multi ? r.name.replace(/^origin\//, '') : r.name;
    const lead = r.kind === 'remote' ? cloudOf(r.default)
      : orphan ? (linked ? icon(wtIc) : wtLead)
      : wtLead + (synced ? icon(syncedIcon(r))
        : REF_ICON[r.kind] ? icon(REF_ICON[r.kind]) : '');
    // A tooltip a saját buborék (`data-tip`), mint az avataré — a natív `title` késik.
    // A hozzáadott worktree csoportja (HEAD-je, leválasztva az ága) a worktree színét
    // kapja: a csonkjáét, a WIP-soráét, vagy a HEAD-jéét (`wtColor`) — mint a fejléc chipje.
    const group = wtOfRef(r);
    const pair = r.kind === 'remote' && DATA.branches.find(b => !b.remote && b.upstream === r.name);
    const lc = ` style="${lcStyle(pair ? branchColor(pair) : (group && wtColor(group)) || lane)}"`;
    return `<span class="badge ref-${r.kind}${other}"${lc} data-tip="${esc(title)}" aria-label="${esc(title)}">`
      // Leválasztott worktree: név | lánc HEAD; a fő checkouté név nélkül (mappa, lánc, HEAD), mint a fejlécen.
      + (orphan ? lead + (linked ? `<span class="badge-name">${esc(wt.name)}</span><span class="div"></span>` : '')
          + `${icon('detached')}<span class="badge-name">HEAD</span>`
        : `${lead}<span class="badge-name">${esc(name)}</span>`)
      + `${distSegs(dist, tr)}${remotes}</span>`;
  }).join('') + refChips(sref, lane);
}
