import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { RiskLevel, Verdict } from "@/types";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function riskLevelLabel(level: RiskLevel): string {
  return { low: "Low risk", medium: "Medium risk", high: "High risk" }[level] ?? "Unknown risk";
}

export function verdictLabel(verdict: Verdict): string {
  return (
    {
      legitimate: "Legitimate",
      spam: "Spam",
      phishing: "Phishing",
      scam: "Scam",
    }[verdict] ?? "Unknown"
  );
}

export function scamCategoryLabel(category: string | null): string {
  if (!category) return "Uncategorized";
  const acronyms: Record<string, string> = { upi: "UPI", otp: "OTP", kyc: "KYC", sms: "SMS", url: "URL", qr: "QR", it: "IT" };
  return category
    .split("_")
    .map((word) => acronyms[word.toLowerCase()] ?? word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function inputTypeLabel(inputType: string | null | undefined): string {
  if (!inputType) return "Text";
  const labels: Record<string, string> = {
    TEXT: "Text",
    URL: "URL",
    EMAIL: "Email",
    IMAGE: "Image / OCR",
    PDF: "PDF",
    QR: "QR Code",
    CAMERA: "Camera",
    VOICE: "Voice call",
  };
  return labels[inputType.toUpperCase()] ?? inputType;
}

export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength).trimEnd()}\u2026`;
}

/**
 * Validates a post-login redirect target from the `?redirect=` query
 * param set by middleware.ts. Only a same-app relative path is ever
 * allowed; anything else (an absolute URL, or a protocol-relative URL
 * like "//evil.com" which browsers treat as a full origin change) is
 * rejected in favor of the given fallback. Without this check, a crafted
 * link like /login?redirect=https://evil.com or
 * /login?redirect=//evil.com would be an open-redirect vulnerability.
 */
export function getSafeRedirectPath(candidate: string | null, fallback = "/dashboard"): string {
  if (!candidate) return fallback;
  if (!candidate.startsWith("/") || candidate.startsWith("//")) return fallback;
  return candidate;
}

export function threatLevelLabel(level: string | null | undefined): string {
  if (!level) return "Unknown";
  const labels: Record<string, string> = {
    very_low: "Very Low",
    low: "Low",
    medium: "Medium",
    high: "High",
    critical: "Critical",
  };
  return labels[level] ?? "Unknown";
}

export function threatLevelColor(level: string | null | undefined): string {
  if (!level) return "text-muted-foreground";
  const colors: Record<string, string> = {
    very_low: "text-risk-very-low",
    low: "text-risk-low",
    medium: "text-risk-medium",
    high: "text-risk-high",
    critical: "text-risk-critical",
  };
  return colors[level] ?? "text-muted-foreground";
}

export function threatLevelBg(level: string | null | undefined): string {
  if (!level) return "bg-muted";
  const bgs: Record<string, string> = {
    very_low: "bg-risk-very-low/10 border-risk-very-low/30",
    low: "bg-risk-low/10 border-risk-low/30",
    medium: "bg-risk-medium/10 border-risk-medium/30",
    high: "bg-risk-high/10 border-risk-high/30",
    critical: "bg-risk-critical/10 border-risk-critical/30",
  };
  return bgs[level] ?? "bg-muted";
}

export function riskDimensionLabel(key: string): string {
  const labels: Record<string, string> = {
    urgency: "Urgency",
    financial_risk: "Financial Risk",
    credential_theft: "Credential Theft",
    identity_risk: "Identity Risk",
    social_engineering: "Social Engineering",
    suspicious_links: "Suspicious Links",
    malicious_tone: "Malicious Tone",
  };
  return labels[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function riskDimensionColor(score: number): string {
  if (score >= 0.7) return "bg-risk-high";
  if (score >= 0.4) return "bg-risk-medium";
  if (score > 0) return "bg-risk-low";
  return "bg-muted-foreground/20";
}
