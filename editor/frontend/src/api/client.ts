const API_ROOT = `${import.meta.env.BASE_URL}api`;

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

// AuthContext registers a handler here so that any 401 from any API call
// invalidates the local user state, which bounces the user to the login page
// via RequireAuth. Avoids leaking session-expired failures into individual
// feature code.
let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(fn: (() => void) | null): void {
  unauthorizedHandler = fn;
}

type RequestOpts = RequestInit & { json?: unknown };

async function sendRaw(path: string, init?: RequestOpts): Promise<Response> {
  const { json, headers, ...rest } = init ?? {};
  const res = await fetch(`${API_ROOT}${path}`, {
    credentials: 'include',
    headers: {
      ...(json !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : (rest.body as BodyInit | undefined),
    ...rest,
  });
  if (!res.ok) {
    if (res.status === 401) unauthorizedHandler?.();
    const text = await res.text();
    let detail: unknown = text;
    try { detail = JSON.parse(text); } catch { /* plain text */ }
    throw new ApiError(res.status, (detail as { detail?: string })?.detail ?? res.statusText, detail);
  }
  return res;
}

async function request<T>(path: string, init?: RequestOpts): Promise<T> {
  const res = await sendRaw(path, init);
  const text = await res.text();
  if (res.status === 204 || !text) return undefined as T;
  try { return JSON.parse(text) as T; }
  catch { return text as unknown as T; }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', json: body }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', json: body }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};
