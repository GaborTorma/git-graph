/* ── Élő frissítés ───────────────────────────────────────────────────────
   A forrás a gépen futó `git-graph --mcp` (a Claude app host-hídján át). Egy
   hívás mindig nyitva áll (`changes`): a szerver akkor válaszol, ha a repó
   állapota vagy az előtérben lévő session megváltozott, különben 50 s után
   üresen. Teljes adatot csak állapotváltozásra kérünk: a lap helyben rajzol
   újra, a nyitott panel, a szűrők és a görgetés megmaradnak. A mért időket a
   lábléc élő-felirata tooltipben mutatja. */
import { fillBranches } from './branches.js';
import { clock } from './dates.js';
import { diffCache, setSource } from './diff.js';
import { rowsEl, scroller } from './dom.js';
import { applyFilters } from './filters.js';
import { hydrate, hydrateFocus } from './hydrate.js';
import { mcpProblem } from './mcp.js';
import { focusWt, setFocusAuto } from './model.js';
import { render } from './rows.js';
import { DATA, setData } from './state.js';
import { esc, ghLink } from './util.js';

const WAIT_S = 50;          // a nyitva tartott hívás leghosszabb várakozása (a host ~50 s-ig tartja, mérve)
const SETTLE_MS = 250;      // megjelenés (session-váltás) után ennyit vár a kérdezéssel
const IDLE_MS = 2000;       // azonnali, változás nélküli válasz után ennyit vár (túlterhelt szerver)
const RETRY_MS = 400;       // átmeneti hiba után ennyi idővel csendben újra
const QUIET_RETRIES = 3;    // ennyi átmeneti hibát nem ír ki
const ARRIVAL_MS = 2000;    // ennyin belül a fókuszváltás az utolsó jelé (a tooltipben)
const foot = document.getElementById('foot');
const liveText = document.getElementById('liveText');
const liveDot = document.getElementById('liveDot');
const versionEl = document.getElementById('version');

/* Adat még nincs (MCP-lap induláskor): az üzenet a sorok helyére is kerül. */
export function notice(text, stale = false) {
  if (!DATA.commits.length) rowsEl.innerHTML = `<p class="empty">${esc(text)}</p>`;
  foot.className = stale ? 'foot stale' : 'foot';
  liveText.textContent = text;
  liveText.title = text;
  liveDot.title = text;
  liveDot.setAttribute('aria-label', stale ? 'Hiba' : 'Kapcsolódás');
  fitFoot();
}

/* A futó git-graph verziója; ha a telepített más, a teendővel együtt — a futó
   `git-graph --mcp` a régi kódot futtatja, amíg az app újra nem indul. */
const PLUGIN_URL = 'https://github.com/GaborTorma/git-graph';   // = plugin.json `repository`
let versionKey = null;
function showVersion(f) {
  // 2 mp-enként hívódik: csak változáskor építi újra (és méri) a láblécet.
  const key = `${f.version}|${f.installed}`;
  if (key === versionKey) return;
  versionKey = key;
  const stale = f.version && f.installed && f.installed !== f.version && !f.version.includes('+');
  versionEl.className = stale ? 'ver warn' : 'ver';
  const name = `<span class="name">${ghLink(PLUGIN_URL, 'Git Graph', 'home', 'A Git Graph a GitHubon')} </span>`;
  versionEl.innerHTML = !f.version ? '' : stale
    ? `${name} v${esc(f.version)} fut, v${esc(f.installed)} telepítve — indítsd újra a Claude appot`
    : `${name} v${esc(f.version)}`;
  fitFoot();
}

/* A verzió csak egészben látszik: ha a „Git Graph” név nem fér ki, csak a
   verziószám marad, ha az sem, semmi. */
const liveEl = document.getElementById('live');
function fitFoot() {
  versionEl.classList.remove('short', 'cut');
  if (versionEl.classList.contains('warn')) return;
  for (const cls of ['short', 'cut']) {
    if (liveEl.scrollWidth <= liveEl.clientWidth) break;
    versionEl.classList.add(cls);
  }
}
new ResizeObserver(fitFoot).observe(document.getElementById('foot'));

