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
  const token = sessionStorage.getItem("career-project");
  const headers: Record<string, string> = {};
  if (token) headers["X-Project"] = token;
  const isFile = body instanceof Blob;
  if (body !== undefined)
    headers["Content-Type"] = isFile ? "application/pdf" : "application/json";
  const response = await fetch("/api/" + path, {
    method,
    headers,
    body: body === undefined ? undefined : isFile ? body : JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(data.errors || {}, response.status);
  }
  return response.json();
}
