import type { Register } from 'claude-code'

// A plugin modja: a session indulásakor a modell nélkül publikálja (ha kell) és
// nyitja meg a repó Artifactját a beépített `Artifact` eszközzel, majd előhozza a
// panelt. Hogy mit kell, azt a Python dönti el (`git-graph --mod-plan`): be van-e
// kapcsolva, van-e már lap, naprakész-e (betöltő, capability-lista, contract), és a
// sessionben volt-e már. A 2.1.321 óta a mod hívásai kérés nélkül mennek, a
// publikálás és a capability-deklarálás is (mérve, .claude/memory/mod-limits.md).

type Publish = { file_path: string; title: string; capabilities: unknown; contract: string }
type Plan = { repo: string; url: string; publish?: Publish }

// Az új Artifact URL-je a publish válaszából: „Published <fájl> at <URL> (Version …”.
const PUBLISHED_URL = /\bat (https:\/\/claude\.ai\/artifact\/[A-Za-z0-9_-]+)/
// A rögzítettnél újabb contract a publish válaszában: „Stored — contract 0.2.96 (newest 0.2.97)”.
// Az emelés egyeztetés után, a kódban (`PUBLISH_CONTRACT`): a mod csak szól.
const NEWER_CONTRACT = /\(newest (\d+\.\d+\.\d+)\)/

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

// Egy `Artifact`-hívás; a válasza, ha sikerült, különben null. Ha az auto mód nem
// döntött („gave no verdict”), egyszer újra (mérve, 2026-11-06).
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const artifact = async ($: any, input: Record<string, unknown>): Promise<string | null> => {
  const call = { tool: 'Artifact', ...input }
  let r = await $.tool.call(call)
  if (r.deny !== undefined && String(r.deny).includes('gave no verdict')) r = await $.tool.call(call)
  return r.deny === undefined && !r.isError ? String(r.text ?? '') : null
}

// A lap feltöltése: meglévőre `read` után (enélkül a publish elutasított), a teljes
// capability-listával és a rögzített contracttal; utána a `--published` írja vissza
// az URL-t és a hasheket. A lap URL-je, vagy null, ha nem sikerült.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const publish = async ($: any, bin: string, plan: Plan, job: Publish): Promise<string | null> => {
  const { file_path, capabilities, contract } = job
  if (plan.url && (await artifact($, { action: 'read', url: plan.url })) === null) return null
  const text = await artifact($, plan.url
    ? { action: 'publish', url: plan.url, file_path, capabilities, contract }
    : { action: 'publish', file_path, title: job.title, icon: 'branch', capabilities, contract })
  const url = plan.url || PUBLISHED_URL.exec(text ?? '')?.[1]
  if (text === null || !url) return null
  const newer = NEWER_CONTRACT.exec(text)?.[1]
  if (newer) await $.ui.toast(`git-graph: újabb Artifact-contract érhető el (${newer}; a lap ${contract}-on fut)`)
  await $.process.run(['/usr/bin/python3', bin, plan.repo, '--published', url])
  return url
}

// A terv végrehajtása: publikálás, ha kell, majd megnyitás. `manual`: a `/git-graph`
// command kérése (a beállításoktól és a session korábbi megnyitásától függetlenül).
// A válasz a command kimenetének sora; a session indulásakor senki nem olvassa.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const run = async ($: any, manual = false): Promise<string> => {
  const bin = `${$.plugin.root}/bin/git-graph`
  const { stdout } = await $.process.run([
    '/usr/bin/python3', bin, await settledCwd($), '--mod-plan', '--session', await $.session.id(),
    ...(manual ? ['--manual'] : []),
  ])
  if (!stdout.trim()) return 'A git-graph itt nem nyitható meg: a mappa nem git repó.'
  const plan: Plan = JSON.parse(stdout)
  const url = plan.publish ? await publish($, bin, plan, plan.publish) : plan.url
  if (!url) return 'A git-graph lapját nem sikerült publikálni.'
  if ((await artifact($, { action: 'open', url })) === null) return `A git-graph lapját nem sikerült megnyitni: ${url}`
  await $.tool.call({ tool: 'mcp__ccd_view__show_pane', pane: 'artifact' })
  return `${plan.publish ? 'Publikálva és megnyitva' : 'Megnyitva'}: ${url}`
}

const COMMAND = 'git-graph'

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await $.command.register({
      name: COMMAND, description: 'A repó Git Graph lapja: publikálja, ha kell, és megnyitja',
    })
    void run($).catch(() => undefined)
    return started
  })
  on('command.run', { command: COMMAND }, async $ => ({ text: await run($, true) }))
}
