import { apiRequest } from "@/lib/api/client";
import type { CaptchaChallenge, LoginPayload, RegisterPayload, TokenPair, User } from "@/types";

export function getCaptchaChallenge(): Promise<CaptchaChallenge> {
  return apiRequest<CaptchaChallenge>("/auth/captcha", { method: "GET", auth: false });
}

export function register(payload: RegisterPayload): Promise<User> {
  return apiRequest<User>("/auth/register", { method: "POST", body: payload, auth: false });
}

export function login(payload: LoginPayload): Promise<TokenPair> {
  return apiRequest<TokenPair>("/auth/login", { method: "POST", body: payload, auth: false });
}

export function logout(refreshToken: string): Promise<void> {
  return apiRequest<void>("/auth/logout", {
    method: "POST",
    body: { refresh_token: refreshToken },
    auth: false,
  });
}

export function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/users/me", { method: "GET" });
}
