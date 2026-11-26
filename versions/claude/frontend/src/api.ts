import {apiFetch,ownerKey} from './cloud'
import { demoApi } from "./pages-demo";
import type { Lang } from "./types";
export class ApiError extends Error {
  constructor(
    public messages: Partial<Record<Lang, string>>,
    public status: number,
  ) {
    super("Request failed");
  }
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  if (import.meta.env.VITE_PAGES_DEMO === "1") return demoApi(path, method, body) as T;
  const token = sessionStorage.getItem(ownerKey("career-project"));
  const headers: Record<string, string> = {};
  if (token) headers["X-Project"] = token;
  const isFile = body instanceof Blob;
  if (body !== undefined)
    headers["Content-Type"] = isFile ? "application/pdf" : "application/json";
  const response = await apiFetch("/api/" + path, {
    method,
    headers,
    body: body === undefined ? undefined : isFile ? body : JSON.stringify(body),
    cache: "no-store",
  });
  if(method!=="GET")window.dispatchEvent(new Event("quota-update"));
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(data.detail==='DAILY_LIMIT'?{'zh-CN':'今日免费次数已用完，明天可以继续使用。','zh-TW':'今日免費次數已用完，明天可以繼續使用。',en:'Today’s free calls are used up. Please come back tomorrow.'}:data.errors || {}, response.status);
  }
  return response.json();
}
