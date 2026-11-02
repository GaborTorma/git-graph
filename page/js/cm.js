/* ── Kóddiff a CodeMirrorral ──
   Minden kóddiffet a vendorolt CodeMirror 6 (`page/vendor/codemirror.min.js`, `scripts/codemirror.sh`)
   rajzol a `@codemirror/merge`-dzsel: egymás alatt `unifiedMergeView` (a régi sorok nem
   szerkeszthető blokkként az új sorok fölött), 1000 px-től `MergeView` (balra a régi, jobbra az új
   oldal). A CodeMirrort a lap az első diffnél kéri a gépen futó git-graph-tól (`page_code`
   `part: 'codemirror'`), és blobból futtatja, mint a Mermaidot. A diffjelölés a merge saját
   diffje (a szerver szabályai: #57); a változatlan rést a `collapseUnchanged` csukja, egy
   kattintásra egyben nyílik.
   Csak olvasható a dupla kattintásig; szerkeszthető csak az Uncommitted sor szöveges fájlja
   (a szerver `editable`-je): a dupla kattintás helyén áll a kurzor, a nézet nem mozdul. A
   mentés automatikus (1 s csend után, ⌘S-re azonnal) a `write_file` toolon át, az ismert lemez-
   állapot hashével; a lemez közbeni változását a lap befésüli (kék villanással), ha a nem
   mentett résszel ütközik, mindkét változatot mutatja, és amíg a Fejlesztő nem választ, nem ír. */
import { icon } from './icons.js';
import { esc } from './util.js';

const WIDE = 1000;           // ettől a szélességtől egymás mellett
const SAVE_MS = 1000;        // ennyi csend után ment
const FLASH_MS = 1600;       // a külső változás kék villanása
const REBASE_MS = 120;       // a WIP-réteg merge-alapja gépelés után ennyivel frissül
/* A merge nézetek alapja `scanLimit: 500`: sok szétszórt változásnál a diff feladja, és egy nagy
   blokkot jelöl. A korlát helyett időkorlát: a 2 MB-os fájl sem akasztja meg a lapot. */
const DIFF_CONFIG = { scanLimit: 1e9, timeout: 1500 };

let lib = null;              // a CodeMirror betöltésének ígérete; hibánál a következő próba újrakéri
export function loadCM(get) {
  lib ??= get().then(({ js }) => new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = URL.createObjectURL(new Blob([js], { type: 'text/javascript' }));
    s.onload = () => resolve(globalThis.CM);
    s.onerror = () => reject(new Error('a CodeMirror nem indult el'));
    document.head.append(s);
  })).catch(e => { lib = null; throw e; });
  return lib;
}

/* A nyelv a kiterjesztésből (a build `lang`-ja szerint); a többi sima szöveg. Minden JSON a
   JSON-elemzővel megy (a kommentes is: a komment hibajelölést kaphat). */
const LANG = {
  py: 'py', pyi: 'py', js: 'js', mjs: 'js', cjs: 'js', jsx: 'jsx', ts: 'ts', mts: 'ts', cts: 'ts', tsx: 'tsx',
  json: 'json', jsonc: 'json', css: 'css', html: 'html', htm: 'html', md: 'md', markdown: 'md', mdx: 'md',
  sh: 'sh', bash: 'sh', zsh: 'sh', yml: 'yaml', yaml: 'yaml', toml: 'toml', swift: 'swift',
};
export function cmLang(path) {
  const name = path.split('/').pop();
  const ext = name.includes('.') ? name.split('.').pop().toLowerCase() : '';
  return LANG[ext] || (name === 'git-graph' ? 'py' : null);
}

