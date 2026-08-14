import { CompanyManager } from "@/components/company-manager";
import { PageHeader } from "@/components/page-header";
import { requireUser, serverRequest } from "@/lib/server-api";
import type { Company, CompanyWatchlistEntry } from "@/types/api";

export default async function CompaniesPage() {
  const [user, companies, watchlist] = await Promise.all([
    requireUser(),
    serverRequest<Company[]>("/api/v1/companies"),
    serverRequest<CompanyWatchlistEntry[]>("/api/v1/companies/watchlist")
  ]);
  return <><PageHeader eyebrow="Sources" title="Company registry" description={user.is_admin ? "Watch priority companies, inspect ATS health, and manage validated sources. Wide Search profiles can match the full active registry." : "Choose companies for your personal watchlist and inspect the ATS sources Radar currently monitors."} /><CompanyManager initialCompanies={companies} initialWatchlistIds={watchlist.map((item) => item.company_id)} isAdmin={user.is_admin} /></>;
}
