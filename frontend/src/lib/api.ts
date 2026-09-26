// Small typed fetch wrapper around the FastAPI backend (proxied at /api by Vite).

const TOKEN_KEY = "shopsense.token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode): the session just won't persist */
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** FastAPI errors are `{detail: string}` or, for validation, `{detail: [{msg, loc}]}`. */
function readableDetail(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d: { msg?: string }) => (d.msg ?? "").replace(/^Value error, /, ""))
        .filter(Boolean)
        .join(". ");
    }
  }
  return fallback;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  json?: unknown;
  form?: Record<string, string>;
}

export async function api<T>(path: string, { method = "GET", json, form }: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = new URLSearchParams(form);
  }

  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { method, headers, body });
  } catch {
    throw new ApiError(0, "Can't reach ShopSense. Check your connection and try again.");
  }

  const data: unknown = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && token) {
      setToken(null);
      window.dispatchEvent(new Event("shopsense:logout"));
    }
    throw new ApiError(response.status, readableDetail(data, `Something went wrong (${response.status})`));
  }
  return data as T;
}
