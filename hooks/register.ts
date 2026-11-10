import type { Register } from 'claude-code'

// A plugin modja: a session indulásakor a modell nélkül nyitja meg a repó
// Artifactját, a beépített `Artifact` eszköz `open`-jével, majd előhozza a panelt.
// Hogy kell-e, azt a Python dönti el (`git-graph --mod-plan`): be van-e kapcsolva,
// naprakész-e a lap, a deklarált capability-lista és a contract, és a sessionben
// volt-e már. Új lapot, elavultat és capability- vagy contract-változást a hook kér
// a sessiontől: modból az auto mód a publikálást elutasítja
// (mérve, .claude/memory/mod-limits.md).

type Plan = { repo: string; url: string }

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

// Az `Artifact` `open`-je: a meglévő lapot újraküldés nélkül, kérdés nélkül nyitja
// meg. Ha az auto mód nem döntött („gave no verdict”), egyszer újra (mérve,
// 2026-11-06). Igaz, ha megnyílt.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const open = async ($: any, plan: Plan): Promise<boolean> => {
  const input = { tool: 'Artifact', action: 'open', url: plan.url }
  let r = await $.tool.call(input)
  if (r.deny !== undefined && String(r.deny).includes('gave no verdict')) r = await $.tool.call(input)
  return r.deny === undefined && !r.isError
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const run = async ($: any): Promise<void> => {
  const bin = `${$.plugin.root}/bin/git-graph`
  const { stdout } = await $.process.run([
    '/usr/bin/python3', bin, await settledCwd($), '--mod-plan', '--session', await $.session.id(),
  ])
  if (!stdout.trim()) return
  const plan: Plan = JSON.parse(stdout)
  if (await open($, plan)) await $.tool.call({ tool: 'mcp__ccd_view__show_pane', pane: 'artifact' })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    void run($).catch(() => undefined)
    return started
  })
}
