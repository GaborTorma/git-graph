import { expect, test } from 'claude-code/testing'

const URL = 'https://claude.ai/artifact/x'

// A git-graph `--open-url` válasza (`stdout`), és amit a mod ebből az Artifact toolnak ad.
const opens = async (
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  $: any,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on: any,
  stdout: string,
  act: () => Promise<unknown>,
): Promise<{ argv: string[][]; calls: unknown[] }> => {
  const argv: string[][] = []
  const calls: unknown[] = []
  on('session.cwd', () => ({ value: '/repo' }))
  on('session.id', () => ({ value: 's1' }))
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on('process.run', (_: any, e: any) => {
    argv.push([...e.argv])
    return { value: { exitCode: 0, stdout, stderr: '' } }
  })
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on('tool.call', (_: any, e: any) => {
    if (e.tool === 'Artifact') calls.push({ action: e.action, url: e.url })
    return { result: {}, text: '' }
  })
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
  await act()
  // a mod nem várja meg a megnyitást (`void`): a mikrofeladatok lefutnak
  for (let i = 0; i < 500; i++) await Promise.resolve()
  return { argv, calls }
}

test('a session indulásakor megnyitja, ha a git-graph URL-t ad', async ($, on) => {
  const { argv, calls } = await opens($, on, `${URL}\n`, () =>
    $.session.start({ cwd: '/repo', surface: 'desktop', isInteractive: true }))
  expect(argv[0]?.slice(2)).toEqual(['/repo', '--open-url', '--session', 's1'])
  expect(calls).toEqual([{ action: 'open', url: URL }])
})

test('nem nyit, ha a git-graph nem ad URL-t', async ($, on) => {
  const { calls } = await opens($, on, '', () =>
    $.session.start({ cwd: '/repo', surface: 'desktop', isInteractive: true }))
  expect(calls).toEqual([])
})
