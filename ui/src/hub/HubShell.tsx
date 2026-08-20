import { Clock3, ExternalLink, FolderOpen, Power, RefreshCw, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

type HubProject = Readonly<{
  projectId: string
  displayName: string
  rootFingerprint: string
  lastOpenedAt: string
  available: boolean
  running: boolean
}>

export function HubShell() {
  const [projects, setProjects] = useState<readonly HubProject[]>([])
  const [error, setError] = useState<string>()
  const [loading, setLoading] = useState(true)
  const [updatePending, setUpdatePending] = useState<{ runtimeVersion: string; compatible?: boolean; reasons: string[] } | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(undefined)
    try {
      const response = await fetch('/v1/hub/projects', { credentials: 'same-origin' })
      const value = await response.json() as { ok?: boolean; projects?: HubProject[]; updatePending?: { runtimeVersion: string; compatible?: boolean; reasons: string[] } | null; error?: string }
      if (!response.ok || !value.ok || !Array.isArray(value.projects)) throw new Error(value.error || 'Could not load projects')
      setProjects(value.projects)
      setUpdatePending(value.updatePending ?? null)
      document.documentElement.dataset.runtimeState = 'hub-ready'
    } catch (caught) {
      document.documentElement.dataset.runtimeState = 'hub-error'
      setError(caught instanceof Error ? caught.message : 'Could not load projects')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  const postLifecycle = async (path: string, label: string) => {
    const send = async (force: boolean): Promise<boolean> => {
      const response = await fetch(path, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ force }),
      })
      const value = await response.json() as { ok?: boolean; requiresConfirmation?: boolean; reasons?: string[]; affected?: { displayName: string; reasons: string[] }[]; error?: string }
      if (response.status === 409 && value.requiresConfirmation) {
        const details = value.reasons?.join(', ') ?? value.affected?.flatMap((project) => project.reasons.map((reason) => `${project.displayName}: ${reason}`)).join(', ')
        if (window.confirm(`${label} will affect protected work${details ? ` (${details})` : ''}. Continue?`)) return send(true)
        return false
      }
      if (!response.ok || !value.ok) throw new Error(value.error ?? `${label} failed`)
      return true
    }
    try {
      if (await send(false)) await refresh()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `${label} failed`)
    }
  }

  return (
    <main className="hub-shell" data-hub-shell>
      <header className="hub-header">
        <div className="hub-brand">
          <span className="hub-mark" aria-hidden><FolderOpen size={18} /></span>
          <div>
            <h1>Cut as Code</h1>
            <p>Editor Hub</p>
          </div>
        </div>
        <button className="hub-icon-button" type="button" onClick={() => void refresh()} title="Refresh projects" aria-label="Refresh projects">
          <RefreshCw size={16} />
        </button>
        <button className="hub-icon-button" type="button" onClick={() => void postLifecycle('/v1/hub/quit', 'Quit Editor Service')} title="Quit Editor Service" aria-label="Quit Editor Service">
          <Power size={16} />
        </button>
      </header>

      <section className="hub-content" aria-labelledby="hub-projects-title">
        {updatePending ? (
          <div className="hub-update-pending" role="status" data-update-pending>
            <strong>Editor update pending</strong>
            <span>{updatePending.compatible
              ? `${updatePending.runtimeVersion} is available; active sessions continue on the current runtime.`
              : `${updatePending.runtimeVersion} waits for ${updatePending.reasons.join(', ')}.`}</span>
          </div>
        ) : null}
        <div className="hub-section-heading">
          <div>
            <h2 id="hub-projects-title">Projects</h2>
            <p>Registered Cut as Code projects</p>
          </div>
          <span className="hub-project-count">{projects.length}</span>
        </div>

        {loading ? <div className="hub-state" role="status">Loading projects...</div> : null}
        {error ? <div className="hub-state hub-state-error" role="alert">{error}</div> : null}
        {!loading && !error && projects.length === 0 ? (
          <div className="hub-state">No registered projects</div>
        ) : null}
        {!loading && !error && projects.length > 0 ? (
          <div className="hub-project-list">
            {projects.map((project) => (
              <article className="hub-project" key={project.projectId} data-hub-project>
                <span className={`hub-project-icon ${project.available ? '' : 'is-unavailable'}`} aria-hidden><FolderOpen size={18} /></span>
                <div className="hub-project-copy">
                  <h3 data-hub-project-name>{project.displayName}</h3>
                  <p><Clock3 size={12} /> {formatLastOpened(project.lastOpenedAt)} · {project.rootFingerprint}</p>
                </div>
                <span className={`hub-status ${project.running ? 'is-running' : ''}`}>
                  {project.available ? (project.running ? 'Open' : 'Ready') : 'Unavailable'}
                </span>
                {project.available ? (
                  <a className="hub-open-button" href={`/v1/hub/projects/${encodeURIComponent(project.projectId)}/open`} target="_blank" rel="noreferrer" title={`Open ${project.displayName}`} aria-label={`Open ${project.displayName}`}>
                    <ExternalLink size={16} />
                  </a>
                ) : null}
                {project.running ? (
                  <button className="hub-close-button" type="button" onClick={() => void postLifecycle(`/v1/hub/projects/${encodeURIComponent(project.projectId)}/close`, `Close ${project.displayName}`)} title={`Close ${project.displayName}`} aria-label={`Close ${project.displayName}`}>
                    <X size={16} />
                  </button>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  )
}

function formatLastOpened(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Recently opened' : `Opened ${new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date)}`
}
