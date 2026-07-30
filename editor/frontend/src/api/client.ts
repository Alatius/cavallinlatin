const API_ROOT = `${import.meta.env.BASE_URL}api`;

export class ApiError extends Error {
  /** HTTP status, or 0 when the request never reached the server. */
  status: number;
  detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

// Every caller renders failures into a Swedish UI, and most of them had this
// same line inlined. Centralised so a raw `TypeError: Failed to fetch` can't
// leak through as user-facing text.
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return String(err);
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
  let res: Response;
  try {
    res = await fetch(`${API_ROOT}${path}`, {
      // `rest` first: it must not be able to override the body and
      // credentials computed below from `json`.
      ...rest,
      credentials: 'include',
      headers: {
        ...(json !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
      body: json !== undefined ? JSON.stringify(json) : (rest.body as BodyInit | undefined),
    });
  } catch {
    // fetch only rejects when the request never completed. Callers all treat
    // failures as ApiError; a bare TypeError would otherwise be rendered
    // verbatim into the UI.
    throw new ApiError(0, 'Nätverksfel – kontrollera anslutningen');
  }
  if (!res.ok) {
    if (res.status === 401) unauthorizedHandler?.();
    const text = await res.text();
    let detail: unknown = text;
    try { detail = JSON.parse(text); } catch { /* plain text */ }
    // FastAPI's `detail` is a string for most errors but an object for some
    // (the lock 409 carries the winning LockInfo). Only use it as the
    // message when it really is a string, or Error stringifies it to
    // "[object Object]".
    const d = (detail as { detail?: unknown } | null)?.detail;
    const message = typeof d === 'string' ? d : res.statusText || `HTTP ${res.status}`;
    throw new ApiError(res.status, message, detail);
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
