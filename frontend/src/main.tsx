import { AuthGate } from './cloud'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import ProjectHost from './components/ProjectHost'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode><AuthGate>
    <ProjectHost />
  </AuthGate></StrictMode>,
)
