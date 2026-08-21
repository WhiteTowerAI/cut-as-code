import { Check, Clock3, ExternalLink, FolderOpen, FolderPlus, Plus, Power, RefreshCw, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

type HubProject = Readonly<{
  projectId: string
  displayName: string
  rootFingerprint: string
  lastOpenedAt: string
  available: boolean
  running: boolean
}>

type HubCandidate = Readonly<{
  candidateId: string
  displayName: string
  rootFingerprint: string
}>

export function HubShell() {
  const [projects, setProjects] = useState<readonly HubProject[]>([])
  const [candidates, setCandidates] = useState<readonly HubCandidate[]>([])
  const [suggestedParent, setSuggestedParent] = useState('')
  const [creating, setCreating] = useState(false)
  const [projectName, setProjectName] = useState('')
  const [projectParent, setProjectParent] = useState('')
  const [projectSource, setProjectSource] = useState('')
  const [error, setError] = useState<string>()
  const [loading, setLoading] = useState(true)
  const [updatePending, setUpdatePending] = useState<{ runtimeVersion: string; compatible?: boolean; reasons: string[] } | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(undefined)
    try {
      const response = await fetch('/v1/hub/projects', { credentials: 'same-origin' })
      const value = await response.json() as { ok?: boolean; projects?: HubProject[]; candidates?: HubCandidate[]; suggestedParent?: string; updatePending?: { runtimeVersion: string; compatible?: boolean; reasons: string[] } | null; error?: string }
      if (!response.ok || !value.ok || !Array.isArray(value.projects)) throw new Error(value.error || 'Could not load projects')
      setProjects(value.projects)
      setCandidates(Array.isArray(value.candidates) ? value.candidates : [])
      setSuggestedParent(value.suggestedParent ?? '')
      setProjectParent((current) => current || value.suggestedParent || '')
      setUpdatePending(value.updatePending ?? null)
      document.documentElement.dataset.runtimeState = 'hub-ready'
    } catch (caught) {
      document.documentElement.dataset.runtimeState = 'hub-error'
      setError(caught instanceof Error ? caught.message : 'Could not load projects')
    } finally {
      setLoading(false)
    }
  }, [])

  const post = async (path: string, body: object) => {
    const response = await fetch(path, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    })
    const value = await response.json() as { ok?: boolean; error?: string }
    if (!response.ok || !value.ok) throw new Error(value.error ?? 'Project action failed')
  }

  const registerCandidate = async (candidate: HubCandidate) => {
    try {
      setError(undefined)
      await post(`/v1/hub/candidates/${candidate.candidateId}/register`, {})
      await refresh()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not register project')
    }
  }

  const createProject = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      setError(undefined)
      await post('/v1/hub/projects', { name: projectName, parent: projectParent, source: projectSource })
      setProjectName('')
      setProjectSource('')
      setCreating(false)
      await refresh()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not create project')
    }
  }

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
          <div className="hub-heading-actions">
            <span className="hub-project-count">{projects.length}</span>
            <button className="hub-command-button" type="button" onClick={() => setCreating((value) => !value)} aria-expanded={creating}>
              {creating ? <X size={15} /> : <Plus size={15} />}
              {creating ? 'Cancel' : 'New project'}
            </button>
          </div>
        </div>

        {creating ? (
          <form className="hub-create-form" onSubmit={(event) => void createProject(event)} data-hub-create-form>
            <span className="hub-project-icon" aria-hidden><FolderPlus size={18} /></span>
            <label>Project name<input value={projectName} onChange={(event) => setProjectName(event.target.value)} required autoFocus /></label>
            <label>Parent folder<input value={projectParent} onChange={(event) => setProjectParent(event.target.value)} required placeholder={suggestedParent || 'Absolute folder path'} /></label>
            <label>Source video<input value={projectSource} onChange={(event) => setProjectSource(event.target.value)} required placeholder="Absolute video path" /></label>
            <button className="hub-command-button is-primary" type="submit"><Check size={15} />Create</button>
          </form>
        ) : null}

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

        {!loading && candidates.length > 0 ? (
          <section className="hub-candidates" aria-labelledby="hub-candidates-title">
            <div className="hub-subsection-heading">
              <div><h2 id="hub-candidates-title">Available projects</h2><p>Detected nearby, not registered</p></div>
              <span className="hub-project-count">{candidates.length}</span>
            </div>
            <div className="hub-project-list">
              {candidates.map((candidate) => (
                <article className="hub-project hub-candidate" key={candidate.candidateId} data-hub-candidate>
                  <span className="hub-project-icon is-candidate" aria-hidden><FolderPlus size={18} /></span>
                  <div className="hub-project-copy"><h3>{candidate.displayName}</h3><p>{candidate.rootFingerprint}</p></div>
                  <span className="hub-status">Unregistered</span>
                  <button className="hub-command-button" type="button" onClick={() => void registerCandidate(candidate)}><Plus size={15} />Register</button>
                </article>
              ))}
            </div>
          </section>
        ) : null}
      </section>
    </main>
  )
}

function formatLastOpened(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Recently opened' : `Opened ${new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date)}`
}
