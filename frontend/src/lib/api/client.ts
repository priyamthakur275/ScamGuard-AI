import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "@/lib/auth/token-storage";
import type { ApiErrorBody, TokenPair } from "@/types";

export class ApiError extends Error {
  readonly status: number;
  readonly errorCode: string;
  readonly details?: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = body.error_code;
    this.details = body.details;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  auth?: boolean;
  /** Base URL override; defaults to the app_service base URL. */
  baseUrl?: string;
}

// These are same-origin paths, rewritten server-side to the real backend
// URLs by next.config.js's rewrites() -- see that file for why.
const APP_API_URL = "/backend-api/api/v1";
const API_TIMEOUT_MS = 45000;

let refreshPromise: Promise<TokenPair | null> | null = null;

function fetchWithTimeout(input: RequestInfo, init: RequestInit = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  return fetch(input, { ...init, signal: controller.signal }).finally(() => clearTimeout(timeoutId));
}

async function performRefresh(): Promise<TokenPair | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const response = await fetchWithTimeout(`${APP_API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      clearTokens();
      return null;
    }
    const pair = (await response.json()) as TokenPair;
    setTokens(pair);
    return pair;
  } catch {
    clearTokens();
    return null;
  }
}

/** Ensures only one refresh request is ever in flight at a time, even if
 * several API calls hit a 401 simultaneously.
 */
function refreshOnce(): Promise<TokenPair | null> {
  if (!refreshPromise) {
    refreshPromise = performRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function parseErrorBody(response: Response): Promise<ApiErrorBody> {
  try {
    const data = await response.json();
    if (data && typeof data.message === "string") {
      return data as ApiErrorBody;
    }
    if (data && typeof data.detail === "string") {
      return { error_code: "VALIDATION_ERROR", message: data.detail };
    }
    if (data && Array.isArray(data.detail) && data.detail.length > 0 && typeof data.detail[0].msg === "string") {
      return { error_code: "VALIDATION_ERROR", message: data.detail[0].msg };
    }
    return { error_code: "UNKNOWN_ERROR", message: "An unexpected error occurred." };
  } catch {
    if (response.status >= 500) {
      return {
        error_code: "SERVICE_UNAVAILABLE",
        message: "The backend server is starting up or temporarily busy. Please wait a moment and try again.",
      };
    }
    return { error_code: "UNKNOWN_ERROR", message: `Request failed with status ${response.status}.` };
  }
}

function mapFetchError(error: unknown): never {
  if (error instanceof DOMException && error.name === "AbortError") {
    throw new ApiError(0, {
      error_code: "REQUEST_TIMEOUT",
      message: "The backend server is waking up from standby or taking longer than usual. Please wait a moment and try again.",
    });
  }

  // Raw browser messages ("Failed to fetch", "NetworkError when attempting
  // to fetch resource") are not actionable for users.
  void error;
  throw new ApiError(0, {
    error_code: "NETWORK_ERROR",
    message: "Could not reach the ScamGuard service. Check that the backend is running and try again.",
  });
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true, baseUrl = APP_API_URL } = options;

  const doFetch = async (urlBase: string): Promise<Response> => {
    const headers: Record<string, string> = {};
    if (!(body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    if (auth) {
      const token = getAccessToken();
      if (token) headers.Authorization = `Bearer ${token}`;
    }
    return fetchWithTimeout(`${urlBase}${path}`, {
      method,
      headers,
      body: body !== undefined ? (body instanceof FormData ? body : JSON.stringify(body)) : undefined,
    });
  };

  let response: Response | undefined;
  try {
    response = await doFetch(baseUrl);
  } catch (error) {
    mapFetchError(error);
  }

  if (!response) {
    throw new ApiError(0, {
      error_code: "NETWORK_ERROR",
      message: "Unable to connect to ScamGuard backend service. Please try again in a few seconds.",
    });
  }

  if (response.status === 401 && auth && getRefreshToken()) {
    const refreshed = await refreshOnce();
    if (refreshed) {
      try {
        response = await doFetch(baseUrl);
      } catch (error) {
        mapFetchError(error);
      }
    }
  }

  if (!response.ok) {
    const errorBody = await parseErrorBody(response);
    if (response.status === 401 && auth) {
      // A genuinely authenticated request came back unauthorized even
      // after the refresh attempt above -- the session is dead (expired,
      // revoked, or the token was never valid). Clear it and send the
      // user back to login instead of leaving them on a protected page
      // that will just keep showing this same raw backend error on every
      // retry. Scoped to `auth: true` requests only: a 401 from a plain
      // login/register attempt (wrong password) is not a session expiry
      // and must not bounce the user off the login page.
      clearTokens();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
      }
    }
    throw new ApiError(response.status, errorBody);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/**
 * Authenticated request that returns the raw Response (for binary downloads
 * such as reports). Uses the same bearer token and one-shot refresh-on-401
 * as apiRequest, so exports keep working after the short-lived access
 * token expires.
 */
export async function authorizedFetch(path: string): Promise<Response> {
  const doFetch = () => {
    const token = getAccessToken();
    return fetchWithTimeout(`${APP_API_URL}${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  };
  let response: Response;
  try {
    response = await doFetch();
    if (response.status === 401 && getRefreshToken() && (await refreshOnce())) {
      response = await doFetch();
    }
  } catch (error) {
    mapFetchError(error);
  }
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorBody(response));
  }
  return response;
}

/** Saves a Blob via a temporary object URL. The URL is revoked on a delay:
 * revoking synchronously after click() can cancel the download in some
 * browsers. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export { APP_API_URL };