/* A Claude kódszínei (page.css `--syn-*`), a Lezer címkéire. */
let shared = null;
function common(CM) {
  if (shared) return shared;
  const t = CM.tags;
  const style = CM.HighlightStyle.define([
    { tag: [t.keyword, t.controlKeyword, t.operatorKeyword, t.definitionKeyword, t.moduleKeyword, t.modifier,
            t.bool, t.null, t.self, t.heading], color: 'var(--syn-kw)' },
    { tag: [t.function(t.variableName), t.function(t.propertyName), t.macroName, t.propertyName,
            t.attributeName], color: 'var(--syn-fn)' },
    { tag: [t.typeName, t.className, t.namespace, t.tagName, t.labelName], color: 'var(--syn-ty)' },
    { tag: [t.string, t.special(t.string), t.regexp, t.character, t.attributeValue, t.url], color: 'var(--syn-st)' },
    { tag: [t.number, t.atom, t.unit], color: 'var(--syn-nu)' },
    { tag: [t.comment, t.lineComment, t.blockComment, t.docComment, t.meta], color: 'var(--syn-cm)', fontStyle: 'italic' },
    { tag: t.strong, fontWeight: 'var(--w-bold)' },
    { tag: t.emphasis, fontStyle: 'italic' },
    { tag: t.invalid, textDecoration: 'underline wavy var(--del)' },
  ]);
  // A külső változás kék villanása: soronként, `FLASH_MS` után magától eltűnik.
  const flash = CM.StateEffect.define();
  const unflash = CM.StateEffect.define();
  const flashField = CM.StateField.define({
    create: () => CM.Decoration.none,
    update(deco, tr) {
      deco = deco.map(tr.changes);
      for (const e of tr.effects) {
        if (e.is(unflash)) deco = CM.Decoration.none;
        if (e.is(flash)) {
          deco = deco.update({ add: e.value.map(pos => CM.Decoration.line({ class: 'cm-flash' }).range(pos)), sort: true });
        }
      }
      return deco;
    },
    provide: f => CM.EditorView.decorations.from(f),
  });
  shared = {
    style: CM.syntaxHighlighting(style),
    phrases: CM.EditorState.phrases.of({ '$ unchanged lines': '$ változatlan sor', Find: 'Keresés', Replace: 'Csere',
      next: 'következő', previous: 'előző', all: 'mind', 'match case': 'kis/nagybetű', regexp: 'regexp',
      'by word': 'egész szó', replace: 'csere', 'replace all': 'mind cseréje', close: 'bezárás' }),
    flash, unflash, flashField,
  };
  return shared;
}

/* ── WIP-réteg ── a saját worktree HEAD-commitjánál a dokumentum a lemez szövege (`d.head`: a HEAD-beli):
   a HEAD → lemez eltérések a merge zöld / piros jelölése fölött; a hozzáadott sor kék (`cm-wipLine`), a
   HEAD-beli változata narancs blokk (`cm-wipDeleted`), rajta az elvetés (a HEAD-beli változatra). */
