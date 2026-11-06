import { expect, test } from 'claude-code/testing'

const URL = 'https://claude.ai/artifact/x'
const PLAN = JSON.stringify({ repo: '/repo', url: URL, page: '/state/artifact.html' })

// A mod futása: a git-graph válasza (`--mod-plan`), az Artifact-eszközök kamu
// válaszai, és amit a mod ebből hív.
const runs = async (
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  $: any,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on: any,
  stdout: string,
  { read = 'owner', denyOnce = '' } = {},
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<{ argv: string[][]; calls: any[] }> => {
  const argv: string[][] = []
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const calls: any[] = []
  let denied = false
  on('session.cwd', () => ({ value: '/repo' }))
  on('session.id', () => ({ value: 's1' }))
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on('process.run', (_: any, e: any) => {
    argv.push([...e.argv])
    return { value: { exitCode: 0, stdout: e.argv.includes('--mod-plan') ? stdout : '', stderr: '' } }
  })
  const answers: Record<string, unknown> = {
    get_artifact: { slug: 'u1', url: URL, version: 'v1', read },
    publish_files: { slug: 'u1', url: URL, version: 'v2' },
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on('tool.call', (_: any, e: any) => {
    const { tool, tool_use_id: _id, ...args } = e
    const name = tool.replace('mcp__claude-artifacts__', '')
    calls.push({ tool: name, ...args })
    if (name === denyOnce && !denied) {
      denied = true
      return { deny: `The server-side auto mode classifier gave no verdict for ${tool}` }
    }
    // a publish_files a JSON után szöveget is fűz (mérve, 2026-11-06)
    const tail = name === 'publish_files' ? '\n\nOpen it: {url} — "kész"' : ''
    return { result: {}, text: JSON.stringify(answers[name] ?? {}) + tail }
  })
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/repo', surface: 'desktop', isInteractive: true })
  // a mod nem várja meg a publikálást (`void`): a mikrofeladatok lefutnak
  for (let i = 0; i < 2000; i++) await Promise.resolve()
  return { argv: argv.map(a => a.slice(2)), calls }
}

test('a lapot az élő verzióra újraküldi, visszaírja a hasht, és megnyitja a panelt', async ($, on) => {
  // Adott egy meglévő Artifact a mostani capability-vel
  // Ha a session indul
  const { argv, calls } = await runs($, on, PLAN)
  // Akkor a mod a Python tervéből újraküldi a lapot, és előhozza a panelt
  expect(calls).toEqual([
    { tool: 'get_artifact', slug: URL },
    { tool: 'publish_files', slug: 'u1', base_version: 'v1', files: [{ as: 'index.html', path: '/state/artifact.html' }] },
    { tool: 'mcp__ccd_view__show_pane', pane: 'artifact' },
  ])
  expect(argv).toEqual([['/repo', '--mod-plan', '--session', 's1'], ['/repo', '--republished', URL]])
})

test('megosztott lapnál a megosztást is megnevezi', async ($, on) => {
  // Adott egy szervezettel megosztott Artifact
  const { calls } = await runs($, on, PLAN, { read: 'org' })
  // Akkor a republish a shared_live-ot is viszi
  expect(calls[1]?.shared_live).toBe('org')
})

test('a döntés nélküli elutasítás után egyszer újrapróbál', async ($, on) => {
  // Adott: az auto mód elsőre nem dönt az olvasásról
  const { calls } = await runs($, on, PLAN, { denyOnce: 'get_artifact' })
  // Akkor a mod másodszorra továbbjut
  expect(calls.map(c => c.tool)).toEqual(
    ['get_artifact', 'get_artifact', 'publish_files', 'mcp__ccd_view__show_pane'])
})

test('nem lép, ha a git-graph nem ad tervet', async ($, on) => {
  // Adott: a Python szerint nincs teendő (szabály nélkül, új lap, capability-változás, már nyitva)
  const { argv, calls } = await runs($, on, '')
  // Akkor nincs eszközhívás és nincs visszaírás
  expect(calls).toEqual([])
  expect(argv.length).toBe(1)
})
