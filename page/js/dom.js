/* A lap állandó elemei: a lista, a gráf, a fix WIP-sáv és a fejléc chipje. */

export const rowsEl = document.getElementById('rows');
export const svg = document.getElementById('lanes');
export const pendingEl = document.getElementById('pending');
export const counter = document.getElementById('counter');
export const scroller = document.querySelector('.scroll');
export const headChip = document.getElementById('headChip');

export const OPEN_PANEL = '.details:not(.folding)';   // a felcsukódó panel már nem számít
