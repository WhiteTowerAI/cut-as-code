import { createRoot } from 'react-dom/client'
import { EditorShell } from './editor/EditorShell'
import './styles.css'

createRoot(document.getElementById('root')!).render(<EditorShell />)
