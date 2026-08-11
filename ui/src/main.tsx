import { createRoot } from 'react-dom/client'
import './styles.css'

function EditorShell() {
  return <main className="editor-shell" data-editor-shell aria-label="Video editor" />
}

createRoot(document.getElementById('root')!).render(<EditorShell />)
