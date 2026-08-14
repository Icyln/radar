import { redirect } from "next/navigation";
import { AuthForm } from "@/components/auth-form";
import { getCurrentUser } from "@/lib/server-api";

export default async function LoginPage() {
  if (await getCurrentUser()) redirect("/dashboard");
  return <section className="panel p-6 sm:p-8"><p className="eyebrow">Welcome back</p><h1 className="mt-2 text-2xl font-semibold text-zinc-50">Sign in to Radar</h1><p className="mt-2 text-sm leading-6 text-zinc-500">Manage your monitoring profiles, review matches, and keep Telegram connected.</p><AuthForm mode="login" /></section>;
}
