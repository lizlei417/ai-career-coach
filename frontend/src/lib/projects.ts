import type { Persisted } from './store'

export interface Project { id: string; name: string }
export interface SavedProject extends Project { state: Persisted; revision: number }

const namespace = import.meta.env.VITE_PAGES_DEMO === '1' ? 'codex-demo-v2' : 'codex-v2'
const activeKey = namespace + '.active'
let connection: Promise<IDBDatabase> | undefined
function database() {
  if (!connection) connection = new Promise<IDBDatabase>((resolve, reject) => {
    const req = indexedDB.open(namespace, 1)
    req.onupgradeneeded = () => req.result.createObjectStore('projects', { keyPath: 'id' }).createIndex('name', 'name')
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
  return connection
}
export async function saveProject(project: SavedProject) {
  const db = await database()
  return new Promise<number>((resolve, reject) => {
    const tx = db.transaction('projects', 'readwrite')
    const store = tx.objectStore('projects')
    const check = store.get(project.id)
    check.onsuccess = () => {
      if ((check.result?.revision ?? 0) !== project.revision) { tx.abort(); return }
      store.put({ ...project, revision: project.revision + 1 })
    }
    tx.oncomplete = () => resolve(project.revision + 1)
    tx.onabort = () => reject(tx.error)
  })
}
export async function readProject(id: string) {
  const db = await database()
  return new Promise<SavedProject>((resolve, reject) => {
    const req = db.transaction('projects').objectStore('projects').get(id)
    req.onsuccess = () => req.result ? resolve(req.result) : reject(new Error('Missing project'))
    req.onerror = () => reject(req.error)
  })
}
export async function listProjects(): Promise<Project[]> {
  const db = await database()
  return new Promise((resolve, reject) => {
    const projects: Project[] = []
    const req = db.transaction('projects').objectStore('projects').index('name').openKeyCursor()
    req.onerror = () => reject(req.error)
    req.onsuccess = () => {
      const cursor = req.result
      if (!cursor) return resolve(projects)
      projects.push({ id: String(cursor.primaryKey), name: String(cursor.key) })
      cursor.continue()
    }
  })
}
export const lastProject = () => localStorage.getItem(activeKey)
export const rememberProject = (id: string) => localStorage.setItem(activeKey, id)
