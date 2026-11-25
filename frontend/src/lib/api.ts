const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

const ACCESS_KEY = "agritwin_access_token";
const REFRESH_KEY = "agritwin_refresh_token";

export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown;

  constructor(message: string, status: number, code = "error", details: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!response.ok) return false;
        const data = await response.json();
        setTokens(data.access_token, data.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  rawBody?: BodyInit;
  auth?: boolean;
}

async function parseError(response: Response): Promise<ApiError> {
  let message = `Request failed with status ${response.status}`;
  let code = "http_error";
  let details: unknown = null;
  try {
    const payload = await response.json();
    if (payload?.error) {
      message = payload.error.message ?? message;
      code = payload.error.code ?? code;
      details = payload.error.details ?? null;
      if (Array.isArray(details) && details.length > 0) {
        const first = details[0] as { field?: string; message?: string };
        if (first?.message) {
          message = `${first.field ? `${first.field}: ` : ""}${first.message}`;
        }
      }
    } else if (payload?.detail) {
      message = typeof payload.detail === "string" ? payload.detail : message;
    }
  } catch {
    // Non-JSON response.
  }
  return new ApiError(message, response.status, code, details);
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, rawBody, auth = true, headers, ...rest } = options;

  const buildHeaders = (): HeadersInit => {
    const result: Record<string, string> = {
      Accept: "application/json",
      ...(headers as Record<string, string> | undefined),
    };
    if (body !== undefined) result["Content-Type"] = "application/json";
    if (auth) {
      const token = getAccessToken();
      if (token) result.Authorization = `Bearer ${token}`;
    }
    return result;
  };

  const execute = () =>
    fetch(`${API_BASE}${path}`, {
      ...rest,
      headers: buildHeaders(),
      body: body !== undefined ? JSON.stringify(body) : rawBody,
    });

  let response = await execute();

  if (response.status === 401 && auth) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      response = await execute();
    } else {
      clearTokens();
    }
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) return undefined as T;
  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export const api = {
  get: <T>(path: string) => apiRequest<T>(path),
  post: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => apiRequest<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData) =>
    apiRequest<T>(path, { method: "POST", rawBody: form }),
};
