import { CompanyManager } from "@/components/company-manager";
import { PageHeader } from "@/components/page-header";
import { requireUser, serverRequest } from "@/lib/server-api";
import type { Company } from "@/types/api";

export default async function CompaniesPage() {
  const [user, companies] = await Promise.all([requireUser(), serverRequest<Company[]>("/api/v1/companies")]);
  return <><PageHeader eyebrow="Sources" title="Monitored companies" description={user.is_admin ? "Inspect ATS health, priorities, and add validated company sources." : "Inspect the ATS sources Radar currently monitors. Company changes are administrator-only."} /><CompanyManager initialCompanies={companies} isAdmin={user.is_admin} /></>;
}
