import { useStore } from 'zustand'
import type { StoreApi } from 'zustand/vanilla'
import type { EditorOperationView } from './editor-model'
import type { EditorState } from './editor-store'

type ReviewStatusBarProps = {
  operation: EditorOperationView
  store: StoreApi<EditorState>
}

export function reviewStatusText(operation: EditorOperationView, conflict: boolean) {
  return conflict
    ? 'Conflict'
    : !operation.preview
      ? 'No preview artifact'
      : operation.preview.status === 'stale'
        ? 'Preview stale'
        : operation.approval?.status === 'approved'
          ? 'Preview approved'
          : operation.approval?.status === 'rejected'
            ? 'Preview rejected'
            : 'Preview current'
}

function operationLabel(kind: EditorOperationView['kind']) {
  if (kind === 'content-cards') return 'Content Cards'
  if (kind === 'graphic-motion') return 'Graphic Motion'
  return 'Captions'
}

export function ReviewStatusBar({ operation, store }: ReviewStatusBarProps) {
  const draft = useStore(store, (state) => state.getOperationDraft(operation.id))
  const canSave = useStore(store, (state) => state.canSaveOperation(operation.id))
  const save = useStore(store, (state) => state.saveOperationDraft)
  const discard = useStore(store, (state) => state.discardOperationDraft)
  const previewStatus = reviewStatusText(operation, Boolean(draft?.conflict))

  return (
    <section
      data-review-status={operation.preview?.status}
      className="review-status-bar"
    >
      <output className="review-status-copy" role="status" aria-label={`${operationLabel(operation.kind)} review status`} aria-live="polite">
        <strong>{previewStatus}</strong>
        {draft?.dirty ? <span> Unsaved changes</span> : null}
        {draft?.conflict ? <span> External update detected</span> : null}
        {draft?.pending ? <span> Saving</span> : null}
        {draft?.error ? <span role="alert"> {draft.error}</span> : null}
      </output>
      <span className="review-revision">Revision {operation.revision}</span>
      <button className="review-action-button review-action-button--primary" type="button" disabled={!canSave} onClick={() => save(operation.id)}>Save Changes</button>
      <button className="review-action-button" type="button" disabled={!draft || draft.pending} onClick={() => discard(operation.id)}>Discard changes</button>
    </section>
  )
}
