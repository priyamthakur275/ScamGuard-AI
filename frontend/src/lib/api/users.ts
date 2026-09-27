import { apiRequest } from "./client";
import type { User } from "@/types";

export interface UpdateProfileData {
  full_name?: string;
  preferences?: Record<string, unknown>;
}

export async function updateProfile(data: UpdateProfileData): Promise<User> {
  return apiRequest<User>("/users/me", {
    method: "PATCH",
    body: data,
  });
}

export async function updateAvatar(file: File): Promise<User> {
  const formData = new FormData();
  formData.append("file", file);
  return apiRequest<User>("/users/me/avatar", {
    method: "POST",
    body: formData,
  });
}

export async function changePassword(current_password: string, new_password: string): Promise<void> {
  return apiRequest<void>("/users/me/password", {
    method: "PATCH",
    body: { current_password, new_password },
  });
}

export async function deleteAccount(): Promise<void> {
  return apiRequest<void>("/users/me", {
    method: "DELETE",
  });
}

export async function exportUserData(): Promise<{ user: unknown; history: unknown[]; exported_at: string }> {
  return apiRequest<{ user: unknown; history: unknown[]; exported_at: string }>("/users/me/export", {
    method: "GET",
  });
}

export interface AdminStats {
  users_count: number;
  scans_count: number;
  threat_counts: {
    high: number;
    medium: number;
    low: number;
  };
}

export async function getAdminStats(): Promise<AdminStats> {
  return apiRequest<AdminStats>("/users/admin/stats");
}

export async function listUsers(skip = 0, limit = 50): Promise<User[]> {
  return apiRequest<User[]>(`/users?skip=${skip}&limit=${limit}`);
}