export function startLive(src) {
  let since = '', state = null;             // az utolsó válasz tokenje és állapota (az első kör adatot kér)
  let change = '';                          // az utolsó változás: mikor, mennyi idő alatt
  let switched = '', arrival = null;        // az utolsó session-váltás: mi indította, mennyi idő alatt
  let version = null;                       // a szerver verziója, amikor a lap betöltött
  let misses = 0, open = null, resume = null;   // a nyitott hívás megszakítója, a szünet rövidítője
  setSource(src);
  /* Rajzol-e most a lap: rejtett keretben a requestAnimationFrame nem fut. */
  const rendering = () => new Promise(done => {
    requestAnimationFrame(() => done(true));
    setTimeout(() => done(false), 250);
  });
  /* Az új fókusz; true, ha a saját worktree megváltozott (a hívó rajzol újra). */
  function setFocus(focus) {
    const before = focusWt()?.slug;
    setFocusAuto(focus ?? null);
    if (focusWt()?.slug === before) return false;
    const ago = arrival ? performance.now() - arrival.at : Infinity;
    switched = `\nsession-váltás ${clock()}: `
      + (ago < ARRIVAL_MS ? `${arrival.kind} után ${Math.round(ago)} ms` : 'a nyitott hívásra');
    return true;
  }
  /* Egy hívás → válasz → (változásnál adat) → a következő hívás, megállás nélkül. */
  async function follow() {
    for (;;) {
      const ctl = new AbortController();
      open = ctl;
      let pause = 0;
      try {
        const t0 = performance.now();
        const r = await src.changes(since, since ? WAIT_S : 0, ctl.signal);
        // A szerver frissült és újraindult (`restart`): a lap kódja is az övé,
        // újratöltve a betöltő az új `page_code`-ot kéri.
        if (version && r.version && r.version !== version) { location.reload(); return; }
        version = version || r.version;
        const fresh = r.state !== state;
        // A fókusz nem adatváltozás: a lap csak a kiemelést rajzolja újra.
        const moved = setFocus(r.focus);
        if (moved && !fresh) { hydrateFocus(); fillBranches(); render(); }
        if (fresh) {
          const t1 = performance.now();
          setData(await src.data());
          const td = performance.now() - t1;
          for (const [k, v] of diffCache) if (k.startsWith('*uncommitted') || k.startsWith('*staged')) v.stale = true;
          const top = scroller.scrollTop;
          hydrate();
          fillBranches();
          applyFilters();
          scroller.scrollTop = top;
          change = `\nutolsó változás ${clock()}: adat ${Math.round(td)} ms,`
            + ` kirajzolva ${Math.round(performance.now() - t1)} ms alatt`;
        }
        // Azonnali, változás nélküli válasz (a szerver nem várhatott): nem pörgünk.
        if (since && !fresh && !moved && performance.now() - t0 < SETTLE_MS) pause = IDLE_MS;
        since = r.since;
        state = r.state;
        foot.className = 'foot on';
        if (liveText.textContent) {             // az „élő” jelzés a pulzáló zöld pötty
          liveText.textContent = '';
          fitFoot();                            // a hibaüzenet helyén a verzió is elfér
        }
        liveDot.title = `Élő · frissítve ${clock()}` + change + switched;
        liveDot.setAttribute('aria-label', 'Élő');
        showVersion(r);
        misses = 0;
      } catch (e) {
        if (ctl.signal.aborted) continue;       // `wake`: azonnal újra
        // Rejtett keretben a host-híd a hívást azonnal elutasítja (mérve), és az
        // időzítők sem futnak: ez nem hiba — a megjelenés (`wake`) hív újra.
        if (e?.retryable && !(await rendering())) {
          misses = 0;
          pause = IDLE_MS;
        } else if (e?.retryable && ++misses <= QUIET_RETRIES) {
          pause = Math.max(RETRY_MS, e.retryAfterMs || 0);   // átmeneti hiba: csendben, gyorsan újra
        } else {
          notice(mcpProblem(e), true);
          if (!e?.retryable) return;            // magától nem javul: nincs több kör
          pause = Math.max(IDLE_MS, e.retryAfterMs || 0) * 2;
        }
      }
      if (pause) await new Promise(done => { resume = done; setTimeout(done, pause); });
      resume = null;
    }
  }
  /* Session-váltáskor az app ezt az egy keretet átteszi a másik session
     paneljébe. Ha közben más Artifact látszott, a keret rejtve volt, a rejtve
     indított hívás elbukott, és a lap a szünetben áll: a megjelenés után —
     az áthelyezést kivárva — azonnal hív (a kurzor miatt semmi nem veszett el).
     Ha épp nyitott hívás fut, megszakítja; a szerver a sajátját a határidőig
     tartja (a megszakítást nem kapja meg, mérve). */
  let settle = 0;
  function wake(kind, delay = SETTLE_MS) {
    arrival = { kind, at: performance.now() };
    clearTimeout(settle);
    settle = setTimeout(() => (resume ? resume() : open?.abort()), delay);
  }
  /* Rejtve a rajzolás szünetel, megjelenéskor az IntersectionObserver jelez (mérve). */
  new IntersectionObserver(es => { if (es[es.length - 1].isIntersecting) wake('megjelenés'); })
    .observe(document.body);
  follow();
}