let wipShared = null;
function wipKit(CM) {
  if (wipShared) return wipShared;
  const setHead = CM.StateEffect.define();
  class WipBlock extends CM.WidgetType {
    constructor(diff, ch, old, head) { super(); Object.assign(this, { diff, ch, old, head }); }
    eq(o) { return o.old === this.old && o.ch.fromB === this.ch.fromB && o.ch.toB === this.ch.toB && o.diff.editable === this.diff.editable; }
    toDOM() {
      const el = document.createElement('div');
      el.className = 'cm-wipDeleted';
      if (this.old != null) for (const line of this.old.split('\n')) el.append(Object.assign(document.createElement('div'), { textContent: line || '\u200b' }));
      if (this.diff.editable) {
        const bar = Object.assign(document.createElement('span'), { className: 'cm-chunkButtons' }), b = rejectButton();
        b.addEventListener('mousedown', e => { e.preventDefault(); this.diff.rejectWip(this.ch, this.head); });
        bar.append(b);
        el.append(bar);
      }
      return el;
    }
    ignoreEvent() { return true; }
  }
  const build = (diff, state, head) => {
    if (head == null) return { head, deco: CM.Decoration.none, chunks: [] };
    const doc = state.doc, a = CM.Text.of(head.split('\n')), ranges = [];
    const chunks = CM.Chunk.build(a, doc, DIFF_CONFIG);
    for (const ch of chunks) {
      // a blokk vége a következő sor eleje (a sorvég a blokké): a HEAD-beli sorok sorvég nélkül
      const old = ch.toA > ch.fromA ? a.sliceString(ch.fromA, ch.toA).replace(/\n$/, '') : null;
      if (old != null || diff.editable) {
        ranges.push(CM.Decoration.widget({ widget: new WipBlock(diff, ch, old, a), block: true, side: -1 })
          .range(doc.lineAt(Math.min(ch.fromB, doc.length)).from));
      }
      if (ch.toB > ch.fromB) {
        for (let n = doc.lineAt(ch.fromB).number, last = doc.lineAt(Math.min(ch.toB - 1, doc.length)).number; n <= last; n++) {
          ranges.push(CM.Decoration.line({ class: 'cm-wipLine' }).range(doc.line(n).from));
        }
      }
    }
    return { head, deco: CM.Decoration.set(ranges, true), chunks };
  };
  const field = diff => CM.StateField.define({
    create: s => build(diff, s, diff.d.head ?? null),
    update(v, tr) {
      for (const e of tr.effects) if (e.is(setHead)) return build(diff, tr.state, e.value);
      return tr.docChanged ? build(diff, tr.state, v.head) : v;
    },
    provide: f => CM.EditorView.decorations.from(f, v => v.deco),
  });
  // A saját változatlan-rés (egymás alatt, WIP-réteggel): a merge `collapseUnchanged`-je csak a commit
  // változásait látja; ez mindkét diffét. Kattintásra a rés egyben nyílik.
  const setGaps = CM.StateEffect.define(), openGap = CM.StateEffect.define();
  class Gap extends CM.WidgetType {
    constructor(n) { super(); this.n = n; }
    eq(o) { return o.n === this.n; }
    toDOM(view) {
      const el = Object.assign(document.createElement('div'), { className: 'cm-collapsedLines', textContent: `${this.n} változatlan sor` });
      el.addEventListener('click', () => view.dispatch({ effects: openGap.of(view.posAtDOM(el)) }));
      return el;
    }
    ignoreEvent(e) { return e instanceof MouseEvent; }
    get estimatedHeight() { return 27; }
  }
  const gaps = CM.StateField.define({
    create: () => CM.Decoration.none,
    update(deco, tr) {
      deco = deco.map(tr.changes);
      for (const e of tr.effects) {
        if (e.is(setGaps)) deco = e.value;
        if (e.is(openGap)) deco = deco.update({ filter: (from, to) => e.value < from || e.value > to });
      }
      return deco;
    },
    provide: f => CM.EditorView.decorations.from(f),
  });
  /* A rések: a merge és a WIP változott soraitól 3 sornyi margóval, legalább 4 sor. */
  const gapSet = (state, wipChunks) => {
    const doc = state.doc, changed = new Uint8Array(doc.lines + 2);
    const mark = (from, to) => {
      for (let n = doc.lineAt(Math.min(from, doc.length)).number, last = doc.lineAt(Math.min(Math.max(from, to - 1), doc.length)).number; n <= last; n++) changed[n] = 1;
    };
    for (const ch of CM.getChunks(state)?.chunks || []) mark(ch.fromB, ch.toB);
    for (const ch of wipChunks) mark(ch.fromB, ch.toB);
    const ranges = [];
    for (let n = 1; n <= doc.lines;) {
      if (changed[n]) { n++; continue; }
      let end = n;
      while (end < doc.lines && !changed[end + 1]) end++;
      const from = n === 1 ? 1 : n + 3, to = end === doc.lines ? end : end - 3;
      if (to - from + 1 >= 4) ranges.push(CM.Decoration.replace({ widget: new Gap(to - from + 1), block: true }).range(doc.line(from).from, doc.line(to).to));
      n = end + 1;
    }
    return CM.Decoration.set(ranges);
  };
  /* A merge alapja: a szülő, rajta a WIP azon blokkjaival, amelyek a commit blokkjait nem érintik —
     így a merge (alap → lemez) csak a commit változását jelöli; az átfedő blokk a szülőé marad. */
  const base = (parent, head, doc) => {
    const p = CM.Text.of(parent.split('\n')), h = CM.Text.of(head.split('\n')), d = CM.Text.of(doc.split('\n'));
    const commit = CM.Chunk.build(p, h, DIFF_CONFIG), changes = [];
    for (const w of CM.Chunk.build(h, d, DIFF_CONFIG)) {
      // a blokk [from, to): a `to` a következő sor eleje (a sorvég a blokké); érintkezés is átfedés
      if (commit.some(c => c.fromB <= w.toA && w.fromA <= c.toB)) continue;
      // a WIP-blokk előtti commit-blokkok eltolása (a szülő → HEAD hosszváltozás)
      let shift = 0;
      for (const c of commit) if (c.toB <= w.fromA) shift += (c.toA - c.fromA) - (c.toB - c.fromB);
      const from = Math.min(w.fromA + shift, p.length), to = Math.min(w.toA + shift, p.length);
      changes.push({ from, to, insert: d.sliceString(w.fromB, Math.min(w.toB, d.length)) });
    }
    return changes.length ? CM.ChangeSet.of(changes, p.length).apply(p).toString() : parent;
  };
  wipShared = { setHead, field, gaps, setGaps, openGap, gapSet, base };
  return wipShared;
}

