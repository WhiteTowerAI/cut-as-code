import type { ContentCardsReview, ResourceResponse, RuntimeExportJob, RuntimeExportResponse, RuntimeMutationResponse, RuntimeReadSet, RuntimeResourceContent, RuntimeSnapshot, RuntimeTimelineReadSet, SnapshotResponse } from './types'
import type { TimelineEditCommand } from '../editor/timeline-edit'

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

  async importFiles(files: readonly File[]): Promise<RuntimeSnapshot> {
    if (!files.length) throw new Error('Choose at least one media file')
    let snapshot: RuntimeSnapshot | undefined
    for (const file of files) {
      const body = new FormData()
      body.append('asset', file, file.name)
      const response = await fetch(`/v1/projects/${encodeURIComponent(this.projectId)}/imports`, {
        method: 'POST', credentials: 'same-origin', body,
      })
      const value = await response.json() as SnapshotResponse
      if (!response.ok || !value.ok) throw new Error((value as SnapshotResponse & { error?: string }).error ?? 'Could not import media')
      snapshot = value.snapshot
    }
    if (!snapshot) throw new Error('Could not import media')
    return snapshot
  }

  async updateContentCards(readSet: RuntimeReadSet, review: ContentCardsReview) {
    return this.updatePlan('content-cards', readSet, review)
  }

  async editTimeline(readSet: RuntimeTimelineReadSet, command: TimelineEditCommand) {
    const serialized = command.type === 'split'
      ? { type: command.type, clip_id: command.clipId, at_s: command.atS }
      : command.type === 'delete'
        ? { type: command.type, clip_id: command.clipId }
        : command.type === 'trim'
          ? { type: command.type, clip_id: command.clipId, edge: command.edge, source_s: command.sourceS }
          : command.type === 'restore-bounds'
            ? { type: command.type, clip_id: command.clipId }
            : command.type === 'set-range'
              ? { type: command.type, clip_id: command.clipId, start_s: command.startS, end_s: command.endS }
          : command.type === 'join'
            ? { type: command.type, left_clip_id: command.leftClipId, right_clip_id: command.rightClipId }
            : {
                type: command.type,
                index: command.index,
                clip: {
                  id: command.clip.id,
                  source_range: {
                    start_s: command.clip.sourceRange.startS,
                    end_s: command.clip.sourceRange.endS,
                  },
                  speed: command.clip.speed ?? 1,
                  ...(command.clip.decisionRef ? { decision_ref: command.clip.decisionRef } : {}),
                  ...(command.clip.sourceAssetId ? { source_asset_id: command.clip.sourceAssetId } : {}),
                },
              }
    return this.mutate(`/v1/projects/${encodeURIComponent(this.projectId)}/timeline/edits`, {
      readSet,
      command: serialized,
    })
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
