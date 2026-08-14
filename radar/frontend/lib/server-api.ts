import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { API_BASE_URL, SESSION_COOKIE } from "@/lib/config";
import type { User } from "@/types/api";

export class ServerApiError extends Error {
  constructor(
    message: string,
    public readonly status: number
  ) {
    super(message);
    this.name = "ServerApiError";
  }
}

function detailMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return `Radar API request failed with ${status}`;
}

export async function serverRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE)?.value;
  if (!token) throw new ServerApiError("authentication required", 401);

  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  headers.set("Authorization", `Bearer ${token}`);
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store"
  });

  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) throw new ServerApiError(detailMessage(payload, response.status), response.status);
  return payload as T;
}

export async function getCurrentUser(): Promise<User | null> {
  try {
    return await serverRequest<User>("/api/v1/auth/me");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 401) return null;
    throw error;
  }
}

export async function requireUser(): Promise<User> {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  return user;
}
