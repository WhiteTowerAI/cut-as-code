import type { ContentCardsReview, RuntimeMutationResponse, RuntimeReadSet, RuntimeSnapshot, SnapshotResponse } from './types'

export class RuntimeConflictError extends Error {
  constructor(readonly snapshot?: RuntimeSnapshot) {
    super('The operation changed outside this editor')
  }
}

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

  async updateContentCards(readSet: RuntimeReadSet, review: ContentCardsReview) {
    return this.mutate(`/v1/projects/${encodeURIComponent(this.projectId)}/transactions`, {
      operation: 'content-cards', readSet, review,
    })
  }

  async recordContentCardsReview(readSet: RuntimeReadSet, decision: Readonly<Record<string, unknown>>) {
    return this.mutate(`/v1/projects/${encodeURIComponent(this.projectId)}/reviews/decision`, {
      operation: 'content-cards', readSet, decision,
    })
  }

  private async mutate(path: string, body: unknown): Promise<RuntimeMutationResponse> {
    const response = await fetch(path, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    })
    const value = await response.json() as RuntimeMutationResponse
    if (response.status === 409 && value.snapshot) throw new RuntimeConflictError(value.snapshot)
    if (!response.ok || !value.ok) throw new Error(value.error ?? 'Protocol mutation failed')
    return value
  }
}
