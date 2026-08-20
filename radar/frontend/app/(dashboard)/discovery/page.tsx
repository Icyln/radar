import { redirect } from "next/navigation";
import { requireUser } from "@/lib/server-api";

export default async function DiscoveryPage() {
  const user = await requireUser();
  redirect(user.is_admin ? "/admin/discovery" : "/companies#request-company");
}
