import { apiFetch } from '../cloud'
import { demo } from './pages-demo'

export class ApiError extends Error {
  code: string
  detail: string
  constructor(code: string, detail = '') {
    super(code)
    this.code = code
    this.detail = detail
  }
}



async function handle<T>(res: Response): Promise<T> {
  let body: any = null
  try {
    body = await res.json()
  } catch {
    /* non-json */
  }
  if (!res.ok) {
    const code = body?.error?.code || (res.status===429?'LLM_RATE_LIMIT':res.status===402?'LLM_BALANCE':res.status === 504 ? 'LLM_TIMEOUT' : res.status >= 500 ? 'SERVER' : 'BAD_REQUEST')
    throw new ApiError(code, body?.error?.detail || '')
  }
  return body as T
}

export async function post<T>(path: string, data: unknown, signal?: AbortSignal): Promise<T> {
  if (import.meta.env.VITE_PAGES_DEMO === '1') return demo(path, data as Parameters<typeof demo>[1]) as T
  let res: Response
  try {
    res = await apiFetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal,
    })
  } catch (e: any) {
    if (e?.name === 'AbortError') throw new ApiError('ABORTED')
    throw new ApiError('NETWORK')
  }
  return handle<T>(res)
}

export async function get<T>(path: string): Promise<T> {
  if (import.meta.env.VITE_PAGES_DEMO === '1') return demo(path) as T
  let res: Response
  try {
    res = await apiFetch(path)
  } catch {
    throw new ApiError('NETWORK')
  }
  return handle<T>(res)
}

export async function del<T>(path: string): Promise<T> {
  if (import.meta.env.VITE_PAGES_DEMO === '1') return demo(path) as T
  let res: Response
  try {
    res = await apiFetch(path, { method: 'DELETE' })
  } catch {
    throw new ApiError('NETWORK')
  }
  return handle<T>(res)
}

export async function upload<T>(path: string, file: File, projectId="workspace"): Promise<T> {
  if (import.meta.env.VITE_PAGES_DEMO === '1') return demo(path) as T
  const fd = new FormData()
  fd.append('file', file)
  fd.append('project_id',projectId)
  let res: Response
  try {
    res = await apiFetch(path, { method: 'POST', body: fd })
  } catch {
    throw new ApiError('NETWORK')
  }
  return handle<T>(res)
}
