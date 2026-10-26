/* A lap belépője: a betöltő ezt importálja (a `page_code` a modulokat a függőségeik
   sorrendjében blob-URL-re teszi, és az importjaikat azokra írja át). A modulok a saját
   eseménykezelőiket betöltéskor felveszik; amit senki nem importál, az itt töltődik be. */
import { fillBranches } from './branches.js';
import { loadFont } from './font.js';
import { hydrate } from './hydrate.js';
import './keyboard.js';
import { notice, startLive } from './live.js';
import { mcpSource } from './mcp.js';
import { render } from './rows.js';
import './settings.js';
import './theme.js';
import './tip.js';

hydrate();
fillBranches();
render();

notice('Kapcsolódás a gépeden futó git-graph-hoz…');
const src = mcpSource();
startLive(src);
loadFont(src);
