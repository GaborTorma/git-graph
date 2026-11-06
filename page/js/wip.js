/* ── WIP-réteg ── a saját worktree HEAD-commitjának kóddiffjében (`cm.js`, `CodeDiff`) a HEAD → lemez
   eltérések második rétegként: a CodeMirror-bővítmények (állapotmezők, dekorációk, a saját változatlan-rés,
   a bal oldal térközei) és a blokkok számítása. A `CodeDiff` köti be őket; a modul a `cm.js`-t nem importálja. */
import { icon } from './icons.js';

/* A merge nézetek alapja `scanLimit: 500`: sok szétszórt változásnál a diff feladja, és egy nagy
   blokkot jelöl. A korlát helyett időkorlát: a 2 MB-os fájl sem akasztja meg a lapot. */
export const DIFF_CONFIG = { scanLimit: 1e9, timeout: 1500 };

/* A saját worktree HEAD-commitjánál a dokumentum a lemez szövege (`d.head`: a HEAD-beli):
   a HEAD → lemez eltérések a merge zöld / piros jelölése fölött; a hozzáadott sor kék (`cm-wipLine`), a
   HEAD-beli változata narancs (`cm-wipDeleted` blokk; egymás mellett, ha a szülőben is megvan, a bal
   oldal sora: `cm-wipDelLine`), rajta az elvetés (a HEAD-beli változatra). Szókiemelés és sávjel is. */
