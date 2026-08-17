import type { ContentCardsReview, ResourceResponse, RuntimeExportJob, RuntimeExportResponse, RuntimeMutationResponse, RuntimeReadSet, RuntimeResourceContent, RuntimeSnapshot, SnapshotResponse } from './types'

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

  async startExport(): Promise<RuntimeExportJob> {
    return this.exportRequest(`/v1/projects/${encodeURIComponent(this.projectId)}/exports`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
  }

  async getExportStatus(): Promise<RuntimeExportJob> {
    return this.exportRequest(`/v1/projects/${encodeURIComponent(this.projectId)}/exports/status`, {
      credentials: 'same-origin',
    })
  }

  async openExport(action: 'open' | 'reveal'): Promise<void> {
    const response = await fetch(`/v1/projects/${encodeURIComponent(this.projectId)}/exports/${action}`, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}),
    })
    const value = await response.json() as { ok?: boolean; error?: string }
    if (!response.ok || !value.ok) throw new Error(value.error ?? 'Could not open the exported video')
  }

  async updateContentCards(readSet: RuntimeReadSet, review: ContentCardsReview) {
    return this.updatePlan('content-cards', readSet, review)
  }

  async updatePlan(operation: string, readSet: RuntimeReadSet, review: Readonly<Record<string, unknown>>) {
    return this.mutate(`/v1/projects/${encodeURIComponent(this.projectId)}/transactions`, {
      operation, readSet, review,
    })
  }

  async recordContentCardsReview(readSet: RuntimeReadSet, decision: Readonly<Record<string, unknown>>) {
    return this.recordReview('content-cards', readSet, decision)
  }

  async recordReview(operation: string, readSet: RuntimeReadSet, decision: Readonly<Record<string, unknown>>) {
    return this.mutate(`/v1/projects/${encodeURIComponent(this.projectId)}/reviews/decision`, {
      operation, readSet, decision,
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


  private async exportRequest(path: string, init: RequestInit): Promise<RuntimeExportJob> {
    const response = await fetch(path, init)
    const value = await response.json() as RuntimeExportResponse
    if (!response.ok || !value.ok) throw new Error(value.error ?? 'Video export failed')
    return value.job
  }
}
