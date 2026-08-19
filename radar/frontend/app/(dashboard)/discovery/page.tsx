import { DiscoveryManager } from "@/components/discovery-manager";
import { PageHeader } from "@/components/page-header";
import { requireUser, serverRequest } from "@/lib/server-api";
import type { DiscoverySummary, DiscoveryTarget, SourceCandidate } from "@/types/api";

export default async function DiscoveryPage() {
  const user = await requireUser();
  const [targets, candidates, summary] = await Promise.all([
    serverRequest<DiscoveryTarget[]>(user.is_admin ? "/api/v1/discovery/targets?include_all=true" : "/api/v1/discovery/targets"),
    user.is_admin ? serverRequest<SourceCandidate[]>("/api/v1/discovery/candidates") : Promise.resolve([]),
    user.is_admin ? serverRequest<DiscoverySummary>("/api/v1/discovery/summary") : Promise.resolve(null)
  ]);

  return <>
    <PageHeader
      eyebrow="Coverage"
      title="Source discovery"
      description="Radar grows its source registry automatically from system-managed feeds, while still letting users request specific companies. Every source is validated before promotion."
    />
    <DiscoveryManager
      initialTargets={targets}
      initialCandidates={candidates}
      initialSummary={summary}
      isAdmin={user.is_admin}
    />
  </>;
}
