import type { Register } from 'claude-code'

// A plugin modja: a session indulásakor a modell nélkül küldi újra és nyitja
// meg a repó Artifactját. Az app Artifact-panelje csak a sessionben publikált
// lapot mutatja, ezért a mod a lapot újraküldi — a csak betöltőt érintő
// frissítést is (a capability a republishnél öröklődik) —, visszaírja a hasht
// (`--republished`), majd előhozza a panelt. Hogy kell-e, azt a Python dönti el
// (`git-graph --mod-plan`): be van-e kapcsolva, a deklarált capability-lista a
// mostani-e, a sessionben volt-e már, és engedik-e a Claude Code beállításai
// (`permissions.allow`) a kérés nélküli hívást. Új lapot és capability-változást
// a hook kéri a sessiontől: a `declare_capabilities` modból nem megy át, a
// kattintás `consent`-jével sem (mérve, .claude/memory/mod-limits.md).

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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const run = async ($: any): Promise<void> => {
  const bin = `${$.plugin.root}/bin/git-graph`
  const { stdout } = await $.process.run([
    '/usr/bin/python3', bin, await settledCwd($), '--mod-plan', '--session', await $.session.id(),
  ])
  if (!stdout.trim()) return
  const plan: Plan = JSON.parse(stdout)
  await republish($, plan)
  await $.process.run(['/usr/bin/python3', bin, plan.repo, '--republished', plan.url])
  await $.tool.call({ tool: 'mcp__ccd_view__show_pane', pane: 'artifact' })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    void run($).catch(() => undefined)
    return started
  })
}
