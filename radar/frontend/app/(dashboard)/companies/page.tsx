import { CompanyManager } from "@/components/company-manager";
import { CompanyRequest } from "@/components/company-request";
import { PageHeader } from "@/components/page-header";
import { requireUser, serverRequest } from "@/lib/server-api";
import type { Company, CompanyWatchlistEntry, DiscoveryTarget } from "@/types/api";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;
function first(value: string | string[] | undefined) { return Array.isArray(value) ? value[0] : value; }

export default async function CompaniesPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const q = (first(params.q) ?? "").trim();
  const [user, companies, watchlist, requests] = await Promise.all([
    requireUser(),
    serverRequest<Company[]>(`/api/v1/companies?limit=100${q ? `&q=${encodeURIComponent(q)}` : ""}`),
    serverRequest<CompanyWatchlistEntry[]>("/api/v1/companies/watchlist"),
    serverRequest<DiscoveryTarget[]>("/api/v1/discovery/targets")
  ]);
  return <>
    <PageHeader eyebrow="Companies" title="Companies" description="Follow employers you care about. Your normal Job Alerts can still search broadly even when you follow none." />
    <form className="mb-5 flex max-w-xl gap-2" method="get" action="/companies"><input className="input" type="search" name="q" defaultValue={q} placeholder="Search companies"/><button className="button-secondary" type="submit">Search</button></form>
    <CompanyManager initialCompanies={companies} initialWatchlistIds={watchlist.map((item) => item.company_id)} isAdmin={user.is_admin} />
    <div className="mt-7"><CompanyRequest initialTargets={requests} /></div>
  </>;
}
