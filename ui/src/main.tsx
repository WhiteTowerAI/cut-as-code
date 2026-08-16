import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { EditorShell, type RuntimeProjectStatus } from './editor/EditorShell'
import { RuntimeApiClient } from './runtime/api-client'
import './styles.css'

const root = createRoot(document.getElementById('root')!)
root.render(<RuntimeEditor />)

function RuntimeEditor() {
  const parameters = new URLSearchParams(window.location.search)
  const projectId = parameters.get('project')
  const fixtureMode = parameters.has('scenario')
  const [runtimeState, setRuntimeState] = useState<
    | { phase: 'loading' }
    | { phase: 'error'; message: string }
    | { phase: 'ready'; runtime: RuntimeProjectStatus }
  >(() => projectId && !fixtureMode
    ? { phase: 'loading' }
    : { phase: 'error', message: 'No Protocol V1 project was selected.' })

  useEffect(() => {
    if (!projectId || fixtureMode) return
    const client = new RuntimeApiClient(projectId)
    let active = true
    let unsubscribe = () => {}
    setRuntimeState({ phase: 'loading' })
    document.documentElement.dataset.runtimeState = 'loading'
    document.documentElement.dataset.runtimeRefreshCount = '0'

    const refresh = async () => {
      const snapshot = await client.getSnapshot()
      if (!active) return
      setRuntimeState({ phase: 'ready', runtime: { projectId, snapshot, client } })
      const count = Number(document.documentElement.dataset.runtimeRefreshCount ?? '0')
      document.documentElement.dataset.runtimeRefreshCount = String(count + 1)
    }

    void (async () => {
      try {
        await refresh()
        if (!active) return
        document.documentElement.dataset.runtimeState = 'ready'
        unsubscribe = client.subscribe(() => { void refresh() })
      } catch (error) {
        if (active) {
          document.documentElement.dataset.runtimeState = 'error'
          setRuntimeState({
            phase: 'error',
            message: error instanceof Error ? error.message : 'Could not load the project snapshot',
          })
        }
      }
    })()

    return () => {
      active = false
      unsubscribe()
    }
  }, [fixtureMode, projectId])

  if (fixtureMode) return <EditorShell key="fixture" />
  if (runtimeState.phase === 'ready') {
    return <EditorShell key={runtimeState.runtime.projectId} runtime={runtimeState.runtime} />
  }
  return (
    <main className="runtime-gate">
      {runtimeState.phase === 'loading' ? (
        <section className="runtime-gate-panel" role="status" aria-label="Loading project">
          <span className="runtime-gate-spinner" aria-hidden />
          <h1>Opening project</h1>
          <p>Reading the Protocol V1 snapshot...</p>
        </section>
      ) : (
        <section className="runtime-gate-panel" role="alert" aria-label="Project unavailable">
          <h1>Project unavailable</h1>
          <p>{runtimeState.message}</p>
        </section>
      )}
    </main>
  )
}
