import type { RuntimeSnapshot, SnapshotResponse } from './types'

export class RuntimeApiClient {
  constructor(private readonly projectId: string) {}

  async bootstrap(token: string): Promise<void> {
    const response = await fetch('/v1/session/bootstrap', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ projectId: this.projectId, bootstrapToken: token }),
    })
    if (!response.ok) throw new Error('Could not start the local editor session')
  }

  async getSnapshot(): Promise<RuntimeSnapshot> {
    const response = await fetch(`/v1/projects/${encodeURIComponent(this.projectId)}/snapshot`, {
      credentials: 'same-origin',
    })
    if (!response.ok) throw new Error('Could not load the project snapshot')
    const value = await response.json() as SnapshotResponse
    if (!value.ok) throw new Error('Could not load the project snapshot')
    return value.snapshot
  }

  subscribe(onChange: () => void): () => void {
    const events = new EventSource(`/v1/projects/${encodeURIComponent(this.projectId)}/events`)
    events.addEventListener('project-change', onChange)
    return () => events.close()
  }
}
