import type { Register } from 'claude-code'

// A plugin modja: a session indulásakor a modell nélkül nyitja meg a repó
// Artifactját, a beépített `Artifact` eszköz `open`-jével, majd előhozza a panelt.
// Hogy kell-e, azt a Python dönti el (`git-graph --mod-plan`): be van-e kapcsolva,
// naprakész-e a lap és a deklarált capability-lista, és a sessionben volt-e már.
// Új lapot, elavultat és capability-változást a hook kér a sessiontől: modból az
// auto mód a publikálást elutasítja (mérve, .claude/memory/mod-limits.md).
// Tartalék: ahol `Artifact` eszköz nincs (2026-11-05/06-i app), a `claude-artifacts`
// eszközeivel újraküldi a lapot, mert ott a panel csak a sessionben publikáltat mutatja.

type Plan = { repo: string; url: string; page: string }

type Artifact = { slug: string; url?: string; version: string; read?: string }

const ARTIFACTS = 'mcp__claude-artifacts__'

// Egy Artifact-eszköz hívása; a válasza JSON. Elutasítás vagy hiba: kivétel. Ha az
// auto mód nem döntött („gave no verdict”), az üzenete szerint egyszer újra —
// olvasásnál szabály nélkül előfordul (mérve, 2026-11-06).
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const call = async ($: any, tool: string, args: Record<string, unknown>): Promise<any> => {
  const input = { tool: ARTIFACTS + tool, ...args }
  let r = await $.tool.call(input)
  if (r.deny !== undefined && String(r.deny).includes('gave no verdict')) r = await $.tool.call(input)
  if (r.deny !== undefined) throw new Error(`${tool}: ${r.deny}`)
  if (r.isError) throw new Error(`${tool}: ${r.text}`)
  return leadingJson(String(r.text))
}

// A válasz eleji JSON-objektum: az eszköz utána még szöveget fűzhet hozzá.
const leadingJson = (text: string): unknown => {
  const start = text.indexOf('{')
  let depth = 0
  let quoted = false
  for (let i = start; i >= 0 && i < text.length; i++) {
    const c = text[i]
    if (quoted) {
      if (c === '\\') i++
      else if (c === '"') quoted = false
    } else if (c === '"') quoted = true
    else if (c === '{') depth++
    else if (c === '}' && --depth === 0) return JSON.parse(text.slice(start, i + 1))
  }
  return JSON.parse(text)
}

// A lap újraküldése az élő verzióra.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const republish = async ($: any, plan: Plan): Promise<void> => {
  const live: Artifact = await call($, 'get_artifact', { slug: plan.url })
  const shared = live.read && live.read !== 'owner' ? { shared_live: live.read } : {}
  await call($, 'publish_files', {
    slug: live.slug, base_version: live.version, files: [{ as: 'index.html', path: plan.page }], ...shared,
  })
}

// Az app új chathez előre melegített sessiont tart (`~/.claude/spares/spare-*`):
// a `session.start` ott fut, a végleges mappát csak a chat indulásakor kapja meg
// (`relocated`), erre nincs esemény. Addig másodpercenként újranézzük.
const SPARE = '/.claude/spares/'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const settledCwd = async ($: any): Promise<string> => {
  let cwd: string = await $.session.cwd()
  while (cwd.includes(SPARE)) {
    await $.clock.sleep(1000)
    cwd = await $.session.cwd()
  }
  return cwd
}

// A beépített `Artifact` eszköz `open`-je: ahol van, a meglévő lapot újraküldés
// nélkül nyitja meg (2.1.293-on mérve, kérdés nélkül megy; a 2026-11-09-i appban
// újra ez van a `claude-artifacts` eszközei helyett). Hamis, ha nincs ilyen eszköz,
// vagy nem sikerült: akkor a `claude-artifacts` útja jön.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const openBuiltin = async ($: any, plan: Plan): Promise<boolean> => {
  const input = { tool: 'Artifact', action: 'open', url: plan.url }
  try {
    let r = await $.tool.call(input)
    if (r.deny !== undefined && String(r.deny).includes('gave no verdict')) r = await $.tool.call(input)
    return r.deny === undefined && !r.isError
  } catch {
    return false
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const run = async ($: any): Promise<void> => {
  const bin = `${$.plugin.root}/bin/git-graph`
  const { stdout } = await $.process.run([
    '/usr/bin/python3', bin, await settledCwd($), '--mod-plan', '--session', await $.session.id(),
  ])
  if (!stdout.trim()) return
  const plan: Plan = JSON.parse(stdout)
  if (!(await openBuiltin($, plan))) {
    await republish($, plan)
    await $.process.run(['/usr/bin/python3', bin, plan.repo, '--republished', plan.url])
  }
  await $.tool.call({ tool: 'mcp__ccd_view__show_pane', pane: 'artifact' })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    void run($).catch(() => undefined)
    return started
  })
}
