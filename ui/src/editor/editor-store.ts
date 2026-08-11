import { createStore } from 'zustand/vanilla'
import type {
  EditorProjectView,
  EditorSelection,
  LibraryTab,
  MenuId,
} from './editor-model'

export type EditorState = {
  project: EditorProjectView | null
  activeTab: LibraryTab
  selection: EditorSelection
  currentTimeS: number
  isPlaying: boolean
  timelineZoom: number
  snapEnabled: boolean
  openMenu: MenuId
  setProject: (project: EditorProjectView | null) => void
  seek: (timeS: number) => void
  select: (selection: EditorSelection) => void
  setActiveTab: (tab: LibraryTab) => void
  setOpenMenu: (menu: MenuId) => void
}

export type EditorInitialState = Omit<
  EditorState,
  'setProject' | 'seek' | 'select' | 'setActiveTab' | 'setOpenMenu'
>

export function createEditorStore(initialState: EditorInitialState) {
  return createStore<EditorState>()((set, get) => ({
    ...initialState,
    setProject: (project) => set({ project }),
    seek: (timeS) => {
      const durationS = get().project?.durationS ?? 0
      set({ currentTimeS: Math.min(Math.max(timeS, 0), durationS) })
    },
    select: (selection) => set({ selection }),
    setActiveTab: (activeTab) => set({ activeTab }),
    setOpenMenu: (openMenu) => set({ openMenu }),
  }))
}
