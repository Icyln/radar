export type WorkMode = "REMOTE" | "HYBRID" | "ONSITE" | "UNKNOWN";
export type JobStatus = "ACTIVE" | "UNKNOWN" | "CLOSED";
export type UserJobState = "SAVED" | "IGNORED" | null;
export type ATSProvider = "GREENHOUSE" | "LEVER" | "ASHBY";
export type MonitoringPriority = "HIGH" | "NORMAL" | "LOW";
export type ProfileCoverageMode = "WATCHLIST" | "WIDE";

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface AuthResult {
  user: User;
}

export interface JobProfile {
  id: string;
  user_id: string;
  name: string;
  enabled: boolean;
  coverage_mode: ProfileCoverageMode;
  job_titles: string[];
  locations: string[];
  work_modes: WorkMode[];
  excluded_keywords: string[];
  created_at: string;
  updated_at: string;
}

export interface JobProfilePayload {
  name: string;
  enabled: boolean;
  coverage_mode: ProfileCoverageMode;
  job_titles: string[];
  locations: string[];
  work_modes: WorkMode[];
  excluded_keywords: string[];
}

export interface JobListItem {
  id: string;
  company_id: string;
  company_name: string;
  title: string;
  location: string | null;
  work_mode: WorkMode;
  employment_type: string | null;
  apply_url: string;
  source_url: string;
  posted_at: string | null;
  first_seen_at: string;
  last_seen_at: string;
  status: JobStatus;
  closed_at: string | null;
  user_state: UserJobState;
}

export interface DashboardSummary {
  active_profiles: number;
  monitored_companies: number;
  watched_companies: number;
  jobs_discovered_today: number;
  matches_today: number;
  alerts_sent_today: number;
  last_successful_crawler_run: string | null;
  recent_matching_jobs: JobListItem[];
}

export interface Company {
  id: string;
  name: string;
  website: string | null;
  career_url: string;
  ats_provider: ATSProvider;
  ats_identifier: string;
  monitoring_priority: MonitoringPriority;
  active: boolean;
  last_checked_at: string | null;
  last_successful_check_at: string | null;
  last_error_at: string | null;
  consecutive_failures: number;
  created_at: string;
  updated_at: string;
}

export interface CompanyPayload {
  name: string;
  website: string | null;
  career_url: string;
  ats_provider: ATSProvider;
  ats_identifier: string;
  monitoring_priority: MonitoringPriority;
  active: boolean;
}

export interface TelegramConnection {
  id: string;
  telegram_user_id: number;
  telegram_chat_id: number;
  username: string | null;
  verified: boolean;
  connected_at: string;
}

export interface TelegramLink {
  deep_link: string;
  expires_at: string;
}

export interface CompanyWatchlistEntry {
  id: string;
  user_id: string;
  company_id: string;
  created_at: string;
  updated_at: string;
}

export interface DetectedJobPage {
  items: JobListItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}
