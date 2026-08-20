function normalizeApiBaseUrl(value: string | undefined): string {
  const fallback = "http://127.0.0.1:8000";
  const raw = (value ?? fallback).trim();

  // Fail safe for copied example values instead of silently proxying to a fake host.
  const candidate = /YOUR-RENDER-SERVICE/i.test(raw) ? fallback : raw;

  try {
    const url = new URL(candidate);

    // Uvicorn's default dev bind is 127.0.0.1. On some Windows/Node setups,
    // `localhost` resolves to ::1 first, which produces ECONNREFUSED even while
    // the backend is healthy on 127.0.0.1.
    if (process.env.NODE_ENV !== "production" && url.hostname === "localhost") {
      url.hostname = "127.0.0.1";
    }

    // Accept either https://host or https://host/api/v1 in environment files.
    // The BFF and server helpers add the API path themselves.
    url.pathname = url.pathname.replace(/\/api\/v1\/?$/i, "").replace(/\/+$/, "");
    url.search = "";
    url.hash = "";
    return url.toString().replace(/\/+$/, "");
  } catch {
    // Keep local development recoverable if an old/malformed value is present.
    if (process.env.NODE_ENV !== "production") return fallback;
    throw new Error("RADAR_API_URL must be a valid absolute URL");
  }
}

export const API_BASE_URL = normalizeApiBaseUrl(
  process.env.RADAR_API_URL ?? process.env.NEXT_PUBLIC_API_URL
);

export const SESSION_COOKIE = "radar_access_token";

const configuredSessionAge = Number(process.env.RADAR_SESSION_MAX_AGE_SECONDS ?? "3600");

export const SESSION_MAX_AGE_SECONDS =
  Number.isFinite(configuredSessionAge) && configuredSessionAge >= 300
    ? configuredSessionAge
    : 3600;

const configuredBffBodyLimit = Number(process.env.RADAR_BFF_MAX_REQUEST_BYTES ?? "262144");
export const BFF_MAX_REQUEST_BYTES = Number.isFinite(configuredBffBodyLimit) && configuredBffBodyLimit >= 16384
  ? configuredBffBodyLimit
  : 262144;

const configuredUpstreamTimeout = Number(process.env.RADAR_BFF_UPSTREAM_TIMEOUT_MS ?? "20000");
export const BFF_UPSTREAM_TIMEOUT_MS = Number.isFinite(configuredUpstreamTimeout) && configuredUpstreamTimeout >= 1000
  ? configuredUpstreamTimeout
  : 20000;

const configuredWideSearchTimeout = Number(process.env.RADAR_BFF_WIDE_SEARCH_TIMEOUT_MS ?? "60000");
export const BFF_WIDE_SEARCH_TIMEOUT_MS = Number.isFinite(configuredWideSearchTimeout) && configuredWideSearchTimeout >= 5000
  ? configuredWideSearchTimeout
  : 60000;
