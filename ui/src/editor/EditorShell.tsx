import { useState } from 'react'
import { LibraryPanel } from './LibraryPanel'
import { createEditorStore } from './editor-store'
import { getScenario } from './scenarios'

export function EditorShell() {
  const scenarioId = new URLSearchParams(window.location.search).get('scenario') ?? '1-84'
  const scenario = getScenario(scenarioId) ?? getScenario('1-84')!
  const [store] = useState(() => createEditorStore(scenario.initialState))

  return (
    <main className="editor-shell" data-editor-shell aria-label="Video editor">
      <LibraryPanel store={store} />
    </main>
  )
}
