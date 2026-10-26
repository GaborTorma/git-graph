/* A lap betűi: az Anthropic Sans és Mono (a Claude app betűi) az Artifact keretében nincsenek
   meg, külső fontot pedig a CSP nem enged. A bájtjaikat a gépen futó git-graph adja (`page_code`
   `part: "font"`, `"font-mono"`, base64), a lap `FontFace`-ként regisztrálja — ez nem fetch.
   Betöltés után a szöveg szélessége változik: a fejléc és a sorok elrendezése újramérődik. Ha
   nem jön, marad a rendszerfont. */
import { fitChrome } from './layout.js';
import { render } from './rows.js';

/** @type {[family: string, part: string, weight: string][]} */
const FONTS = [['Anthropic Sans', 'font', '100 900'], ['Anthropic Mono', 'font-mono', '300 800']];

async function face(src, [family, part, weight]) {
  const { woff2 } = await src.font(part);
  const bytes = Uint8Array.from(atob(woff2), ch => ch.charCodeAt(0));
  document.fonts.add(await new FontFace(family, bytes.buffer, { weight, style: 'normal' }).load());
}

export async function loadFont(src) {
  // egymástól függetlenül: amelyik nem jön (régebbi szerver vagy hiba), az marad rendszerfont
  const loaded = await Promise.allSettled(FONTS.map(f => face(src, f)));
  if (!loaded.some(r => r.status === 'fulfilled')) return;
  fitChrome();
  render();
}
