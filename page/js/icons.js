/* ── Ikonok ── stroke-os, 16×16-os rácson; a CSS `.ic` színezi. */
import { DATA } from './state.js';

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
  // release: csomag (doboz, fedéllel)
  release: '<path d="M2.5 5 8 2.5 13.5 5v6L8 13.5 2.5 11z"/><path d="M2.5 5 8 7.5 13.5 5M8 7.5v6"/>',
  // a GitHub-jel (Octicons mark-github, MIT): telt, nem vonalas
  github: '<path fill="currentColor" stroke="none" d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"/>',
  copy: '<rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 5.5V3.5a1 1 0 0 0-1-1h-6a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2"/>',
  check: '<path d="m3.5 8.5 3 3 6-7"/>',
  file: '<path d="M4 1.5h5l3.5 3.5v9.5H4z"/><path d="M9 1.5V5h3.5"/>',
  chev: '<path d="M6.5 4.5 10 8l-3.5 3.5"/>',
  // Markdown-diff nézetváltó: nyers forrás, illetve renderelt szöveg
  code: '<path d="M5.5 4.5 2 8l3.5 3.5M10.5 4.5 14 8l-3.5 3.5"/>',
  text: '<path d="M2.5 3.5h11M2.5 6.5h11M2.5 9.5h11M2.5 12.5h7"/>',
  // SVG-diff nézetváltó: a kép (keret, hegy, nap)
  image: '<rect x="2" y="2.5" width="12" height="11" rx="1.5"/><path d="m2.5 12 3.5-4 3 3 1.5-1.5 3 2.5"/><circle cx="10.5" cy="5.75" r="1.25"/>',
  // stash: archiváló doboz, fedéllel és fogantyúval — a stash chipjén
  stash: '<rect x="2" y="3" width="12" height="3.25" rx=".75"/><path d="M3 6.25v6.25a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V6.25M6.5 9h3"/>',
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
  // beállítások: fogaskerék (Lucide settings, ISC), 24-es rácsról lekicsinyítve, a vonal 1,5 marad
  gear: '<g transform="scale(.6667)" stroke-width="2.25"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></g>',
  detached: '<path d="M6.5 9.5 4.8 11.2a2 2 0 0 1-2.8-2.8L3.7 6.7M9.5 6.5l1.7-1.7a2 2 0 0 1 2.8 2.8l-1.7 1.7M5.5 2.5V4M2.5 5.5H4M10.5 13.5V12M13.5 10.5H12"/>',
};
export const icon = (name, cls = 'ic') => `<svg class="${cls}" viewBox="0 0 16 16" aria-hidden="true">${ICONS[name]}</svg>`;
// Fájltípus-ikon: a git-graph a fájlhoz rendelt Catppuccin-ikon SVG-jét adja
// (`fileIcons`, a színei a lap `--ic-*` tokenjei); ha a készlet hiányzik, az általános ikon.
export const fileIcon = f => {
  const svg = DATA.fileIcons?.[f.icon];
  return svg ? svg.replace('<svg', '<svg class="fic" aria-hidden="true"') : icon('file', 'ic fic');
};

export const tinted = (name, color) => `<svg class="ic" style="color:${color}" viewBox="0 0 16 16" aria-hidden="true">${ICONS[name]}</svg>`;
