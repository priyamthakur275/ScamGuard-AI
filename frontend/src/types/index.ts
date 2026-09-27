// ---- Auth / Users (app_service) ----------------------------------------

export type UserRole = "user" | "admin";

export interface User {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  preferences?: Record<string, unknown>;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginPayload {
  email: string;
  password: string;
  captcha_token?: string;
  captcha_answer?: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  captcha_token: string;
  captcha_answer: string;
}

export interface CaptchaChallenge {
  question: string;
  token: string;
}

export interface AnalyticsSummary {
  range: "24h" | "7d" | "30d" | "all";
  total_scans: number;
  verdict_distribution: Record<string, number>;
  risk_distribution: Record<string, number>;
  category_distribution: Record<string, number>;
  input_type_distribution: Record<string, number>;
  feedback_accurate: number;
  feedback_inaccurate: number;
  feedback_pending: number;
  high_risk_count: number;
  average_confidence: number;
  average_threat_score: number;
}

// ---- Prediction (ml_service, via app_service proxy) ---------------------

export type Verdict = "legitimate" | "spam" | "phishing" | "scam";
export type RiskLevel = "low" | "medium" | "high";
export type ThreatLevel = "very_low" | "low" | "medium" | "high" | "critical";

export interface FeatureContribution {
  token: string;
  weight: number;
}

/** Result of a message analysis, persisted server-side by app_service
 * (backend/app_service/api/v1/messages.py) rather than in localStorage.
 */
export interface UrlIntelligenceEvidence {
  code: string;
  severity: "low" | "medium" | "high";
  reason: string;
}

export type CorrelationSignal = UrlIntelligenceEvidence;

export interface UrlIntelligence {
  original_url: string;
  scheme: string;
  hostname: string;
  port: number | null;
  path: string;
  query: string;
  fragment: string;
  registrable_domain: string;
  url_length: number;
  is_punycode: boolean;
  is_ip_literal: boolean;
  ip_version: number | null;
  is_shortened: boolean;
  is_suspicious_tld: boolean;
  has_userinfo_obfuscation: boolean;
  has_percent_encoding: boolean;
  subdomain_depth: number;
  hostname_length: number;
  digit_ratio_in_hostname: number;
  hyphen_count_in_hostname: number;
  lookalike_of: string | null;
  lookalike_distance: number | null;
  suspicious_path_keywords: string[];
  suspicious_query_params: string[];
  evidence: UrlIntelligenceEvidence[];
  redirect_count?: number;
  redirect_chain?: Array<{ url: string; status_code: number }>;
  resolved_ips?: string[];
  tls?: { subject_cn: string | null; issuer_cn: string | null; not_after: string | null; is_expired: boolean | null } | null;
}

export interface EmailEvidenceSignal {
  code: string;
  severity: "low" | "medium" | "high";
  reason: string;
}

export interface EmailForensics {
  headers: {
    from_address: string | null;
    from_domain: string | null;
    to_address: string | null;
    reply_to: string | null;
    reply_to_domain: string | null;
    return_path: string | null;
    return_path_domain: string | null;
    subject: string | null;
    date: string | null;
    message_id: string | null;
    received_chain: string[];
    spf: string;
    dkim: string;
    dmarc: string;
    authentication_results_raw: string | null;
  };
  header_evidence: EmailEvidenceSignal[];
  content_evidence: EmailEvidenceSignal[];
  url_evidence: Record<string, UrlIntelligence>;
  attachments: Array<{ filename: string | null; content_type: string | null; size_bytes: number }>;
  attachment_evidence: EmailEvidenceSignal[];
}

export interface VoiceEvidenceSignal {
  code: string;
  severity: "low" | "medium" | "high";
  reason: string;
}

export interface AnalysisResult {
  id: string;
  text: string;
  input_type?: string | null;
  /** Raw extraction metadata -- e.g. { url_intelligence: UrlIntelligence, ... }
   * for URL scans. Real, computed data already flowing through the backend
   * pipeline; this type just lets the frontend actually use it. */
  metadata?: Record<string, unknown> | null;
  verdict: Verdict;
  scam_probability: number;
  risk_level: RiskLevel;
  scam_category: string | null;
  confidence_score: number;
  threat_score: number;
  top_contributing_tokens: FeatureContribution[];
  model_name: string;
  model_version: string;
  latency_ms: number;
  user_feedback: boolean | null;
  created_at: string;
  ai_explanation?: string | null;
  executive_summary?: string | null;
  technical_explanation?: string | null;
  threat_level?: ThreatLevel | null;
  risk_breakdown?: Record<string, number> | null;
  recommended_actions?: string[] | null;
  highlighted_entities?: {
    urls?: string[];
    emails?: string[];
    phones?: string[];
    upi_ids?: string[];
    shortened_links?: string[];
    crypto_wallets?: string[];
    payment_amounts?: string[];
    bank_references?: string[];
    dates?: string[];
    organizations?: string[];
  } | null;
  similar_patterns?: Array<{ title: string; description: string }> | null;
}

// ---- API error shape (matches both app_service and ml_service) ----------

export interface ApiErrorBody {
  error_code: string;
  message: string;
  details?: unknown;
}