/* Az éppen szerkesztett diff (egyszerre egy): a máshová kattintás befejezi. */
let editing = null;
document.addEventListener('pointerdown', e => {
  if (editing && !editing.root.contains(/** @type {Node} */ (e.target))) editing.stopEditing();
}, true);
export const editingDiff = () => editing;

/* Egy fájl diffje: `d` — `{ old, new }` (a két oldal teljes szövege, a hiányzó oldal `null`),
   `hash` (az Uncommitted sor lemezállapota), `editable`, `big` (2 MB fölött: a csonkolt hunkok,
   `lines`: a sorszámok). `o`: `{ lang, write(text, base) }`. */
export class CodeDiff {
  constructor(CM, d, o) {
    this.CM = CM;
    this.o = o;
    this.root = document.createElement('div');
    this.root.className = 'cm-diff';
    this.mode = '';
    this.editing = false;
    this.applying = false;           // a saját (nem a Fejlesztő) változtatásunk fut
    this.conflict = null;
    this.timer = 0;
    this.saving = null;
    this.rebaseTimer = 0;
    this.shownOld = null;            // a merge régi oldala (WIP-réteggel nem a szülő: `rebase`)
    this.wipField = null;
    this.edit = new CM.Compartment();
    this.set(d);
    this.root.addEventListener('dblclick', e => this.onDblclick(e));
    this.resize = new ResizeObserver(() => this.layout());
    this.resize.observe(this.root);
  }

  /* A nézet megszűnik (a fájl vagy a commit becsukódott): a méretfigyelő sem épít újra. */
  dispose() {
    this.resize.disconnect();
    this.destroy();
  }

  set(d) {
    this.d = d;
    this.big = Boolean(d.big);
    this.base = d.hash ?? null;      // az utoljára ismert lemezállapot (hash és szöveg)
    this.seen = new Set(d.hash ? [d.hash] : []);   // a már látott / saját írású lemezállapotok
    this.saved = d.new ?? '';
    this.editable = Boolean(d.editable && !d.big);
  }

  /* A nézet a szélességhez: egyoldalú (új / törölt / változatlan) fájlnál mindig egymás alatt. */
  wantMode() {
    const one = this.d.old == null || this.d.new == null || this.d.old === this.d.new || this.d.big;
    return !one && this.root.clientWidth >= WIDE ? 'split' : 'uni';
  }

  layout() {
    if (!this.root.isConnected || !this.root.clientWidth) return;
    const mode = this.wantMode();
    if (mode !== this.mode) this.build(mode);
  }

  /* Az új oldal szövege: szerkesztés közben a dokumentumé. */
  text() { return this.ed ? this.ed.state.doc.toString() : (this.d.new ?? ''); }

  readOnly(on) {
    const CM = this.CM;
    return [CM.EditorState.readOnly.of(on), CM.EditorView.editable.of(!on)];
  }

  extensions(side) {
    const CM = this.CM, c = common(CM), d = this.d;
    const lang = this.o.lang && CM.lang(this.o.lang);
    const lines = d.lines;
    return [
      CM.lineNumbers(lines ? { formatNumber: n => String(lines[n - 1] ?? '') } : {}),
      CM.EditorView.lineWrapping, CM.drawSelection(), c.style, c.phrases, c.flashField, CM.search({ top: true }),
      ...(lang ? [lang] : []),
      ...(side === 'b' ? [CM.history(), CM.keymap.of([
        { key: 'Mod-s', run: () => { this.save(); return true; }, preventDefault: true },
        { key: 'Escape', run: () => { if (!this.editing) return false; this.stopEditing(); return true; } },
        ...CM.historyKeymap, ...CM.searchKeymap, CM.indentWithTab, ...CM.defaultKeymap,
      ]), CM.EditorView.updateListener.of(u => this.onUpdate(u)), this.edit.of(this.readOnly(true))]
        : [CM.keymap.of(CM.searchKeymap), ...this.readOnly(true)]),
    ];
  }

