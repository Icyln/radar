import { PageHeader } from "@/components/page-header";
import { ProfileManager } from "@/components/profile-manager";
import { serverRequest } from "@/lib/server-api";
import type { JobProfile } from "@/types/api";

export default async function ProfilesPage() {
  const profiles = await serverRequest<JobProfile[]>("/api/v1/job-profiles");
  return <><PageHeader eyebrow="Matching" title="Job profiles" description="Define deterministic title, location, work-mode, and exclusion rules. Enabled profiles are evaluated against collected jobs." /><ProfileManager initialProfiles={profiles} /></>;
}
