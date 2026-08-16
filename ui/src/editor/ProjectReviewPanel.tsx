import { useEffect, useState } from 'react'
import { useStore } from 'zustand'
import type { StoreApi } from 'zustand/vanilla'
import type { EditorOperationView } from './editor-model'
import type { EditorState } from './editor-store'
import { ReviewStatusBar } from './ReviewStatusBar'
import type { RuntimeApiClient } from '../runtime/api-client'
import type { RuntimeResource, RuntimeResourceContent } from '../runtime/types'

type ProjectReviewPanelProps = {
  operation: EditorOperationView
  store: StoreApi<EditorState>
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
