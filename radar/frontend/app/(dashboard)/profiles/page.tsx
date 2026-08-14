import { PageHeader } from "@/components/page-header";
import { ProfileManager } from "@/components/profile-manager";
import { serverRequest } from "@/lib/server-api";
import type { CompanyWatchlistEntry, JobProfile } from "@/types/api";

export default async function ProfilesPage() {
  const [profiles, watchlist] = await Promise.all([
    serverRequest<JobProfile[]>("/api/v1/job-profiles"),
    serverRequest<CompanyWatchlistEntry[]>("/api/v1/companies/watchlist")
  ]);
  return <><PageHeader eyebrow="Matching" title="Job profiles" description="Define deterministic role rules, then choose Wide Search across Radar's registry or Watchlist-only coverage." /><ProfileManager initialProfiles={profiles} watchlistCount={watchlist.length} /></>;
}
