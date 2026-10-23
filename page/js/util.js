/* Apró, állapot nélküli segédek: HTML-escape, GitHub-link, keresőszavak. */

export const menuOpen = () => Boolean(document.querySelector('.menu-pop:not([hidden])'));
export const esc = s => String(s).replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));

/* GitHub-linkek: valódi `<a target="_blank">` — az Artifact keretéből a Claude
   app csak ezt engedi át (mérve: a `window.open` el sem jutott hozzá). Commit
   és fájl csak pusholt commitnál (`pushed`, a Python jelöli): a helyi a
   GitHubon 404 lenne. A fájl-diff horgonyát (`anchor`) is a Python számolja. */
export const ghLink = (href, html, cls = 'gh-link', label = '') =>
  `<a class="${cls}" href="${href}" target="_blank" rel="noopener"${label ? ` aria-label="${esc(label)}" title="${esc(label)}"` : ''}>${html}</a>`;

/* Bájtméret 1024-es alappal: B alatt tizedes nélkül, KB / MB egy tizedessel, tizedesvesszővel
   (ami KB-ban 1024,0-ra kerekedne, már MB). */
export const fmtBytes = n => n < 1024 ? `${n} B` : n < 1048525 ? `${(n / 1024).toFixed(1).replace('.', ',')} KB`
  : `${(n / 1048576).toFixed(1).replace('.', ',')} MB`;

/* Keresőszavak: kis- és nagybetű, ékezet nem számít. */
// A sor fájlszáma: az összevont mappa (`count`) a fájljaival, a le nem küldöttek (`more`) is.
export const fileCount = st => st.files.reduce((n, f) => n + (f.count || 1), 0) + (st.more || 0);
export const fmtInt = n => n.toLocaleString('hu-HU');
export const fold = s => String(s).toLowerCase().normalize('NFD').replace(/\p{M}/gu, '');
export const queryWords = s => fold(s).split(/\s+/).filter(Boolean);
