import { useState } from 'react'
import { useStore } from 'zustand'
import type { StoreApi } from 'zustand/vanilla'
import type { EditorOperationView } from './editor-model'
import type { EditorState } from './editor-store'
import { ReviewStatusBar } from './ReviewStatusBar'

type ProjectReviewPanelProps = {
  operation: EditorOperationView
  store: StoreApi<EditorState>
}

export function ProjectReviewPanel({ operation, store }: ProjectReviewPanelProps) {
  const [decision, setDecision] = useState<'approved' | 'rejected' | null>(null)
  const [rationale, setRationale] = useState('')
  const recordDecision = useStore(store, (state) => state.recordReviewDecision)
  const canApprove = useStore(store, (state) => state.canApproveOperation(operation.id))

  return (
    <>
      <ReviewStatusBar operation={operation} store={store} />
      <div style={{ display: 'flex', gap: 8, padding: '8px 12px', borderBottom: '1px solid #30333b', background: '#17191e' }}>
        <button type="button" disabled={!canApprove} onClick={() => setDecision('approved')}>Approve preview</button>
        <button type="button" disabled={!canApprove} onClick={() => setDecision('rejected')}>Reject preview</button>
      </div>
      {decision ? (
        <form
          aria-label={`${decision === 'approved' ? 'Approve' : 'Reject'} preview form`}
          style={{ display: 'flex', gap: 8, padding: 12, borderBottom: '1px solid #30333b', background: '#17191e' }}
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
          <button type="submit" disabled={!canApprove || !rationale.trim()}>Confirm {decision === 'approved' ? 'approval' : 'rejection'}</button>
        </form>
      ) : null}
    </>
  )
}
