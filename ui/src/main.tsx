import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { EditorShell, type RuntimeProjectStatus } from './editor/EditorShell'
import { RuntimeApiClient } from './runtime/api-client'
import './styles.css'

const root = createRoot(document.getElementById('root')!)
root.render(<RuntimeEditor />)

function RuntimeEditor() {
  const [runtime, setRuntime] = useState<RuntimeProjectStatus>()
  const parameters = new URLSearchParams(window.location.search)
  const projectId = parameters.get('project')
  const bootstrapToken = parameters.get('bootstrap')
  const fixtureMode = parameters.has('scenario')

  useEffect(() => {
    if (!projectId || fixtureMode) return
    const client = new RuntimeApiClient(projectId)
    let active = true
    let unsubscribe = () => {}
    document.documentElement.dataset.runtimeState = 'loading'
    document.documentElement.dataset.runtimeRefreshCount = '0'

    const refresh = async () => {
      const snapshot = await client.getSnapshot()
      if (!active) return
      setRuntime({ projectId, snapshot, client })
      const count = Number(document.documentElement.dataset.runtimeRefreshCount ?? '0')
      document.documentElement.dataset.runtimeRefreshCount = String(count + 1)
    }

    void (async () => {
      try {
        if (bootstrapToken) {
          await client.bootstrap(bootstrapToken)
          parameters.delete('bootstrap')
          const query = parameters.toString()
          window.history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}`)
        }
        await refresh()
        if (!active) return
        document.documentElement.dataset.runtimeState = 'ready'
        unsubscribe = client.subscribe(() => { void refresh() })
      } catch {
        if (active) document.documentElement.dataset.runtimeState = 'error'
      }
    })()

    return () => {
      active = false
      unsubscribe()
    }
  }, [bootstrapToken, fixtureMode, projectId])

  return <EditorShell key={runtime?.projectId ?? 'fixture'} runtime={runtime} />
}
