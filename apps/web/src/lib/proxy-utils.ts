/**
 * Shared utilities for API proxy routes
 */

export const HOP_BY_HOP_RESPONSE_HEADERS = new Set<string>([
  'connection',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
]);

function isProductionRuntime(): boolean {
  if (process.env.NODE_ENV === 'production') return true;
  if (process.env.VERCEL_ENV === 'production') return true;
  if (process.env.VERCEL === '1') return true;
  return false;
}

function isLocalhostUrl(value: string): boolean {
  const trimmed = value.trim().toLowerCase();
  return (
    trimmed.includes('://localhost') ||
    trimmed.includes('://127.0.0.1') ||
    trimmed.includes('://[::1]') ||
    trimmed.includes('://0.0.0.0')
  );
}

/**
 * Get backend API base URL with production safety checks
 * @throws Error if BACKEND_API_URL is misconfigured in production
 */
export function getBackendApiBaseUrl(): string {
  const raw = process.env.BACKEND_API_URL;
  if (isProductionRuntime()) {
    const trimmed = raw?.trim();
    if (!trimmed) {
      throw new Error('BACKEND_API_URL must be set in production');
    }
    if (isLocalhostUrl(trimmed)) {
      throw new Error('BACKEND_API_URL must not point to localhost in production');
    }
  }

  const defaultBackendUrl =
    process.env.BACKEND_API_URL ||
    (process.env.BACKEND_PORT
      ? `http://localhost:${process.env.BACKEND_PORT}/api/v1`
      : 'http://localhost:8000/api/v1');
  const fallback = raw || defaultBackendUrl;
  return fallback.replace(/\/+$/, '');
}

/**
 * Get API access key from environment (no hardcoded fallback)
 * @returns API key or undefined if not configured
 */
export function getApiAccessKey(): string | undefined {
  const raw = process.env.API_ACCESS_KEY;
  if (raw) {
    const trimmed = raw.trim();
    if (trimmed) return trimmed;
  }

  const rotated = process.env.API_ACCESS_KEYS;
  if (!rotated) return undefined;
  const first = rotated
    .split(',')
    .map((value) => value.trim())
    .find((value) => Boolean(value));
  return first ? first : undefined;
}

/**
 * Filter hop-by-hop headers from backend response
 */
export function filterResponseHeaders(source: Headers): Headers {
  const filtered = new Headers();
  for (const [name, value] of source.entries()) {
    if (HOP_BY_HOP_RESPONSE_HEADERS.has(name.toLowerCase())) continue;
    filtered.set(name, value);
  }
  return filtered;
}
