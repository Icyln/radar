import { redirect } from "next/navigation";
import { DiscoveryManager } from "@/components/discovery-manager";
import { PageHeader } from "@/components/page-header";
import { requireUser, serverRequest } from "@/lib/server-api";
import type { DiscoverySummary, DiscoveryTarget, SourceCandidate } from "@/types/api";

export default async function AdminDiscoveryPage() {
  const user = await requireUser();
  if (!user.is_admin) redirect("/companies#request-company");

  const [targets, candidates, summary] = await Promise.all([
    serverRequest<DiscoveryTarget[]>("/api/v1/discovery/targets?include_all=true"),
    serverRequest<SourceCandidate[]>("/api/v1/discovery/candidates"),
    serverRequest<DiscoverySummary>("/api/v1/discovery/summary")
  ]);

  return <>
    <PageHeader eyebrow="Admin" title="Source discovery" description="Inspect company-source requests, automated discovery, validation, and promotion into Radar's monitored company registry." />
    <DiscoveryManager initialTargets={targets} initialCandidates={candidates} initialSummary={summary} isAdmin />
  </>;
}
