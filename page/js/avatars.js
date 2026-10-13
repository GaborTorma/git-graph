/* A szerzők avatarjai egy közös stíluslapban. */
import { DATA } from './state.js';

/* Az avatarok (data URI, néhány KB) szerzőnként egyszer kerülnek a lapra, egy
   stíluslapba (`.av<n>` háttérkép); a sor csak az osztályt kapja — különben
   minden sor újra beágyazná a képet, és a render ezt sokszor újraépítené. */
const avatarStyle = document.head.appendChild(document.createElement('style'));
export let avatarClass = new Map();          // e-mail → osztálynév
export function hydrateAvatars() {
  const entries = Object.entries(DATA.avatars || {});
  avatarClass = new Map(entries.map(([email], i) => [email, `av${i}`]));
  avatarStyle.textContent = entries
    .map(([, url], i) => `.av${i}{background-image:url("${url.replace(/["\\\n]/g, '')}")}`).join('\n');
}
export const avatarOf = c => DATA.avatars?.[c.email];
