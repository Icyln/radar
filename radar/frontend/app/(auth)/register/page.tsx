import { redirect } from "next/navigation";
import { AuthForm } from "@/components/auth-form";
import { getCurrentUser } from "@/lib/server-api";

export default async function RegisterPage() {
  if (await getCurrentUser()) redirect("/dashboard");
  return <section className="panel p-6 sm:p-8"><p className="eyebrow">Get started</p><h1 className="mt-2 text-2xl font-semibold text-zinc-50">Create your Radar account</h1><p className="mt-2 text-sm leading-6 text-zinc-500">Start with deterministic job profiles and connect Telegram for real-time alerts.</p><AuthForm mode="register" /></section>;
}