let wipShared = null;
export function wipKit(CM) {
  if (wipShared) return wipShared;
  const setHead = CM.StateEffect.define();
  const marker = cls => new (class extends CM.GutterMarker { constructor() { super(); this.elementClass = cls; } })();
  const addGutter = marker('cm-wipAddGutter'), delGutter = marker('cm-wipDelGutter');
  /* A narancs sor szövege a szókiemelésekkel (`marks`: [from, to] a soron belül). */
  const lineEl = (text, marks, tag = 'div') => {
    const el = document.createElement(tag);
    let at = 0;
    for (const [f, t] of marks) {
      el.append(text.slice(at, f), Object.assign(document.createElement('span'), { className: 'cm-wipDelText', textContent: text.slice(f, t) }));
      at = t;
    }
    el.append(text.slice(at) || (at ? '' : '​'));
    return el;
  };
  const rejectBar = (diff, ch, head) => {
    const bar = Object.assign(document.createElement('span'), { className: 'cm-chunkButtons' }), b = rejectButton();
    b.addEventListener('mousedown', e => { e.preventDefault(); diff.rejectWip(ch, head); });
    bar.append(b);
    return bar;
  };
  class WipBlock extends CM.WidgetType {
    constructor(diff, ch, old, head) { super(); Object.assign(this, { diff, ch, old, head }); }
    eq(o) {
      return JSON.stringify(o.old) === JSON.stringify(this.old) && o.ch.fromB === this.ch.fromB && o.ch.toB === this.ch.toB
        && o.diff.editable === this.diff.editable;
    }
    toDOM() {
      const el = document.createElement('div');
      el.className = 'cm-wipDeleted';
      for (const l of this.old) el.append(lineEl(l.text, l.marks));
      if (this.diff.editable) el.append(rejectBar(this.diff, this.ch, this.head));
      return el;
    }
    ignoreEvent() { return true; }
  }
  // egymás mellett a bal oldal narancs sorának elvetése (a sor elején, a gomb a jobb szélen)
  class RejectMark extends CM.WidgetType {
    constructor(diff, ch, head) { super(); Object.assign(this, { diff, ch, head }); }
    eq(o) { return o.ch.fromB === this.ch.fromB && o.ch.toB === this.ch.toB; }
    toDOM() { return rejectBar(this.diff, this.ch, this.head); }
    ignoreEvent() { return true; }
  }
  /* A WIP blokkjai (HEAD → lemez) soronként: a karakteres diff egy beszúrt sort néha a szomszéd változatlan
     sorral együtt jelöl (Enter egy sor végén: a következő sor narancs és kék is); a blokk két végéről a
     mindkét oldalon azonos sorok lekerülnek, a szókiemelés (`changes`) a maradékra újra számolódik. */
  const lineChunks = (a, b) => CM.Chunk.build(a, b, DIFF_CONFIG).map(ch => {
    let { fromA, toA, fromB, toB } = ch;
    const lines = (doc, from, to) => {
      const out = [];
      for (let pos = from; pos < to && pos <= doc.length;) { const l = doc.lineAt(pos); out.push(l); pos = l.to + 1; }
      return out;
    };
    const la = lines(a, fromA, toA), lb = lines(b, fromB, toB);
    let i = 0, j = 0;
    while (i < la.length && i < lb.length && la[i].text === lb[i].text) i++;
    while (j < la.length - i && j < lb.length - i && la[la.length - 1 - j].text === lb[lb.length - 1 - j].text) j++;
    if (!i && !j) return ch;
    if (i) { fromA = i < la.length ? la[i].from : toA; fromB = i < lb.length ? lb[i].from : toB; }
    if (j) { toA = la[la.length - j].from; toB = lb[lb.length - j].from; }
    fromA = Math.min(fromA, toA);
    fromB = Math.min(fromB, toB);
    const changes = CM.diff(a.sliceString(fromA, Math.min(toA, a.length)), b.sliceString(fromB, Math.min(toB, b.length)));
    return { fromA, toA, fromB, toB, changes };
  }).filter(ch => ch.toA > ch.fromA || ch.toB > ch.fromB);
  /* A HEAD sora (`from`: a sor eleje) a szülőben: a pozíciója ott, vagy -1, ha a commit hozta. */
  const inParent = (commit, from) => {
    let shift = 0;
    for (const c of commit) {
      if (c.fromB <= from && from < c.toB) return -1;
      if (c.toB <= from) shift += (c.toA - c.fromA) - (c.toB - c.fromB);
    }
    return from + shift;
  };
  const build = (diff, state, head) => {
    const none = { head, deco: CM.Decoration.none, gutter: CM.RangeSet.empty, chunks: [], blocks: [], aLines: [] };
    if (head == null) return none;
    const doc = state.doc, a = CM.Text.of(head.split('\n')), ranges = [], gutter = [], blocks = [], aLines = [];
    const chunks = lineChunks(a, doc);
    const commit = diff.split ? diff.commitChunks(head) : null;
    for (const ch of chunks) {
      // a HEAD-beli sorok szókiemeléssel; egymás mellett a szülőben is meglévők a bal oldalra kerülnek
      const old = [];
      for (let pos = ch.fromA; pos < ch.toA && pos <= a.length;) {
        const line = a.lineAt(pos);
        const marks = ch.changes.map(c => [Math.max(ch.fromA + c.fromA, line.from) - line.from, Math.min(ch.fromA + c.toA, line.to) - line.from])
          .filter(([f, t]) => t > f);
        const p = commit ? inParent(commit, line.from) : -1;
        if (p >= 0) aLines.push({ pos: p, marks, reject: aLines.at(-1)?.ch === ch ? null : ch, ch });
        else old.push({ text: line.text, marks });
        pos = line.to + 1;
      }
      const at = doc.lineAt(Math.min(ch.fromB, doc.length)).from;
      blocks.push({ pos: Math.min(ch.fromB, doc.length), lines: old.length });
      if (old.length || (diff.editable && !aLines.some(l => l.ch === ch))) {
        ranges.push(CM.Decoration.widget({ widget: new WipBlock(diff, ch, old, a), block: true, side: -1 }).range(at));
      }
      if (ch.toB > ch.fromB) {
        for (let n = doc.lineAt(ch.fromB).number, last = doc.lineAt(Math.min(ch.toB - 1, doc.length)).number; n <= last; n++) {
          ranges.push(CM.Decoration.line({ class: 'cm-wipLine' }).range(doc.line(n).from));
          gutter.push(addGutter.range(doc.line(n).from));
        }
      }
      for (const c of ch.changes) {
        const from = Math.min(ch.fromB + c.fromB, doc.length), to = Math.min(ch.fromB + c.toB, doc.length);
        if (to > from) ranges.push(CM.Decoration.mark({ class: 'cm-wipText' }).range(from, to));
      }
    }
    return { head, deco: CM.Decoration.set(ranges, true), gutter: CM.RangeSet.of(gutter, true), chunks, blocks, aLines };
  };
  const field = diff => CM.StateField.define({
    create: s => build(diff, s, diff.d.head ?? null),
    update(v, tr) {
      for (const e of tr.effects) if (e.is(setHead)) return build(diff, tr.state, e.value);
      return tr.docChanged ? build(diff, tr.state, v.head) : v;
    },
    provide: f => [CM.EditorView.decorations.from(f, v => v.deco), CM.gutterLineClass.from(f, v => v.gutter)],
  });
  // a narancs blokk sávjele a változás-hasábban
  const widgetGutter = CM.gutterWidgetClass.of((view, widget) => (widget instanceof WipBlock ? delGutter : null));
  /* Egymás mellett a bal oldal (a szülő) narancs sorai: a WIP törölte őket (`aLines`). */
  const setALayer = CM.StateEffect.define();
  const aLayer = CM.StateField.define({
    create: () => ({ deco: CM.Decoration.none, gutter: CM.RangeSet.empty }),
    update(v, tr) {
      for (const e of tr.effects) {
        if (!e.is(setALayer)) continue;
        const { diff, lines, head } = e.value, doc = tr.state.doc, ranges = [], gutter = [];
        for (const l of lines) {
          if (l.pos > doc.length) continue;
          const line = doc.lineAt(l.pos);
          ranges.push(CM.Decoration.line({ class: 'cm-wipDelLine' }).range(line.from));
          gutter.push(delGutter.range(line.from));
          if (l.reject && diff.editable) ranges.push(CM.Decoration.widget({ widget: new RejectMark(diff, l.reject, head), side: -1 }).range(line.from));
          for (const [f, t] of l.marks) if (line.from + t <= line.to) ranges.push(CM.Decoration.mark({ class: 'cm-wipDelText' }).range(line.from + f, line.from + t));
        }
        return { deco: CM.Decoration.set(ranges, true), gutter: CM.RangeSet.of(gutter, true) };
      }
      return { deco: v.deco.map(tr.changes), gutter: v.gutter.map(tr.changes) };
    },
    provide: f => [CM.EditorView.decorations.from(f, v => v.deco), CM.gutterLineClass.from(f, v => v.gutter)],
  });
  // A saját változatlan-rés (egymás alatt, WIP-réteggel): a merge `collapseUnchanged`-je csak a commit
  // változásait látja; ez mindkét diffét. Kattintásra a rés egyben nyílik.
  const setGaps = CM.StateEffect.define(), openGap = CM.StateEffect.define();
  /* A rés magassága: a DOM-ja ezt kapja, és a CodeMirror becslése is ez. Ha a kettő eltér (a merge
     27-es becslése mellett a CSS-ből 26 px lett), egymás mellett a MergeView igazítása minden
     képkockában újramér (#63). */
  const GAP_H = 26;
  class Gap extends CM.WidgetType {
    constructor(n, i, onOpen) { super(); Object.assign(this, { n, i, onOpen }); }
    eq(o) { return o.n === this.n && o.i === this.i; }
    toDOM() {
      const el = Object.assign(document.createElement('div'), { className: 'cm-collapsedLines', textContent: `${this.n} változatlan sor` });
      el.style.height = `${GAP_H}px`;
      el.addEventListener('click', () => this.onOpen(this.i));
      return el;
    }
    ignoreEvent(e) { return e instanceof MouseEvent; }
    get estimatedHeight() { return GAP_H; }
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
  /* A rések sorai ([első, utolsó]): a merge és a WIP változott soraitól 3 sornyi margóval, legalább 4 sor. */
  const gapLines = (state, wipChunks) => {
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
      if (to - from + 1 >= 4) ranges.push([from, to]);
      n = end + 1;
    }
    return ranges;
  };
  /* A rések dekorációja; a kattintás `onOpen(i)`: a hívó nyitja ki (egymás mellett a két oldalon együtt). */
  const gapDeco = (doc, lines, onOpen) => CM.Decoration.set(lines.map(([from, to], i) =>
    CM.Decoration.replace({ widget: new Gap(to - from + 1, i, onOpen), block: true }).range(doc.line(from).from, doc.line(to).to)));
  /* A merge alapja: a szülő, rajta a WIP azon blokkjaival, amelyek a commit blokkjait nem érintik —
     így a merge (alap → lemez) csak a commit változását jelöli; az átfedő blokk a szülőé marad. */
  const base = (parent, head, doc) => {
    const p = CM.Text.of(parent.split('\n')), h = CM.Text.of(head.split('\n')), d = CM.Text.of(doc.split('\n'));
    const commit = CM.Chunk.build(p, h, DIFF_CONFIG), changes = [];
    for (const w of lineChunks(h, d)) {
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
  /* Egymás mellett a narancs blokk csak a jobb oldalon foglal helyet: a bal oldalon ugyanakkora üres hely
     (`cm-wipSpacer`, mint a merge saját térköze), így a két oldal egy vonalban marad. */
  const setSpacers = CM.StateEffect.define();
  class Spacer extends CM.WidgetType {
    constructor(px) { super(); this.px = px; }
    eq(o) { return o.px === this.px; }
    toDOM() { return Object.assign(document.createElement('div'), { className: 'cm-wipSpacer', style: `height:${this.px}px` }); }
    get estimatedHeight() { return this.px; }
  }
  const spacers = CM.StateField.define({
    create: () => CM.Decoration.none,
    update(deco, tr) {
      deco = deco.map(tr.changes);
      for (const e of tr.effects) {
        if (e.is(setSpacers)) {
          deco = CM.Decoration.set(e.value.map(s => CM.Decoration.widget({ widget: new Spacer(s.px), block: true, side: -1 }).range(s.pos)), true);
        }
      }
      return deco;
    },
    provide: f => CM.EditorView.decorations.from(f),
  });
  wipShared = { setHead, field, widgetGutter, setALayer, aLayer, gaps, setGaps, openGap, gapLines, gapDeco, base, setSpacers, spacers };
  return wipShared;
}

/* Az elvetés gombja: ikon, egy sornyi magas, a súgója a felirat. */
export function rejectButton() {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'cm-reject';
  b.setAttribute('aria-label', 'Elvetés');
  b.dataset.tip = 'Elvetés';
  b.innerHTML = icon('revert');
  return b;
}
