/* ── Fájl-diff ───────────────────────────────────────────────────────────────
   A diffet a lap lustán kéri, fájlonként (a file_diff toollal) —
   a teljes adatban nincs benne. A commitok diffje nem változik, gyorstárazzuk;
   az Uncommitted soré adatcserekor elavul (`stale`): a régi látszik, amíg az
   új meg nem jön, így a 2 mp-es frissítés nem villog. */
import { grow, shrink } from './anim.js';
import { diffHtml } from './diff-html.js';
import { drawGraph } from './graph.js';
import { icon } from './icons.js';
import { mdDiffHtml, syncRows } from './md-diff.js';
import { refitMermaid, renderMermaid } from './mermaid.js';
import { revealCommit, revealFile } from './panel.js';
import { expanded } from './state.js';
import { langOf } from './syntax.js';
import { esc } from './util.js';

/* A markdown side-by-side sormagasságai (`syncRows`) a szélességtől függnek:
   dobozonként egy méretfigyelő, csak szélességváltozásra (a magasságot a
   szinkron maga is változtatja). A gráfot a sorok figyelője rajzolja újra. */
const watched = new WeakSet();
function watchWidth(box) {
  if (watched.has(box)) return;
  watched.add(box);
  let width = box.clientWidth;
  new ResizeObserver(() => {
    if (box.clientWidth !== width) { width = box.clientWidth; refitMermaid(box); syncRows(box); }
  }).observe(box);
}

export const openFiles = new Set();   // sha + '\n' + út
export const diffCache = new Map();   // ugyanígy kulcsolva → { data, stale }
let SRC = null;                // az élő adatforrás (startLive állítja); az appon kívül nincs
export const setSource = src => { SRC = src; };

/* `reveal`: a megnőtt panelt a nézetbe hozza — `true`: a commitot és a
   fájlt (felhasználói nyitás), `'commit'`: csak a commitot, `false`: semmit. */
/** @param {boolean | 'commit'} [reveal] */
export function toggleFile(fileEl, sha, on, reveal = true) {
  const key = sha + '\n' + fileEl.dataset.path;
  const box = fileEl.nextElementSibling;
  fileEl.setAttribute('aria-expanded', on ? 'true' : 'false');
  if (!on) {
    openFiles.delete(key);
    shrink(box, () => { box.hidden = true; drawGraph(); revealCommit(fileEl.closest('.details'), true); });
    return;
  }
  openFiles.add(key);

  const lang = langOf(fileEl.dataset.path);
  // Felhasználói nyitásnál a diff (és vele a panel) animálva nő; a nézetbe
  // hozás a végső méretből számol.
  const show = html => {
    if (!fileEl.isConnected || fileEl.getAttribute('aria-expanded') !== 'true') return;
    const fill = () => {
      box.hidden = false;
      box.innerHTML = html;
      syncRows(box);
      watchWidth(box);
      renderMermaid(box, () => SRC.mermaid());
    };
    const settle = () => {
      if (reveal) revealCommit(fileEl.closest('.details'), true);
      if (reveal === true) revealFile(fileEl);
    };
    if (reveal === true) { grow(box, fill, settle); return; }
    fill();
    settle();
    drawGraph();
  };
  // Markdown-fájl: renderelve a teljes fájlból (`full`, külön gyorstárazva), a
  // kapcsolóval nyersen — a kapcsoló mindkét nézet fölött ott van.
  const md = lang === 'md', full = md && !mdRaw;
  const cacheKey = full ? key + '\nfull' : key;
  const render = d => (md ? mdModeHtml() : '') + (full ? mdDiffHtml(d) : diffHtml(d, lang));
  const cached = diffCache.get(cacheKey);
  if (!SRC) return show('<p class="diff-note">A diff csak élő nézetben látszik '
    + '(az Artifact a Claude appban).</p>');
  show(cached ? render(cached.data) : '<p class="diff-note loading">Betöltés…</p>');
  if (cached && !cached.stale) return;
  SRC.diff(sha, fileEl.dataset.path, full).then(
    d => {
      // Élő frissítéskor a régi adat már kirajzolva: ha nem változott, nem rajzoljuk újra.
      const same = cached && JSON.stringify(cached.data) === JSON.stringify(d);
      diffCache.set(cacheKey, { data: d });
      if (!same && full === (md && !mdRaw)) show(render(d));   // közben átváltott: a másik nézet a soros
    },
    e => { if (!cached) show(`<p class="diff-note">A diff nem tölthető be: ${esc(
      e?.message || e?.code || e)}</p>`); });
}

const MD_RAW_KEY = 'git-graph:mdRaw';
export let mdRaw = (() => { try { return localStorage.getItem(MD_RAW_KEY) === '1'; } catch { return false; } })();

export function setMdRaw(raw) {
  mdRaw = raw;
  try { localStorage.setItem(MD_RAW_KEY, raw ? '1' : '0'); } catch { /* privát ablak: nem baj */ }
  document.querySelectorAll('.details .file[aria-expanded="true"]').forEach(f => {
    if (langOf(f.dataset.path) === 'md') toggleFile(f, expanded, true, 'commit');
  });
}

const mdModeHtml = () => `<button class="mini md-mode" data-md-mode title="${
  mdRaw ? 'Renderelt nézet' : 'Nyers diff'}">${icon(mdRaw ? 'text' : 'code')}</button>`;