  build(mode) {
    const CM = this.CM, d = this.d;
    const doc = this.ed ? this.ed.state.doc.toString() : (d.new ?? '');
    // WIP-réteggel a merge alapja a szülő a commitot nem érintő WIP-blokkokkal (`wipKit().base`)
    const orig = d.head != null && !d.big ? wipKit(CM).base(d.old ?? '', d.head, doc) : (d.old ?? '');
    this.shownOld = orig;
    const wasEditing = this.editing, head = this.ed?.state.selection.main.head ?? 0;
    this.destroy();
    this.mode = mode;
    // a WIP-réteg (HEAD-commit, lemez szöveg): elvetés csak a WIP-blokkon, a rés a saját (`wipKit`)
    const wip = d.head != null && !d.big ? wipKit(CM) : null;
    this.wipField = wip ? wip.field(this) : null;
    const layer = wip ? [this.wipField] : [];
    // WIP-eltérés nélkül (a lemez a HEAD-beli) a merge rése marad; különben a saját, mindkét diffhez
    const ownGaps = wip && d.head !== doc;
    const collapse = orig !== doc && !d.big && !(wip && d.head !== doc) ? { collapseUnchanged: { margin: 3, minSize: 4 } } : {};
    if (mode === 'split') {
      // egymás mellett az elvetés a két oldal közti gomb: a változásblokk a régi oldalra áll vissza
      const revert = this.editable && !wip ? { revertControls: /** @type {'a-to-b'} */ ('a-to-b'), renderRevertControl: () => {
        const b = rejectButton();
        b.addEventListener('mousedown', () => setTimeout(() => {
          if (!this.editing) this.startEditing(this.ed.state.selection.main.head);
        }));
        return b;
      } } : {};
      this.mv = new CM.MergeView({ a: { doc: orig, extensions: this.extensions('a') },
                                   b: { doc, extensions: [...this.extensions('b'), ...layer] },
                                   parent: this.root, gutter: true, highlightChanges: true, diffConfig: DIFF_CONFIG,
                                   ...collapse, ...revert });
      this.ed = this.mv.b;
      this.ea = this.mv.a;
    } else {
      const controls = this.editable && !wip ? (type, action) => {
        if (type === 'accept') return document.createElement('span');   // az elfogadás stage-elés lenne: nincs
        const b = rejectButton();
        b.onmousedown = e => { action(e); if (!this.editing) this.startEditing(this.ed.state.selection.main.head); };
        return b;
      } : false;
      this.ed = new CM.EditorView({ parent: this.root, state: CM.EditorState.create({ doc, extensions: [
        ...this.extensions('b'),
        CM.unifiedMergeView({ original: orig, gutter: true, highlightChanges: true, syntaxHighlightDeletions: true,
                              mergeControls: controls, diffConfig: DIFF_CONFIG, ...collapse }),
        ...layer, ...(ownGaps ? [wip.gaps] : []),
      ] }) });
      this.ea = null;
      if (ownGaps) this.ed.dispatch({ effects: wip.setGaps.of(wip.gapSet(this.ed.state, this.ed.state.field(this.wipField).chunks)) });
    }
    if (wasEditing) this.startEditing(head);
  }

  destroy() {
    this.mv?.destroy();
    if (!this.mv) this.ed?.destroy();
    this.mv = this.ed = this.ea = null;
    this.root.querySelectorAll('.cm-mergeView, .cm-editor').forEach(e => e.remove());
  }

  /* ── Szerkesztés ── */
  onDblclick(e) {
    if (!this.editable || this.editing || !this.ed) return;
    const at = { x: e.clientX, y: e.clientY };
    let pos;
    if (this.ea?.dom.contains(/** @type {Node} */ (e.target))) {
      // a régi oldal sora: az új oldal megfelelő sorának eleje
      const a = this.ea.posAtCoords(at, false), chunks = this.CM.getChunks(this.ea.state)?.chunks || [];
      let ours = 0, other = 0;
      for (const ch of chunks) {
        if (ch.fromA > a) break;
        if (ch.toA > a) { ours = ch.fromA; other = ch.fromB; break; }
        ours = ch.toA; other = ch.toB;
      }
      pos = this.ed.state.doc.lineAt(Math.min(this.ed.state.doc.length, other + (a - ours))).from;
    } else {
      pos = this.ed.posAtCoords(at, false);
    }
    this.startEditing(pos);
  }

