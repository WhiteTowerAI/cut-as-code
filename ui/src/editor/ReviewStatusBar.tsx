import { useStore } from 'zustand'
import type { StoreApi } from 'zustand/vanilla'
import type { EditorOperationView } from './editor-model'
import type { EditorState } from './editor-store'

type ReviewStatusBarProps = {
  operation: EditorOperationView
  store: StoreApi<EditorState>
}

export function ReviewStatusBar({ operation, store }: ReviewStatusBarProps) {
  const draft = useStore(store, (state) => state.getOperationDraft(operation.id))
  const canSave = useStore(store, (state) => state.canSaveOperation(operation.id))
  const save = useStore(store, (state) => state.saveOperationDraft)
  const discard = useStore(store, (state) => state.discardOperationDraft)
  const previewStatus = draft?.conflict
    ? 'Conflict'
    : !operation.preview
      ? 'No preview artifact'
    : operation.preview?.status === 'stale'
      ? 'Preview stale'
      : operation.approval?.status === 'approved'
        ? 'Preview approved'
        : operation.approval?.status === 'rejected'
          ? 'Preview rejected'
          : 'Preview current'

  return (
    <section
      data-review-status={operation.preview?.status}
      style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderBottom: '1px solid #30333b', color: '#e8ebf0', background: '#1c1e24', fontSize: 12 }}
    >
      <output role="status" aria-label="Content Cards review status" aria-live="polite">
        <strong>{previewStatus}</strong>
        {draft?.dirty ? <span> Unsaved changes</span> : null}
        {draft?.conflict ? <span> External update detected</span> : null}
      </output>
      <span style={{ marginLeft: 'auto' }}>Revision {operation.revision}</span>
      <button type="button" disabled={!canSave} onClick={() => save(operation.id)}>Save Changes</button>
      <button type="button" disabled={!draft} onClick={() => discard(operation.id)}>Discard changes</button>
    </section>
  )
}
