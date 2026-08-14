function normalizeApiBaseUrl(value: string | undefined): string {
  const fallback = "http://localhost:8000";
  const candidate = (value ?? fallback).trim();
  return candidate.replace(/\/+$/, "");
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
