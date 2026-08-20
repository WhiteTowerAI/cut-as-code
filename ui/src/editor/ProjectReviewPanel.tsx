import { useEffect, useState } from 'react'
import { useStore } from 'zustand'
import type { StoreApi } from 'zustand/vanilla'
import type { ContentCardLayout, ContentCardPlacement, EditorOperationView } from './editor-model'
import { draftFieldsForCue, type EditorState } from './editor-store'
import { ReviewStatusBar } from './ReviewStatusBar'
import type { RuntimeApiClient } from '../runtime/api-client'
import type { RuntimeResource, RuntimeResourceContent } from '../runtime/types'

type ProjectReviewPanelProps = {
  operation: EditorOperationView
  store: StoreApi<EditorState>
}

const cardLayouts: readonly ContentCardLayout[] = [
  'lower-third', 'quote', 'statistic', 'default', 'metric-spotlight',
  'bar-chart', 'pie-chart', 'line-chart', 'side-by-side', 'parallel-columns',
]
const cardPlacements: readonly ContentCardPlacement[] = [
  'top-left', 'top-right', 'bottom-left', 'bottom-right', 'top', 'bottom', 'left', 'right', 'center',
]

function CueInspector({ operation, store }: ProjectReviewPanelProps) {
  const selection = useStore(store, (state) => state.selection)
  const draft = useStore(store, (state) => state.getOperationDraft(operation.id))
  const edit = useStore(store, (state) => state.editOperationDraft)
  const expectedKind = operation.kind === 'content-cards' ? 'card'
    : operation.kind === 'captions' ? 'caption'
      : operation.kind === 'graphic-motion' ? 'graphic-motion'
        : null
  if (!expectedKind || selection?.kind !== expectedKind) return null
  const cues = Array.isArray(operation.fields.cues)
    ? operation.fields.cues as readonly Readonly<Record<string, unknown>>[]
    : []
  const cue = cues.find((item) => item.id === selection.id)
  if (!cue) return null
  const fields = draftFieldsForCue(draft, selection.id)
  const title = expectedKind === 'caption' ? 'Caption Inspector'
    : expectedKind === 'card' ? 'Content Card Inspector'
      : 'Graphic Motion Inspector'

  return (
    <section className="cue-inspector" aria-label={title} data-cue-inspector={selection.id} tabIndex={-1}>
      <header>
        <strong>{title}</strong>
        <span>{selection.id}</span>
      </header>
      {expectedKind === 'caption' ? (
        <label>
          <span>Text</span>
          <textarea
            aria-label="Caption text"
            value={String(fields?.text ?? cue.text ?? '')}
            onChange={(event) => edit(operation.id, { cueId: selection.id, text: event.target.value })}
          />
        </label>
      ) : null}
      {expectedKind === 'card' ? (
        <>
          <label>
            <span>Copy</span>
            <textarea
              aria-label="Content card copy"
              value={String(fields?.copy ?? cue.copy ?? '')}
              onChange={(event) => edit(operation.id, { cueId: selection.id, copy: event.target.value })}
            />
          </label>
          <label>
            <span>Layout</span>
            <select
              aria-label="Content card layout"
              value={String(fields?.layout ?? cue.layout ?? 'default')}
              onChange={(event) => edit(operation.id, { cueId: selection.id, layout: event.target.value as ContentCardLayout })}
            >
              {cardLayouts.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <label>
            <span>Placement</span>
            <select
              aria-label="Content card placement"
              value={String(fields?.placement ?? cue.placement ?? 'bottom')}
              onChange={(event) => edit(operation.id, { cueId: selection.id, placement: event.target.value as ContentCardPlacement })}
            >
              {cardPlacements.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
        </>
      ) : null}
      {expectedKind !== 'caption' ? (
        <label className="cue-inspector-toggle">
          <input
            type="checkbox"
            aria-label={`${title} enabled`}
            checked={Boolean(fields?.enabled ?? cue.enabled)}
            onChange={(event) => edit(operation.id, { cueId: selection.id, enabled: event.target.checked })}
          />
          <span>Enabled</span>
        </label>
      ) : null}
      {expectedKind === 'graphic-motion' ? (
        <p>Adjust position and scale directly on the selected layer in the Viewer.</p>
      ) : null}
    </section>
  )
}

export function ProjectReviewPanel({ operation, store }: ProjectReviewPanelProps) {
  const [decision, setDecision] = useState<'approved' | 'rejected' | null>(null)
  const [rationale, setRationale] = useState('')
  const recordDecision = useStore(store, (state) => state.recordReviewDecision)
  const canApprove = useStore(store, (state) => state.canApproveOperation(operation.id))
  const hasCurrentPreview = operation.preview?.status === 'current'
    && operation.preview.revision === operation.revision

  useEffect(() => {
    if (hasCurrentPreview) return
    setDecision(null)
    setRationale('')
  }, [hasCurrentPreview])

  return (
    <>
      <ReviewStatusBar operation={operation} store={store} />
      <CueInspector operation={operation} store={store} />
      {hasCurrentPreview ? (
        <div className="review-action-row">
          <button className="review-action-button review-action-button--primary" type="button" disabled={!canApprove} onClick={() => setDecision('approved')}>Approve preview</button>
          <button className="review-action-button review-action-button--danger" type="button" disabled={!canApprove} onClick={() => setDecision('rejected')}>Reject preview</button>
        </div>
      ) : null}
      {hasCurrentPreview && decision ? (
        <form
          aria-label={`${decision === 'approved' ? 'Approve' : 'Reject'} preview form`}
          className="review-decision-form"
          onSubmit={async (event) => {
            event.preventDefault()
            if (!rationale.trim()) return
            await recordDecision(operation.id, decision, rationale)
            setDecision(null)
            setRationale('')
          }}
        >
          <label style={{ display: 'contents' }}>
            <span className="sr-only">Decision rationale</span>
            <input aria-label="Decision rationale" value={rationale} onChange={(event) => setRationale(event.target.value)} />
          </label>
          <button className="review-action-button review-action-button--primary" type="submit" disabled={!canApprove || !rationale.trim()}>Confirm {decision === 'approved' ? 'approval' : 'rejection'}</button>
        </form>
      ) : null}
    </>
  )
}

export function ProtocolResourceInspector({ resources, client }: Readonly<{ resources: readonly RuntimeResource[]; client: RuntimeApiClient }>) {
  const [resourceId, setResourceId] = useState(resources[0]?.id ?? '')
  const [resource, setResource] = useState<RuntimeResourceContent>()
  const selectedResource = resources.find((item) => item.id === resourceId)
  const resourceIsCurrent = resource?.id === selectedResource?.id && resource?.etag === selectedResource?.etag

  useEffect(() => {
    if (selectedResource) return
    setResourceId(resources[0]?.id ?? '')
    setResource(undefined)
  }, [resources, selectedResource])

  useEffect(() => {
    if (!resourceId || !selectedResource) return
    let active = true
    setResource(undefined)
    void client.getResource(resourceId).then((next) => {
      if (active) setResource(next)
    }).catch(() => {
      if (active) setResource(undefined)
    })
    return () => { active = false }
  }, [client, resourceId, selectedResource?.etag])

  return (
    <details className="protocol-resource-inspector">
      <summary>Project data</summary>
      <section
        aria-label="Protocol resources"
        data-resource-id={resourceId}
        data-resource-kind={selectedResource?.kind ?? ''}
        data-resource-size={selectedResource ? String(selectedResource.size) : ''}
        data-resource-operation={selectedResource?.operation_id ?? ''}
      >
        <label>
          <span className="sr-only">Protocol resource</span>
          <select aria-label="Protocol resource" value={resourceId} onChange={(event) => setResourceId(event.target.value)}>
            {resources.map((item) => <option key={item.id} value={item.id}>{item.kind}{item.operation_id ? `: ${item.operation_id}` : ''}</option>)}
          </select>
        </label>
        {resourceIsCurrent && resource ? (
          <div className="protocol-resource-content">
            <output data-resource-kind>{selectedResource?.kind ?? resource.kind}</output>
            <output data-resource-size>{selectedResource?.size ?? resource.size ?? 0}</output>
            <output data-resource-operation>{selectedResource?.operation_id ?? resource.operation_id ?? ''}</output>
            <output data-resource-etag>{resource.etag}</output>
            <pre>{JSON.stringify(resource.content, null, 2)}</pre>
          </div>
        ) : <output>Loading resource</output>}
      </section>
    </details>
  )
}
