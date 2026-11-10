import { expect, test } from 'claude-code/testing'

const URL = 'https://claude.ai/artifact/x'
const PLAN = JSON.stringify({ repo: '/repo', url: URL })

// A mod futása: a git-graph válasza (`--mod-plan`), az eszközök kamu válaszai, és
// amit a mod ebből hív.
const runs = async (
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  $: any,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on: any,
  stdout: string,
  { denyOnce = false, fail = false, cwds = ['/repo'] } = {},
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<{ argv: string[][]; calls: any[]; sleeps: number }> => {
  const argv: string[][] = []
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const calls: any[] = []
  let denied = false
  let sleeps = 0
  // a mappák sorban, az utolsó marad
  on('session.cwd', () => ({ value: cwds.length > 1 ? cwds.shift() : cwds[0] }))
  on('clock.sleep', () => {
    sleeps++
    return { value: undefined }
  })
  on('session.id', () => ({ value: 's1' }))
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on('process.run', (_: any, e: any) => {
    argv.push([...e.argv])
    return { value: { exitCode: 0, stdout: e.argv.includes('--mod-plan') ? stdout : '', stderr: '' } }
  })
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on('tool.call', (_: any, e: any) => {
    const { tool_use_id: _id, ...args } = e
    calls.push(args)
    if (args.tool === 'Artifact' && denyOnce && !denied) {
      denied = true
      return { deny: 'The server-side auto mode classifier gave no verdict for Artifact' }
    }
    if (args.tool === 'Artifact' && fail) return { result: {}, isError: true, text: 'not found' }
    return { result: {}, text: 'ok' }
  })
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/repo', surface: 'desktop', isInteractive: true })
  // a mod nem várja meg a megnyitást (`void`): a mikrofeladatok lefutnak
  for (let i = 0; i < 2000; i++) await Promise.resolve()
  return { argv: argv.map(a => a.slice(2)), calls, sleeps }
}

test('a lapot az Artifact open-jével nyitja meg, és előhozza a panelt', async ($, on) => {
  // Adott egy naprakész Artifact
  // Ha a session indul
  const { argv, calls } = await runs($, on, PLAN)
  // Akkor a mod a Python tervéből megnyitja a lapot, újraküldés nélkül
  expect(calls).toEqual([
    { tool: 'Artifact', action: 'open', url: URL },
    { tool: 'mcp__ccd_view__show_pane', pane: 'artifact' },
  ])
  expect(argv).toEqual([['/repo', '--mod-plan', '--session', 's1']])
})

test('előre melegített sessionben a végleges mappát várja meg', async ($, on) => {
  // Adott: az app a sessiont egy spare mappában indítja, és később helyezi át a repóba
  const spare = '/Users/u/.claude/spares/spare-Ab12'
  const { argv, sleeps } = await runs($, on, PLAN, { cwds: [spare, spare, '/repo'] })
  // Akkor a mod a repó mappájával dönt, nem a spare-ével
  expect(argv[0]).toEqual(['/repo', '--mod-plan', '--session', 's1'])
  expect(sleeps).toBe(2)
})

test('a döntés nélküli elutasítás után egyszer újrapróbál', async ($, on) => {
  // Adott: az auto mód elsőre nem dönt a megnyitásról
  const { calls } = await runs($, on, PLAN, { denyOnce: true })
  // Akkor a mod másodszorra megnyitja
  expect(calls.map(c => c.tool)).toEqual(['Artifact', 'Artifact', 'mcp__ccd_view__show_pane'])
})

test('ha a megnyitás nem sikerül, a panelt sem hozza elő', async ($, on) => {
  // Adott: az Artifact open hibát ad
  const { calls } = await runs($, on, PLAN, { fail: true })
  // Akkor nincs show_pane
  expect(calls.map(c => c.tool)).toEqual(['Artifact'])
})

test('nem lép, ha a git-graph nem ad tervet', async ($, on) => {
  // Adott: a Python szerint nincs teendő (kikapcsolva, elavult lap, már nyitva)
  const { argv, calls } = await runs($, on, '')
  // Akkor nincs eszközhívás
  expect(calls).toEqual([])
  expect(argv.length).toBe(1)
})