  startEditing(pos) {
    if (!this.editable || !this.ed) return;
    if (editing && editing !== this) editing.stopEditing();
    // a nézet egy pixelt sem mozdul: a görgető ősök helyzete a fókusz után visszaáll
    const keep = [];
    for (let el = this.root.parentElement; el; el = el.parentElement) keep.push([el, el.scrollTop, el.scrollLeft]);
    this.editing = true;
    editing = this;
    this.root.classList.add('editing');
    this.ed.dispatch({ effects: this.edit.reconfigure(this.readOnly(false)),
                       selection: { anchor: Math.max(0, Math.min(pos, this.ed.state.doc.length)) } });
    this.ed.focus();
    for (const [el, top, left] of keep) { el.scrollTop = top; el.scrollLeft = left; }
  }

  stopEditing() {
    if (!this.editing) return;
    this.editing = false;
    if (editing === this) editing = null;
    this.root.classList.remove('editing');
    this.save();
    this.ed?.dispatch({ effects: this.edit.reconfigure(this.readOnly(true)) });
    this.ed?.contentDOM.blur();
  }

  onUpdate(u) {
    if (u.docChanged && this.wipField) {          // a merge alapja követi a dokumentumot (`rebase`)
      clearTimeout(this.rebaseTimer);
      this.rebaseTimer = setTimeout(() => this.rebase(), REBASE_MS);
    }
    if (!u.docChanged || this.applying || !this.editable) return;
    clearTimeout(this.timer);
    if (!this.conflict) this.timer = setTimeout(() => this.save(), SAVE_MS);
  }

  /* A merge régi oldala (`shownOld`) az új alapra: egymás mellett a bal szerkesztő, egymás alatt az
     eredeti dokumentum változik. */
  setOriginal(next) {
    const orig = this.shownOld ?? '';
    if (!this.ed || orig === next) return;
    if (this.ea) this.ea.dispatch({ changes: this.changes(orig, next) });
    else this.ed.dispatch({ effects: this.CM.originalDocChangeEffect(this.ed.state, this.changes(orig, next)) });
    this.shownOld = next;
  }

  /* A WIP-réteg merge-alapja a mostani dokumentumhoz (`wipKit().base`). */
  rebase() {
    if (!this.ed || !this.wipField || this.d.head == null) return;
    this.setOriginal(wipKit(this.CM).base(this.d.old ?? '', this.d.head, this.text()));
  }

  /* A WIP-blokk elvetése: a dokumentum `ch` része a HEAD-beli (`head`) változatra áll vissza; a
     szerkesztés elindul, a mentés a szokásos úton megy. */
  rejectWip(ch, head) {
    if (!this.ed) return;
    if (!this.editing) this.startEditing(this.ed.state.selection.main.head);
    const doc = this.ed.state.doc;
    this.ed.dispatch({ changes: { from: ch.fromB, to: Math.min(ch.toB, doc.length),
                                  insert: head.sliceString(ch.fromA, Math.min(ch.toA, head.length)) } });
  }

  /* A dokumentum a lemezre (`write_file`), az ismert lemezállapot hashével: ha a lemez közben
     változott, a szerver nem ír, hanem a lemez mostani szövegét adja — azt fésüljük be. */
  async save() {
    clearTimeout(this.timer);
    if (!this.editable || this.conflict || !this.ed) return;
    if (this.saving) { await this.saving; return this.save(); }
    const text = this.text();
    if (text === this.saved) return;
    this.saving = (async () => {
      try {
        const r = await this.o.write(text, this.base, this.d.write);
        if (r?.ok) { this.base = r.hash; this.seen.add(r.hash); this.saved = text; this.note(''); }
        else if (r?.conflict) this.external(r.text, r.hash);
      } catch (e) {
        this.note(`A mentés nem sikerült: ${e?.message || e?.code || e}`);
      }
    })();
    await this.saving;
    this.saving = null;
    if (this.text() !== this.saved && !this.conflict) this.timer = setTimeout(() => this.save(), SAVE_MS);
  }

  note(text) {
    let bar = this.root.querySelector(':scope > .cm-note');
    if (!text) { bar?.remove(); return; }
    bar ??= this.root.appendChild(Object.assign(document.createElement('p'), { className: 'diff-note cm-note' }));
    bar.textContent = text;
  }

  /* Saját változtatás a dokumentumban (nem menti, nem a Fejlesztőé). */
  apply(spec) {
    this.applying = true;
    try { this.ed.dispatch(spec); } finally { this.applying = false; }
  }

