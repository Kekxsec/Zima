import type { ApiError } from "@/types/api"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
const UPLOAD_BASE_URL = process.env.NEXT_PUBLIC_API_UPLOAD_URL ?? ""

export interface UploadProgress {
  loaded: number
  total: number | null
  percent: number | null
}

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
  const url = buildUrl(BASE_URL, path)

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

function buildUrl(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/$/, "")}${path}`
}


function resolveUploadBaseUrl(): string {
  return UPLOAD_BASE_URL || BASE_URL
}

function parseResponseBody(text: string): unknown {
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function buildXhrError(xhr: XMLHttpRequest): ApiRequestError {
  const body = parseResponseBody(xhr.responseText)

  if (xhr.status === 401) {
    return new ApiRequestError(401, "Unauthenticated")
  }

  if (xhr.status > 0) {
    return new ApiRequestError(xhr.status, extractDetail(body))
  }

  return new ApiRequestError(
    0,
    "Network error. The upload may have been blocked before reaching the server.",
  )
}

function requestFormWithProgress<T>(
  path: string,
  form: FormData,
  onProgress?: (progress: UploadProgress) => void,
): Promise<T> {
  const url = buildUrl(resolveUploadBaseUrl(), path)

  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open("POST", url)
    xhr.withCredentials = true

    xhr.upload.onprogress = (event) => {
      if (!onProgress) return
      const total = event.lengthComputable ? event.total : null
      const percent =
        total && total > 0
          ? Math.min(100, Math.round((event.loaded / total) * 100))
          : null
      onProgress({ loaded: event.loaded, total, percent })
    }

    xhr.onerror = () => {
      reject(buildXhrError(xhr))
    }

    xhr.onabort = () => {
      reject(new ApiRequestError(0, "Upload canceled."))
    }

    xhr.onload = () => {
      const body = parseResponseBody(xhr.responseText)

      if (xhr.status === 401) {
        reject(new ApiRequestError(401, "Unauthenticated"))
        return
      }

      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new ApiRequestError(xhr.status, extractDetail(body)))
        return
      }

      if (onProgress) {
        onProgress({
          loaded: 1,
          total: 1,
          percent: 100,
        })
      }

      resolve((body ?? undefined) as T)
    }

    xhr.send(form)
  })
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
  put<T>(path: string, body?: unknown, init?: RequestInit) {
    return request<T>(path, {
      method: "PUT",
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
  postFormWithProgress<T>(
    path: string,
    form: FormData,
    onProgress?: (progress: UploadProgress) => void,
  ) {
    return requestFormWithProgress<T>(path, form, onProgress)
  },
  async postFileChunked<T>(
    path: string,
    file: File,
    chunkSize: number = 2 * 1024 * 1024,
    onProgress?: (progress: UploadProgress) => void,
  ): Promise<T> {
    const token = crypto.randomUUID()
    const totalChunks = Math.max(1, Math.ceil(file.size / chunkSize))
    let result: unknown
    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize
      const end = Math.min(start + chunkSize, file.size)
      const form = new FormData()
      form.append("token", token)
      form.append("index", String(i))
      form.append("total", String(totalChunks))
      form.append("filename", file.name)
      form.append("chunk", file.slice(start, end), file.name)
      result = await request<unknown>(`${path}/chunked`, { method: "POST", body: form })
      onProgress?.({
        loaded: end,
        total: file.size,
        percent: Math.round((end / file.size) * 100),
      })
    }
    return result as T
  },
  delete<T>(path: string, init?: RequestInit) {
    return request<T>(path, { method: "DELETE", ...init })
  },
}
