import { redirect } from "next/navigation";
import { AuthForm } from "@/components/auth-form";
import { getCurrentUser } from "@/lib/server-api";

export default async function LoginPage() {
  if (await getCurrentUser()) redirect("/dashboard");
  return (
    <section className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_24px_70px_rgba(15,45,36,0.10)] sm:p-8">
      <p className="eyebrow">Welcome back</p>
      <h1 className="mt-2 text-2xl font-extrabold tracking-[-0.025em] text-slate-950">Sign in to Radar</h1>
      <p className="mt-2 text-sm leading-6 text-slate-500">Open your job alerts, review new matches, and manage your notifications.</p>
      <AuthForm mode="login" />
    </section>
  );
}
