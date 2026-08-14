export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return `Radar request failed with ${status}`;
}

export async function clientRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`/api/radar/${path.replace(/^\//, "")}`, {
    ...init,
    headers
  });

  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) throw new ApiError(errorMessage(payload, response.status), response.status);
  return payload as T;
}
