export class ApiError extends Error {
  code: string
  detail: string
  constructor(code: string, detail = '') {
    super(code)
    this.code = code
    this.detail = detail
  }
}

const BASE = (import.meta as any).env?.VITE_API_BASE ?? ''

async function handle<T>(res: Response): Promise<T> {
  let body: any = null
  try {
    body = await res.json()
  } catch {
    /* non-json */
  }
  if (!res.ok) {
    const code = body?.error?.code || (res.status === 504 ? 'LLM_TIMEOUT' : res.status >= 500 ? 'SERVER' : 'BAD_REQUEST')
    throw new ApiError(code, body?.error?.detail || '')
  }
  return body as T
}

export async function post<T>(path: string, data: unknown, signal?: AbortSignal): Promise<T> {
  let res: Response
  try {
    res = await fetch(BASE + path, {
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
  let res: Response
  try {
    res = await fetch(BASE + path)
  } catch {
    throw new ApiError('NETWORK')
  }
  return handle<T>(res)
}

export async function del<T>(path: string): Promise<T> {
  let res: Response
  try {
    res = await fetch(BASE + path, { method: 'DELETE' })
  } catch {
    throw new ApiError('NETWORK')
  }
  return handle<T>(res)
}

export async function upload<T>(path: string, file: File): Promise<T> {
  const fd = new FormData()
  fd.append('file', file)
  let res: Response
  try {
    res = await fetch(BASE + path, { method: 'POST', body: fd })
  } catch {
    throw new ApiError('NETWORK')
  }
  return handle<T>(res)
}
