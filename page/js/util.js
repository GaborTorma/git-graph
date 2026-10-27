/* Apró, állapot nélküli segédek: HTML-escape, GitHub-link, keresőszavak. */

export const menuOpen = () => Boolean(document.querySelector('.menu-pop:not([hidden])'));
export const esc = s => String(s).replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));

/* GitHub-linkek: valódi `<a target="_blank">` — az Artifact keretéből a Claude
   app csak ezt engedi át (mérve: a `window.open` el sem jutott hozzá). Commit
   és fájl csak pusholt commitnál (`pushed`, a Python jelöli): a helyi a
   GitHubon 404 lenne. A fájl-diff horgonyát (`anchor`) is a Python számolja. */
export const ghLink = (href, html, cls = 'gh-link', label = '') =>
  `<a class="${cls}" href="${href}" target="_blank" rel="noopener"${label ? ` aria-label="${esc(label)}" data-tip="${esc(label)}"` : ''}>${html}</a>`;

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

/* A keresőszavak (`queryWords`) kiemelése `<mark>`-kal az elemek szövegében, a keresés
   szabályával: kis- és nagybetű, ékezet nem számít. A HTML (link) érintetlen marad. */
export function markWords(els, words) {
  if (!words.length) return;
  for (const el of els) {
    const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), nodes = [];
    while (walk.nextNode()) nodes.push(/** @type {Text} */ (walk.currentNode));
    for (const node of nodes) {
      // a hajtott szöveg minden karaktere → az eredeti karakter indexe
      const s = node.data, at = [];
      let folded = '';
      for (let i = 0; i < s.length;) {
        const ch = String.fromCodePoint(/** @type {number} */ (s.codePointAt(i))), f = fold(ch);
        for (let k = 0; k < f.length; k++) at.push(i);
        folded += f;
        i += ch.length;
      }
      at.push(s.length);
      const hits = [];
      for (const w of words) {
        for (let p = folded.indexOf(w); p >= 0; p = folded.indexOf(w, p + w.length)) hits.push([at[p], at[p + w.length]]);
      }
      if (!hits.length) continue;
      hits.sort((a, b) => a[0] - b[0]);
      const frag = document.createDocumentFragment();
      let pos = 0;
      for (const [from, to] of hits) {
        if (to <= pos) continue;                         // átfedő találat: az előző már kiemelte
        frag.append(s.slice(pos, Math.max(pos, from)));
        frag.append(Object.assign(document.createElement('mark'), { textContent: s.slice(Math.max(pos, from), to) }));
        pos = to;
      }
      frag.append(s.slice(pos));
      node.replaceWith(frag);
    }
  }
}
