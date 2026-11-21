import { useEffect, useState } from 'react'
import App from '../App'
import { AppProvider, initial } from '../lib/store'
import { lastProject, listProjects, readProject, rememberProject, saveProject, type Project, type SavedProject } from '../lib/projects'

async function openWorkspace() {
  const projects = await listProjects()
  if (projects.length) {
    const id = projects.find(p => p.id === lastProject())?.id || projects[0].id
    return { projects, current: await readProject(id) }
  }
  const state = initial
  const project = { id: 'first-project', name: state.lang === 'en' ? 'My first project' : state.lang === 'zh-TW' ? '我的第一個專案' : '我的第一个项目' }
  const current = { ...project, state, revision: 0 }
  try { current.revision = await saveProject(current) }
  catch (error) {
    // A concurrent first visit may already have created this workspace.
    const saved = await readProject(project.id).catch(() => { throw error })
    return { projects: await listProjects(), current: saved }
  }
  return { projects: [project], current }
}
export default function ProjectHost() {
  const [workspace, setWorkspace] = useState<{projects: Project[]; current: SavedProject}>()
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let mounted = true
    openWorkspace().then(w => mounted && setWorkspace(w)).catch(() => mounted && setFailed(true))
    return () => { mounted = false }
  }, [])
  if (!workspace) return <p role="status">{failed ? '项目存储不可用 · Browser storage unavailable' : 'Loading…'}</p>
  async function select(id: string, lang: SavedProject['state']['lang']) {
    const current = await readProject(id)
    rememberProject(id)
    setWorkspace(w => w && ({ ...w, current: { ...current, state: { ...current.state, entered: true, lang } } }))
  }
  async function create(name: string, lang: SavedProject['state']['lang']) {
    const project = { id: crypto.randomUUID(), name }
    const current = { ...project, revision: 0, state: { ...initial, entered: true, lang } }
    current.revision = await saveProject(current)
    rememberProject(project.id)
    setWorkspace(w => w && ({ projects: [...w.projects, project], current }))
  }
  return <AppProvider key={workspace.current.id} project={workspace.current} projects={workspace.projects} select={select} create={create}><App /></AppProvider>
}
