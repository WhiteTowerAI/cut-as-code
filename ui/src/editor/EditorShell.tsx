import { useState } from 'react'
import { LibraryPanel } from './LibraryPanel'
import { TimelinePanel } from './TimelinePanel'
import { ViewerPanel } from './ViewerPanel'
import { createEditorStore } from './editor-store'
import { getScenario } from './scenarios'

export function EditorShell() {
  const scenarioId = new URLSearchParams(window.location.search).get('scenario') ?? '1-84'
  const scenario = getScenario(scenarioId) ?? getScenario('1-84')!
  const [store] = useState(() => createEditorStore(scenario.initialState))
  const viewerScenarios = new Set(['1-282', '57-152', '1-1026', '1-528', '123-79'])
  const timelineScenarios = new Set(['1-324', '1-1115', '1-754', '123-167'])
  const isViewerScenario = viewerScenarios.has(scenarioId)
  const isTimelineScenario = timelineScenarios.has(scenarioId)
  const isMenuFrame = scenarioId === '57-152' || scenarioId === '1-528'

  return (
    <main
      className={isMenuFrame ? 'editor-shell editor-shell--menu-frame' : 'editor-shell'}
      data-editor-shell
      aria-label="Video editor"
    >
      {isTimelineScenario ? (
        <TimelinePanel store={store} />
      ) : isViewerScenario ? (
        <ViewerPanel store={store} />
      ) : (
        <LibraryPanel store={store} />
      )}
    </main>
  )
}
