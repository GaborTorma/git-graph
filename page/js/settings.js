/* ── Beállítások ── a fogaskerék-menü kapcsolói. A megnyitás a repóé (a
   `.git/config`-ban): a session indulásakor magától nyílik a lap, és ha elavult,
   frissül. A publikálás a gépé: Artifact nélküli repóban a session létrehozza.
   A merge-ek összecsukása is a repóé; a lap a `graph_data`-ból már az első rajzolásnál ismeri.
   A git-graph tárolja (`settings` tool); a menü nyitáskor kérdezi le. */
import { icon } from './icons.js';
import { mcpProblem } from './mcp.js';
import { clearOverrides } from './merges.js';
import { makeMenu } from './menu.js';
import { CTX, DATA, MCP_SERVER, REFILTER, SLUG } from './state.js';
import { esc } from './util.js';

const SETTINGS = [
  ['autoOpen', 'Automatikus megnyitás', 'Új session indításakor'],
  ['autoPublish', 'Automatikus publikálás', 'Új projekt/repo esetén'],
  ['collapseMerges', 'Merge-ek összecsukása', 'A beolvasztott commitok a merge alatt'],
];
const settingsBtn = document.getElementById('settingsBtn');
const settingsPop = document.getElementById('settingsPop');
settingsBtn.innerHTML = icon('gear');
let settings = null;                  // a git-graph válasza (null: még nem jött)
function fillSettings(note = '') {
  const focused = settingsPop.contains(document.activeElement) && /** @type {HTMLElement} */ (document.activeElement).dataset.key;
  settingsPop.innerHTML = SETTINGS.map(([key, name, sub]) =>
    `<button type="button" class="option setting" role="menuitemcheckbox" data-keep data-key="${key}"`
    + ` aria-checked="${settings?.[key] ?? true}"${settings ? '' : ' disabled'}>`
    + `<span class="txt"><span class="name">${name}</span><span class="sub">${sub}</span></span>`
    + '<span class="track"></span></button>').join('')
    + (note ? `<p class="menu-note">${esc(note)}</p>` : '');
  if (focused) settingsPop.querySelector(`[data-key="${focused}"]`)?.focus();   // az újraépítés ne vigye el
}
async function callSettings(changes) {
  try {
    settings = await CTX.mcp.callTool(MCP_SERVER, 'settings', { repo: SLUG, ...changes }, { cache: false })
      .then(r => r.payload);
    fillSettings();
  } catch (e) {
    // not_in_manifest: az app a futó szerver tool-listáját csak induláskor kérdezi le
    fillSettings(e?.code === 'not_in_manifest'
      ? 'A Claude app még nem ismeri ezt a beállítást — indítsd újra az appot.' : mcpProblem(e));
  }
}
makeMenu(settingsBtn, settingsPop, o => {
  if (!settings || o.disabled) return;
  const key = o.dataset.key;
  settings = { ...settings, [key]: !settings[key] };     // azonnal vált, a válasz igazítja
  fillSettings();
  // A lista azonnal követi; a merge-enként kézzel nyitott / zárt állapotok törlődnek.
  if (key === 'collapseMerges') {
    DATA.meta.collapseMerges = settings[key];
    clearOverrides();
    document.dispatchEvent(new Event(REFILTER));
  }
  callSettings({ [key]: settings[key] });
}, () => {
  fillSettings();
  callSettings({}).then(() => settingsPop.querySelector('.option:not([disabled])')?.focus());
});
