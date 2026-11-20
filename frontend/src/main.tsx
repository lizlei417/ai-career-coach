import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import ProjectHost from './components/ProjectHost'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ProjectHost />
  </StrictMode>,
)
