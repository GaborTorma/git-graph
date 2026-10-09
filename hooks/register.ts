import type { Register } from 'claude-code'

// A plugin modja: a repó Artifactját a modell nélkül nyitja meg a session
// indulásakor. Hogy kell-e, azt a Python dönti el (`git-graph --open-url`:
// naprakész lap, a sessionben még nem volt nyitva). A publikálás a modellé
// marad (a hook kéri): modból az auto mód elutasítja, az `open` viszont
// átmegy (mérve, docs/artifact-findings.md).

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const openArtifact = async ($: any): Promise<void> => {
  const { stdout } = await $.process.run([
    '/usr/bin/python3', `${$.plugin.root}/bin/git-graph`, await $.session.cwd(),
    '--open-url', '--session', await $.session.id(),
  ])
  const url = stdout.trim()
  if (url) await $.tool.call({ tool: 'Artifact', action: 'open', url })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    void openArtifact($).catch(() => undefined)
    return started
  })
}