  /* A változott sorok kék villanása. */
  flash(changes) {
    const c = common(this.CM), doc = this.ed.state.doc, at = new Set();
    changes.iterChangedRanges((_fa, _ta, from, to) => {
      for (let l = doc.lineAt(from).number; l <= doc.lineAt(Math.min(to, doc.length)).number; l++) at.add(doc.line(l).from);
    });
    if (!at.size) return;
    this.ed.dispatch({ effects: c.flash.of([...at].sort((x, y) => x - y)) });
    setTimeout(() => this.ed?.dispatch({ effects: c.unflash.of(null) }), FLASH_MS);
  }

  /* `a` → `b` változásai ChangeSet-ként (`a` hosszára). */
  changes(a, b) {
    const CM = this.CM;
    return CM.ChangeSet.of(CM.diff(a, b).map(ch => ({ from: ch.fromA, to: ch.toA, insert: b.slice(ch.fromB, ch.toB) })), a.length);
  }

  /* Az új oldal a lemezen változott (élő frissítés vagy mentéskori ütközés). */
  external(text, hash) {
    // egy korábbi (pl. a mentés előtt indult) lekérdezés régi állapota nem külső változás
    if (!this.ed || text == null || (hash && this.seen.has(hash))) return;
    if (hash) this.seen.add(hash);
    const mine = this.text(), base = this.saved;
    if (mine === base) {                          // nincs nem mentett változás: a lemezé
      const ch = this.changes(mine, text);
      this.apply({ changes: ch });
      this.base = hash ?? this.base;
      this.saved = text;
      this.d = { ...this.d, new: text };
      this.flash(ch);
      return;
    }
    const ours = this.CM.diff(base, mine), theirs = this.CM.diff(base, text);
    const lines = (s, from, to) => [s.slice(0, from).split('\n').length, s.slice(0, Math.max(from, to)).split('\n').length];
    const clash = theirs.filter(t => ours.some(o => {
      const [a1, a2] = lines(base, t.fromA, t.toA), [b1, b2] = lines(base, o.fromA, o.toA);
      return a1 <= b2 && b1 <= a2;
    }));
    if (clash.length) { this.showConflict(text, hash, clash); return; }
    const mineSet = this.changes(base, mine), theirSet = this.changes(base, text);
    const mapped = theirSet.map(mineSet);
    this.apply({ changes: mapped });
    this.base = hash ?? this.base;
    this.saved = text;
    this.d = { ...this.d, new: text };
    this.flash(mapped);
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.save(), SAVE_MS);   // a saját, nem mentett rész a lemezre
  }

  /* Ütközés: a két változat egymás mellett, két gombbal; amíg nincs választás, nem íródik semmi. */
  showConflict(text, hash, clash) {
    clearTimeout(this.timer);
    this.conflict = { text, hash };
    const mine = this.text(), base = this.saved;
    const ours = this.CM.diff(base, mine);
    const lineSpan = (s, from, to) => {
      const a = s.lastIndexOf('\n', from - 1) + 1, b = s.indexOf('\n', Math.max(from, to - 1));
      return s.slice(a, b < 0 ? s.length : b);
    };
    const parts = clash.map(t => {
      const o = ours.find(x => x.fromA <= Math.max(t.toA, t.fromA + 1) && t.fromA <= Math.max(x.toA, x.fromA + 1)) || t;
      return `<div class="cm-conflict-pair"><div><b>Az enyém</b><pre>${esc(lineSpan(mine, o.fromB, o.toB))}</pre></div>`
        + `<div><b>A lemezen</b><pre>${esc(lineSpan(text, t.fromB, t.toB))}</pre></div></div>`;
    }).join('');
    this.root.querySelector(':scope > .cm-conflict')?.remove();
    const box = document.createElement('div');
    box.className = 'cm-conflict';
    box.innerHTML = '<p>A fájl a lemezen is változott, ugyanott, ahol még nem mentett módosításod van.</p>'
      + parts + '<div class="cm-conflict-btns"><button type="button" class="btn" data-keep="mine">Az enyém marad</button>'
      + '<button type="button" class="btn" data-keep="disk">A lemezen lévőt veszem</button></div>';
    box.addEventListener('click', e => {
      const btn = /** @type {HTMLElement} */ (e.target).closest('[data-keep]');
      if (btn) this.resolve(/** @type {HTMLElement} */ (btn).dataset.keep);
    });
    this.root.prepend(box);
  }

  resolve(keep) {
    const { text, hash } = this.conflict;
    this.conflict = null;
    this.root.querySelector(':scope > .cm-conflict')?.remove();
    this.base = hash;
    this.saved = text;
    if (keep === 'disk') {
      const ch = this.changes(this.text(), text);
      this.apply({ changes: ch });
      this.d = { ...this.d, new: text };
    } else {
      this.save();
    }
  }

  /* Élő frissítés: az új adat (a régi oldal is változhatott — az Uncommitted soron az index). */
  update(d) {
    if (!this.ed) { this.set(d); return; }
    // Csak a csonkolt (2 MB fölötti) nézet ki- és bekapcsolása épít újra; a többi változás helyben
    // (a régi oldal is), szerkesztés közben a kurzor és a mentés sora marad.
    if (Boolean(d.big) !== Boolean(this.d.big)) {
      const keepText = this.editing ? this.text() : null;
      this.set(d);
      if (keepText != null) this.d = { ...this.d, new: keepText };
      this.build(this.wantMode());
      return;
    }
    const CM = this.CM, head = d.head ?? null;
    this.setOriginal(this.wipField && head != null ? wipKit(CM).base(d.old ?? '', head, this.text()) : (d.old ?? ''));
    if ((d.head ?? null) !== (this.d.head ?? null) && this.wipField) {
      this.ed.dispatch({ effects: wipKit(CM).setHead.of(d.head ?? null) });
    }
    this.d = { ...this.d, old: d.old, head: d.head, editable: d.editable, write: d.write ?? this.d.write };
    this.editable = Boolean(d.editable && !d.big);
    if (this.editable) this.external(d.new, d.hash);
    else if ((d.new ?? '') !== this.text()) {
      const ch = this.changes(this.text(), d.new ?? '');
      this.apply({ changes: ch });
      this.d = { ...this.d, new: d.new };
      this.flash(ch);
    }
    this.layout();                      // egyoldalúból kétoldalú lett: szélesen egymás mellett
  }

  /* ── Görgetés ── a nézet egy sora (az új oldalé) a görgető régió tetején. */
  topLine(scroller) {
    if (!this.ed) return 1;
    const y = scroller.getBoundingClientRect().top - this.ed.documentTop;
    if (y <= 0) return 1;
    return this.ed.state.doc.lineAt(this.ed.lineBlockAtHeight(y).from).number;
  }

  /* `offset`: a görgető régió tetején ennyi helyet takar el valami (ragadós fejléc). */
  scrollToLine(n, scroller, offset = 0) {
    if (!this.ed) return;
    const doc = this.ed.state.doc, line = doc.line(Math.max(1, Math.min(n, doc.lines)));
    this.CM.uncollapseUnchanged && this.ed.dispatch({ effects: this.CM.uncollapseUnchanged.of(line.from) });
    if (this.wipField && !this.ea) this.ed.dispatch({ effects: wipKit(this.CM).openGap.of(line.from) });
    requestAnimationFrame(() => {
      if (!this.ed) return;
      const block = this.ed.lineBlockAt(line.from);
      scroller.scrollTop += this.ed.documentTop + block.top - scroller.getBoundingClientRect().top - offset;
    });
  }

  /* Az első változás sora (nincs változás: 1). */
  firstChange() {
    const chunks = this.ed && this.CM.getChunks(this.ed.state)?.chunks;
    return chunks?.length ? this.ed.state.doc.lineAt(Math.min(chunks[0].fromB, this.ed.state.doc.length)).number : 1;
  }
}

/* Az elvetés gombja: ikon, egy sornyi magas, a súgója a felirat. */
function rejectButton() {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'cm-reject';
  b.setAttribute('aria-label', 'Elvetés');
  b.dataset.tip = 'Elvetés';
  b.innerHTML = icon('revert');
  return b;
}

/* A 2 MB fölötti fájl: a csonkolt hunkokból a két oldal szövege és az új oldal sorszámai — a
   merge ebből rajzol, nem szerkeszthető. */
export function fromHunks(d) {
  const old = [], now = [], lines = [];
  for (const h of d.hunks) {
    for (const l of h.lines) {
      if (l.t !== '+') old.push(l.s);
      if (l.t !== '-') { now.push(l.s); lines.push(l.n); }
    }
  }
  return { old: old.join('\n'), new: now.join('\n'), lines, big: true, editable: false };
}
