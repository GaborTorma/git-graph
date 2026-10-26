/* ── Téma ── automatikus / világos / sötét, lenyíló menüből; a választás
   nézőnként megmarad (a betöltő is ebből indul, hogy ne villanjon). */
import { icon } from './icons.js';
import { makeMenu } from './menu.js';

const THEME_KEY = 'git-graph:theme';
const THEMES = [
  ['auto', 'Automatikus', '<circle cx="8" cy="8" r="5.5"/><path d="M8 2.5a5.5 5.5 0 0 1 0 11z" fill="currentColor"/>'],
  ['light', 'Világos', '<path class="ic-ag" d="M11.37 8Q11.37 8.67 11.11 9.29Q10.85 9.91 10.39 10.39Q9.91 10.86 9.28 11.11Q8.66 11.37 8 11.37Q7.33 11.37 6.71 11.11Q6.09 10.85 5.61 10.39Q5.14 9.91 4.89 9.28Q4.63 8.66 4.63 8Q4.63 7.33 4.89 6.71Q5.15 6.09 5.61 5.61Q6.09 5.14 6.72 4.89Q7.34 4.63 8 4.63Q8.67 4.63 9.29 4.89Q9.91 5.15 10.39 5.61Q10.86 6.09 11.11 6.72Q11.37 7.34 11.37 8ZM10.23 8Q10.23 7.4 9.93 6.89Q9.62 6.38 9.12 6.07Q8.61 5.77 8 5.77Q7.4 5.77 6.89 6.07Q6.38 6.38 6.07 6.88Q5.77 7.39 5.77 8Q5.77 8.6 6.07 9.11Q6.38 9.62 6.88 9.93Q7.39 10.23 8 10.23Q8.6 10.23 9.11 9.93Q9.62 9.62 9.93 9.12Q10.23 8.61 10.23 8ZM7.43 2Q7.43 1.76 7.59 1.59Q7.76 1.43 8 1.43Q8.24 1.43 8.41 1.59Q8.57 1.76 8.57 2V3.2Q8.57 3.44 8.41 3.61Q8.24 3.77 8 3.77Q7.76 3.77 7.59 3.61Q7.43 3.44 7.43 3.2ZM7.43 12.8Q7.43 12.56 7.59 12.39Q7.76 12.23 8 12.23Q8.24 12.23 8.41 12.39Q8.57 12.56 8.57 12.8V14Q8.57 14.24 8.41 14.41Q8.24 14.57 8 14.57Q7.76 14.57 7.59 14.41Q7.43 14.24 7.43 14ZM14 7.43Q14.24 7.43 14.41 7.59Q14.57 7.76 14.57 8Q14.57 8.24 14.41 8.41Q14.24 8.57 14 8.57H12.8Q12.56 8.57 12.39 8.41Q12.23 8.24 12.23 8Q12.23 7.76 12.39 7.59Q12.56 7.43 12.8 7.43ZM3.2 7.43Q3.44 7.43 3.61 7.59Q3.77 7.76 3.77 8Q3.77 8.24 3.61 8.41Q3.44 8.57 3.2 8.57H2Q1.76 8.57 1.59 8.41Q1.43 8.24 1.43 8Q1.43 7.76 1.59 7.59Q1.76 7.43 2 7.43ZM11.83 3.35Q12 3.19 12.24 3.19Q12.48 3.19 12.65 3.35Q12.81 3.52 12.81 3.75Q12.81 3.99 12.65 4.17L11.8 5.01Q11.63 5.18 11.4 5.18Q11.17 5.18 10.98 5.01Q10.82 4.85 10.82 4.61Q10.82 4.37 10.99 4.2ZM4.2 10.99Q4.37 10.82 4.6 10.82Q4.83 10.82 5.02 10.99Q5.18 11.15 5.18 11.39Q5.18 11.63 5.01 11.8L4.17 12.65Q4 12.81 3.76 12.81Q3.52 12.81 3.35 12.65Q3.19 12.48 3.19 12.25Q3.19 12.01 3.35 11.83ZM12.65 11.83Q12.81 12.02 12.81 12.25Q12.81 12.48 12.65 12.65Q12.48 12.81 12.24 12.81Q12 12.81 11.83 12.65L10.99 11.8Q10.82 11.64 10.82 11.39Q10.82 11.15 10.99 10.99Q11.17 10.82 11.4 10.82Q11.63 10.82 11.8 10.99ZM5.01 4.2Q5.18 4.36 5.18 4.61Q5.18 4.85 5.01 5.01Q4.83 5.18 4.6 5.18Q4.37 5.18 4.2 5.01L3.35 4.17Q3.19 3.98 3.19 3.75Q3.19 3.52 3.35 3.35Q3.52 3.19 3.76 3.19Q4 3.19 4.17 3.35Z"/>'],
  ['dark', 'Sötét', '<path class="ic-ag" d="M7.4 1.86Q7.64 1.85 7.8 1.98Q7.96 2.11 8.01 2.32Q8.06 2.53 7.94 2.74Q7.57 3.31 7.37 3.99Q7.18 4.66 7.18 5.39Q7.18 6.44 7.57 7.36Q7.96 8.27 8.64 8.96Q9.33 9.64 10.25 10.03Q11.16 10.42 12.21 10.42L12.69 10.41Q12.93 10.39 13.1 10.52Q13.26 10.65 13.31 10.86Q13.36 11.08 13.23 11.28Q12.69 12.15 11.88 12.8Q11.07 13.45 10.08 13.81Q9.09 14.17 8 14.17Q6.72 14.17 5.61 13.69Q4.49 13.21 3.64 12.36Q2.79 11.51 2.31 10.39Q1.83 9.27 1.83 8Q1.83 6.79 2.26 5.73Q2.68 4.67 3.44 3.84Q4.2 3.01 5.21 2.49Q6.22 1.98 7.4 1.86ZM7.51 2.99Q6.56 3.09 5.73 3.51Q4.9 3.93 4.29 4.6Q3.67 5.28 3.32 6.14Q2.97 7.01 2.97 8Q2.97 9.04 3.36 9.95Q3.75 10.86 4.45 11.55Q5.14 12.25 6.05 12.64Q6.95 13.03 8 13.03Q8.91 13.03 9.71 12.73Q10.51 12.44 11.16 11.91Q11.81 11.38 12.26 10.67Q12.14 10.87 12.18 11.08Q12.23 11.28 12.4 11.42Q12.57 11.56 12.8 11.54L12.21 11.58Q10.92 11.58 9.81 11.1Q8.69 10.62 7.84 9.77Q6.99 8.92 6.51 7.8Q6.03 6.68 6.03 5.39Q6.03 4.5 6.28 3.66Q6.53 2.83 6.97 2.13Q6.85 2.33 6.89 2.53Q6.93 2.73 7.1 2.87Q7.27 3.01 7.51 2.99Z"/>'],
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
