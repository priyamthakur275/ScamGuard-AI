import type { TokenPair, User } from "@/types";

const ACCESS_TOKEN_KEY = "scam_detection_access_token";
const REFRESH_TOKEN_KEY = "scam_detection_refresh_token";
const USER_CACHE_KEY = "scam_detection_user";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

const SESSION_FLAG_COOKIE = "has_session";

function setSessionFlagCookie(): void {
  if (!isBrowser()) return;
  // 7 days, matching the backend's REFRESH_TOKEN_EXPIRE_DAYS default.
  document.cookie = `${SESSION_FLAG_COOKIE}=1; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
}

function clearSessionFlagCookie(): void {
  if (!isBrowser()) return;
  document.cookie = `${SESSION_FLAG_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}

export function getAccessToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getCachedUser(): User | null {
  if (!isBrowser()) return null;
  try {
    const raw = window.localStorage.getItem(USER_CACHE_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export function setCachedUser(user: User): void {
  if (!isBrowser()) return;
  try {
    window.localStorage.setItem(USER_CACHE_KEY, JSON.stringify(user));
  } catch {}
}

export function clearCachedUser(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(USER_CACHE_KEY);
}

export function setTokens(pair: TokenPair): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, pair.access_token);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, pair.refresh_token);
  setSessionFlagCookie();
}

export function clearTokens(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  clearCachedUser();
  clearSessionFlagCookie();
}

export function hasSession(): boolean {
  return getAccessToken() !== null;
}
