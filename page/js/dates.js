/* Dátum és idő budapesti idő szerint, magyar formában. */

const TZ = 'Europe/Budapest';
const fmtParts = (iso, opts) => Object.fromEntries(new Intl.DateTimeFormat('hu-HU',
  { timeZone: TZ, ...opts }).formatToParts(new Date(iso)).map(p => [p.type, p.value]));
export const dayKey = iso => { const p = fmtParts(iso, { year: 'numeric', month: '2-digit', day: '2-digit' });
  return `${p.year}-${p.month}-${p.day}`; };
export const fmtTime = iso => { const p = fmtParts(iso, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
  return `${p.hour}:${p.minute}`; };
export const clock = () => { const p = fmtParts(new Date(),
  { hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' });
  return `${p.hour}:${p.minute}:${p.second}`; };
/* Az idő a napjával, ha nem mai (a rögzített sávnak nincs napfejléce): `tegnap 23:30`, `okt. 3. 23:30`. */
export function pinnedTime(iso) {
  if (dayKey(iso) === dayKey(new Date())) return fmtTime(iso);
  if (dayKey(iso) === dayKey(new Date(Date.now() - 864e5))) return `tegnap ${fmtTime(iso)}`;
  const p = fmtParts(iso, { month: 'short', day: 'numeric' });
  return `${p.month} ${p.day}. ${fmtTime(iso)}`;
}
export const fmtDate = iso =>`${dayKey(iso).replaceAll('-', '.')}. ${fmtTime(iso)}`;
export function dayLabel(key) {
  const [y, m, d] = key.split('-').map(Number);
  const long = new Intl.DateTimeFormat('hu-HU', { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' })
    .format(new Date(Date.UTC(y, m - 1, d)));
  const yesterday = dayKey(new Date(Date.now() - 864e5));
  return key === dayKey(new Date()) ? `Ma · ${long}` : key === yesterday ? `Tegnap · ${long}` : long;
}
