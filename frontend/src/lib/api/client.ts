import type { ApiError } from "@/types/api"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail)
    this.name = "ApiRequestError"
  }
}

function extractDetail(body: ApiError | unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as ApiError).detail
    if (typeof d === "string") return d
    if (Array.isArray(d)) return d.map((e) => e.msg).join("; ")
  }
  return "An unexpected error occurred."
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`

  // Don't set Content-Type for FormData — the browser sets multipart/form-data with boundary
  const isFormData = init.body instanceof FormData
  const res = await fetch(url, {
    ...init,
    credentials: "include", // always send zima_session httpOnly cookie
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(init.headers ?? {}),
    },
  })

  if (res.status === 401) {
    // Let middleware / layout handle redirect — just throw so callers know
    throw new ApiRequestError(401, "Unauthenticated")
  }

  if (!res.ok) {
    let body: unknown
    try { body = await res.json() } catch { body = null }
    throw new ApiRequestError(res.status, extractDetail(body))
  }

  // 204 No Content
  if (res.status === 204) return undefined as T

  return res.json() as Promise<T>
}

// ─── Convenience methods ──────────────────────────────────────────────────────

export const api = {
  get<T>(path: string, init?: RequestInit) {
    return request<T>(path, { method: "GET", ...init })
  },
  post<T>(path: string, body?: unknown, init?: RequestInit) {
    return request<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...init,
    })
  },
  patch<T>(path: string, body?: unknown, init?: RequestInit) {
    return request<T>(path, {
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
      ...init,
    })
  },
  postForm<T>(path: string, form: FormData, init?: RequestInit) {
    return request<T>(path, { method: "POST", body: form, ...init })
  },
  delete<T>(path: string, init?: RequestInit) {
    return request<T>(path, { method: "DELETE", ...init })
  },
}
