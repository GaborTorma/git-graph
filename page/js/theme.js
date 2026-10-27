/* ── Téma ── automatikus / világos / sötét, lenyíló menüből; a választás
   nézőnként megmarad (a betöltő is ebből indul, hogy ne villanjon). */
import { icon } from './icons.js';
import { makeMenu } from './menu.js';

const THEME_KEY = 'git-graph:theme';
const THEMES = [
  ['auto', 'Automatikus', '<circle cx="8" cy="8" r="5.5"/><path d="M8 2.5a5.5 5.5 0 0 1 0 11z" fill="currentColor"/>'],
  ['light', 'Világos', '<path class="ic-ag" d="M10.9 8Q10.9 8.59 10.67 9.12Q10.44 9.64 10.04 10.04Q9.64 10.44 9.11 10.67Q8.58 10.9 8 10.9Q7.41 10.9 6.88 10.67Q6.36 10.44 5.96 10.04Q5.56 9.64 5.33 9.11Q5.1 8.58 5.1 8Q5.1 7.41 5.33 6.88Q5.56 6.36 5.96 5.96Q6.36 5.56 6.89 5.33Q7.42 5.1 8 5.1Q8.59 5.1 9.12 5.33Q9.64 5.56 10.04 5.96Q10.44 6.36 10.67 6.89Q10.9 7.42 10.9 8ZM9.71 8Q9.71 7.54 9.47 7.15Q9.24 6.76 8.85 6.53Q8.46 6.29 8 6.29Q7.54 6.29 7.15 6.53Q6.76 6.76 6.53 7.15Q6.29 7.54 6.29 8Q6.29 8.46 6.53 8.85Q6.76 9.24 7.15 9.47Q7.54 9.71 8 9.71Q8.46 9.71 8.85 9.47Q9.24 9.24 9.47 8.85Q9.71 8.46 9.71 8ZM12.9 8.59Q12.65 8.59 12.48 8.42Q12.3 8.25 12.3 8Q12.3 7.76 12.48 7.58Q12.65 7.41 12.9 7.41H13.9Q14.15 7.41 14.32 7.58Q14.5 7.75 14.5 8Q14.5 8.24 14.32 8.42Q14.15 8.59 13.9 8.59ZM11.04 11.88Q10.87 11.72 10.87 11.47Q10.87 11.21 11.05 11.05Q11.21 10.87 11.46 10.87Q11.71 10.87 11.88 11.04L12.59 11.75Q12.77 11.91 12.77 12.16Q12.77 12.42 12.6 12.58Q12.42 12.76 12.17 12.76Q11.93 12.76 11.75 12.59ZM7.41 12.9Q7.41 12.65 7.58 12.48Q7.75 12.3 8 12.3Q8.24 12.3 8.42 12.48Q8.59 12.65 8.59 12.9V13.9Q8.59 14.15 8.42 14.32Q8.25 14.5 8 14.5Q7.76 14.5 7.58 14.32Q7.41 14.15 7.41 13.9ZM4.12 11.04Q4.28 10.87 4.53 10.87Q4.79 10.87 4.95 11.05Q5.13 11.21 5.13 11.46Q5.13 11.71 4.96 11.88L4.25 12.59Q4.06 12.76 3.82 12.76Q3.58 12.76 3.4 12.58Q3.23 12.42 3.23 12.17Q3.23 11.92 3.41 11.75ZM3.1 7.41Q3.35 7.41 3.52 7.58Q3.7 7.75 3.7 8Q3.7 8.24 3.52 8.42Q3.35 8.59 3.1 8.59H2.1Q1.85 8.59 1.68 8.42Q1.5 8.25 1.5 8Q1.5 7.76 1.68 7.58Q1.85 7.41 2.1 7.41ZM4.96 4.12Q5.13 4.28 5.13 4.53Q5.13 4.79 4.95 4.95Q4.79 5.13 4.54 5.13Q4.29 5.13 4.12 4.96L3.41 4.25Q3.23 4.09 3.23 3.84Q3.23 3.58 3.4 3.42Q3.58 3.24 3.83 3.24Q4.07 3.24 4.25 3.41ZM8.59 3.1Q8.59 3.35 8.42 3.52Q8.25 3.7 8 3.7Q7.76 3.7 7.58 3.52Q7.41 3.35 7.41 3.1V2.1Q7.41 1.85 7.58 1.68Q7.75 1.5 8 1.5Q8.24 1.5 8.42 1.68Q8.59 1.85 8.59 2.1ZM11.88 4.96Q11.72 5.13 11.47 5.13Q11.21 5.13 11.05 4.95Q10.87 4.79 10.87 4.54Q10.87 4.29 11.04 4.12L11.75 3.41Q11.94 3.24 12.18 3.24Q12.42 3.24 12.6 3.42Q12.77 3.58 12.77 3.83Q12.77 4.08 12.59 4.25Z"/>'],
  ['dark', 'Sötét', '<path class="ic-ag" d="M2.76 5.77Q3.2 4.71 4.02 3.93Q4.84 3.14 5.89 2.72Q6.93 2.3 8.1 2.31Q8.32 2.31 8.47 2.44Q8.61 2.57 8.66 2.75Q8.71 2.92 8.66 3.1Q8.61 3.28 8.42 3.4Q7.65 3.91 7.29 4.75Q6.94 5.6 7.12 6.5Q7.24 7.1 7.57 7.6Q7.9 8.1 8.4 8.43Q8.9 8.76 9.5 8.89Q10.1 9.02 10.69 8.89Q11.28 8.76 11.77 8.43Q12.27 8.11 12.6 7.58Q12.73 7.39 12.91 7.34Q13.09 7.29 13.27 7.34Q13.45 7.39 13.57 7.53Q13.7 7.68 13.7 7.9Q13.71 9.07 13.29 10.11Q12.86 11.16 12.08 11.98Q11.29 12.8 10.23 13.24Q9.16 13.7 8.03 13.7Q6.89 13.7 5.84 13.27Q4.79 12.84 3.97 12.03Q3.15 11.21 2.73 10.16Q2.31 9.11 2.31 7.98Q2.31 6.84 2.76 5.77ZM3.86 6.24Q3.5 7.08 3.5 7.98Q3.49 8.87 3.83 9.71Q4.17 10.54 4.81 11.19Q5.46 11.84 6.3 12.18Q7.13 12.52 8.02 12.51Q8.92 12.5 9.76 12.15Q10.6 11.78 11.22 11.14Q11.85 10.5 12.18 9.67Q12.52 8.84 12.5 7.92Q12.52 8.15 12.64 8.29Q12.77 8.43 12.94 8.48Q13.11 8.54 13.29 8.48Q13.47 8.43 13.59 8.24Q13.13 8.95 12.43 9.42Q11.73 9.88 10.91 10.04Q10.1 10.2 9.27 10.04Q8.43 9.88 7.74 9.42Q7.05 8.96 6.58 8.26Q6.12 7.57 5.96 6.73Q5.79 5.89 5.96 5.08Q6.12 4.27 6.59 3.58Q7.05 2.88 7.76 2.41Q7.57 2.53 7.52 2.71Q7.46 2.89 7.52 3.06Q7.57 3.23 7.71 3.37Q7.85 3.5 8.08 3.5Q7.16 3.48 6.33 3.82Q5.5 4.15 4.86 4.78Q4.22 5.4 3.86 6.24Z"/>'],
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
  themeBtn.dataset.tip = `Téma: ${label.toLowerCase()}`;
  themePop.innerHTML = THEMES.map(([value, name, path]) =>
    `<button type="button" class="option with-icon" role="option" data-value="${value}" aria-selected="${value === mode}">`
    + (value === 'auto' ? `<svg class="ic" viewBox="0 0 16 16" aria-hidden="true">${path}</svg>` : icon(value, 'ic', 'md'))
    + `<span class="name">${name}</span>${icon('check', 'ic ck', 'md')}</button>`).join('');
  try { localStorage.setItem(THEME_KEY, mode); } catch { /* privát ablak: nem baj */ }
}
makeMenu(themeBtn, themePop, o => setTheme(o.dataset.value));
setTheme((() => { try { return localStorage.getItem(THEME_KEY) || 'auto'; } catch { return 'auto'; } })());
