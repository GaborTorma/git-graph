// A lap ES-moduljai (page/js) futtatás nélkül: szintaxis, és hogy minden import egy
// létező modul létező exportjára mutat. A lap DOM-ot használ, Node-ban nem futna — a
// `vm` modul-összekötése (link) viszont kiértékelés nélkül ellenőrzi az importokat.
// Futtatás: node --experimental-vm-modules scripts/check-page.mjs
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { SourceTextModule } from 'node:vm';

const dir = new URL('../page/js/', import.meta.url).pathname;
const modules = new Map();
const load = name => {
  if (!modules.has(name)) {
    modules.set(name, new SourceTextModule(readFileSync(join(dir, name), 'utf8'), { identifier: `page/js/${name}` }));
  }
  return modules.get(name);
};
// Minden modul szintaxisa, az elérhetetleneké is.
for (const name of readdirSync(dir).filter(n => n.endsWith('.js'))) load(name);
await load('main.js').link((spec, from) => {
  if (!/^\.\/[\w-]+\.js$/.test(spec)) throw new Error(`${from.identifier}: csak './<név>.js' importálható: ${spec}`);
  return load(spec.slice(2));
});
const unused = [...modules].filter(([, m]) => m.status === 'unlinked').map(([n]) => n);
if (unused.length) throw new Error(`a main.js-ből nem érhető el: ${unused.join(', ')}`);
console.log(`✓ ${modules.size} modul összeköthető`);
