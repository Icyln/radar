import { PageHeader } from "@/components/page-header";
import { ProfileManager } from "@/components/profile-manager";
import { serverRequest } from "@/lib/server-api";
import type { CompanyWatchlistEntry, JobProfile } from "@/types/api";

export default async function ProfilesPage() {
  const [profiles, watchlist] = await Promise.all([
    serverRequest<JobProfile[]>("/api/v1/job-profiles"),
    serverRequest<CompanyWatchlistEntry[]>("/api/v1/companies/watchlist")
  ]);
  return <><PageHeader eyebrow="Job Alerts" title="Job Alerts" description="Tell Radar what you want to find. Keep each alert focused and let Radar do the repeated checking." /><ProfileManager initialProfiles={profiles} watchlistCount={watchlist.length} /></>;
}
