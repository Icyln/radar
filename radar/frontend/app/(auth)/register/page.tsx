import { redirect } from "next/navigation";
import { AuthForm } from "@/components/auth-form";
import { getCurrentUser } from "@/lib/server-api";

export default async function RegisterPage() {
  if (await getCurrentUser()) redirect("/dashboard");
  return (
    <section className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_24px_70px_rgba(15,45,36,0.10)] sm:p-8">
      <p className="eyebrow">Get started</p>
      <h1 className="mt-2 text-2xl font-extrabold tracking-[-0.025em] text-slate-950">Create your Radar account</h1>
      <p className="mt-2 text-sm leading-6 text-slate-500">Set up focused job alerts, follow companies, and optionally receive matching roles in Telegram.</p>
      <AuthForm mode="register" />
    </section>
  );
}
