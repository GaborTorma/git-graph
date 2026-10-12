/* ── Téma ── automatikus / világos / sötét, lenyíló menüből; a választás
   nézőnként megmarad (a betöltő is ebből indul, hogy ne villanjon). */
import { icon } from './icons.js';
import { makeMenu } from './menu.js';

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
