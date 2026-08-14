"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { clientRequest } from "@/lib/client-api";
import type { AuthResult } from "@/types/api";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const register = mode === "register";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await clientRequest<AuthResult>(`auth/${mode}`, {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
      router.replace("/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="mt-7 space-y-5">
      <label className="field-label">Email
        <input className="input mt-2" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="you@example.com" />
      </label>
      <label className="field-label">Password
        <input className="input mt-2" type="password" autoComplete={register ? "new-password" : "current-password"} minLength={8} maxLength={256} value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="At least 8 characters" />
      </label>
      {error ? <div className="rounded-lg border border-rose-900/70 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">{error}</div> : null}
      <button className="button-primary w-full justify-center py-2.5" disabled={busy}>{busy ? (register ? "Creating account…" : "Signing in…") : register ? "Create Radar account" : "Sign in"}</button>
      <p className="text-center text-xs text-zinc-500">{register ? "Already have an account?" : "New to Radar?"} <Link href={register ? "/login" : "/register"} className="text-emerald-300 hover:text-emerald-200">{register ? "Sign in" : "Create one"}</Link></p>
    </form>
  );
}
