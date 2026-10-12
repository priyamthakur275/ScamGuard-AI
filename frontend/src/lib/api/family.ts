import { apiRequest } from "@/lib/api/client";

export interface FamilyLink {
  id: string;
  status: "pending" | "active" | "declined";
  created_at: string | null;
  email: string | null;
  name: string | null;
}

export interface FamilyAlert {
  id: string;
  link_id: string;
  person: string;
  person_email: string | null;
  created_at: string | null;
  threat_score: number;
  scam_category: string | null;
  input_type: string | null;
  preview: string;
}

export const inviteGuardian = (email: string) =>
  apiRequest<FamilyLink>("/family/guardians", { method: "POST", body: { email } });
export const listGuardians = () => apiRequest<FamilyLink[]>("/family/guardians");
export const listProtecting = () => apiRequest<FamilyLink[]>("/family/protecting");
export const acceptLink = (id: string) => apiRequest<FamilyLink>(`/family/links/${id}/accept`, { method: "POST" });
export const declineLink = (id: string) => apiRequest<FamilyLink>(`/family/links/${id}/decline`, { method: "POST" });
export const removeLink = (id: string) => apiRequest<void>(`/family/links/${id}`, { method: "DELETE" });
export const listFamilyAlerts = () => apiRequest<FamilyAlert[]>("/family/alerts");
export const familySummary = () =>
  apiRequest<{ pending_invitations: number; recent_alerts: number }>("/family/summary");
