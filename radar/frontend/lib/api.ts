import type { HealthResponse } from "@/types/health";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers
    }
  });

  if (!response.ok) {
    throw new ApiError(`Radar API request failed with ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export function getApiHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health", { cache: "no-store" });
}
