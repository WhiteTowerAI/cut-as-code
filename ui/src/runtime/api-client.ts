import type { ContentCardsReview, ResourceResponse, RuntimeMutationResponse, RuntimeReadSet, RuntimeResourceContent, RuntimeSnapshot, SnapshotResponse } from './types'

export class RuntimeConflictError extends Error {
  constructor(readonly snapshot?: RuntimeSnapshot) {
    super('The operation changed outside this editor')
  }
}

export class RuntimeApiClient {
  constructor(private readonly projectId: string) {}

  async getSnapshot(): Promise<RuntimeSnapshot> {
    const response = await fetch(`/v1/projects/${encodeURIComponent(this.projectId)}/snapshot`, {
      credentials: 'same-origin',
    })
    if (!response.ok) throw new Error('Could not load the project snapshot')
    const value = await response.json() as SnapshotResponse
    if (!value.ok) throw new Error('Could not load the project snapshot')
    return value.snapshot
  }

  async getResource(resourceId: string): Promise<RuntimeResourceContent> {
    if (!/^res_[a-f0-9]+$/.test(resourceId)) throw new Error('Invalid protocol resource ID')
    const response = await fetch(`/v1/projects/${encodeURIComponent(this.projectId)}/resources/${encodeURIComponent(resourceId)}`, {
      credentials: 'same-origin',
    })
    if (!response.ok) throw new Error('Could not load the protocol resource')
    const value = await response.json() as ResourceResponse
    if (!value.ok) throw new Error('Could not load the protocol resource')
    return value.resource
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
