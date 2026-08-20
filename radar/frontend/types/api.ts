export type WorkMode = "REMOTE" | "HYBRID" | "ONSITE" | "UNKNOWN";
export type JobStatus = "ACTIVE" | "UNKNOWN" | "CLOSED";
export type UserJobState = "SAVED" | "IGNORED" | null;
export type ATSProvider = "GREENHOUSE" | "LEVER" | "ASHBY";
export type MonitoringPriority = "HIGH" | "NORMAL" | "LOW";
export type ProfileCoverageMode = "WATCHLIST" | "WIDE";
export type JobSourceKind = "DIRECT_ATS" | "WIDE_DISCOVERY";
export type AutomationState = "HEALTHY" | "DEGRADED" | "FAILED" | "STALE" | "RUNNING" | "UNKNOWN";

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
  max_job_age_days: number | null;
  include_unknown_posted_at: boolean;
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
  max_job_age_days: number | null;
  include_unknown_posted_at: boolean;
}

export interface JobListItem {
  id: string;
  company_id: string | null;
  company_name: string;
  ats_provider: ATSProvider | null;
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
  freshness_at: string | null;
  freshness_source: "POSTED_AT" | "DISCOVERY_SIGNAL" | "FIRST_SEEN" | "UNKNOWN";
  source_kind: JobSourceKind;
  source_provider: string | null;
  source_verified: boolean;
}

export interface MonitoringAutomationHealth {
  state: AutomationState;
  last_run_at: string | null;
  trigger: string | null;
  companies_selected: number;
  companies_succeeded: number;
  companies_failed: number;
  notifications_sent: number;
}

export interface WideAutomationHealth {
  state: AutomationState;
  last_run_at: string | null;
  trigger: string | null;
  signals_seen: number;
  signals_relevant: number;
  jobs_new: number;
  jobs_deduplicated: number;
  provider_failures: number;
  notifications_sent: number;
  warnings: string[];
}

export interface DashboardSummary {
  active_profiles: number;
  monitored_companies: number;
  watched_companies: number;
  jobs_discovered_today: number;
  wide_jobs_today: number;
  direct_jobs_today: number;
  matches_today: number;
  alerts_sent_today: number;
  last_successful_crawler_run: string | null;
  wide_jobs_unknown: number;
  monitoring_automation: MonitoringAutomationHealth;
  wide_search_automation: WideAutomationHealth;
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
  discovery_boost_until: string | null;
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

export interface TelegramTestResult {
  ok: boolean;
  message: string;
  telegram_message_id: string;
}

export interface TelegramDeliveryStatus {
  sent_today: number;
  pending: number;
  failed: number;
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

export type DiscoveryTargetStatus = "PENDING" | "SCANNING" | "COMPLETE" | "FAILED";
export type DiscoveryTargetOrigin = "USER" | "SYSTEM_FEED";
export type DiscoveryCandidateStatus = "DISCOVERED" | "VALIDATING" | "VALID" | "INVALID";

export interface DiscoveryTarget {
  id: string;
  submitted_by_user_id: string | null;
  url: string;
  origin: DiscoveryTargetOrigin;
  source_label: string | null;
  company_name_hint: string | null;
  signal_external_id: string | null;
  job_title_hint: string | null;
  job_location_hint: string | null;
  job_posted_at_hint: string | null;
  auto_watch: boolean;
  status: DiscoveryTargetStatus;
  scan_attempt_count: number;
  last_scanned_at: string | null;
  pages_scanned: number;
  sources_found: number;
  error_type: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourceCandidate {
  id: string;
  discovery_target_id: string | null;
  name_hint: string | null;
  ats_provider: ATSProvider;
  ats_identifier: string;
  career_url: string;
  source_url: string;
  status: DiscoveryCandidateStatus;
  validation_attempt_count: number;
  last_validated_at: string | null;
  last_revalidated_at: string | null;
  revalidation_failure_count: number;
  jobs_seen: number | null;
  error_type: string | null;
  error_message: string | null;
  promoted_company_id: string | null;
  promoted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DiscoverySummary {
  pending_targets: number;
  failed_targets: number;
  discovered_candidates: number;
  valid_candidates: number;
  invalid_candidates: number;
  promoted_candidates: number;
  system_targets: number;
  system_promoted_candidates: number;
  revalidation_failures: number;
  hiring_signal_targets: number;
  hiring_signal_promoted_sources: number;
  fresh_signal_jobs: number;
}

export interface WideSearchRefreshResult {
  profiles: number;
  queries: number;
  signals_seen: number;
  signals_relevant: number;
  jobs_new: number;
  jobs_updated: number;
  jobs_existing: number;
  jobs_deduplicated: number;
  matches_created: number;
  notifications_queued: number;
  notifications_sent: number;
  telegram_ready: boolean;
  targets_resolved: number;
  probe_candidates_staged: number;
  provider_failed: number;
  provider_warnings: string[];
  provider_successes: string[];
  provider_pages: number;
}
