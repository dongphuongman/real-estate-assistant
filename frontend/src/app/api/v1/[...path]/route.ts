import type { NextRequest } from "next/server";

export const runtime = "nodejs";

type ProxyContext = {
  params: Promise<{
    path: string[];
  }>;
};

const HOP_BY_HOP_RESPONSE_HEADERS = new Set<string>([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "accept-language",
  "content-type",
  "user-agent",
  "x-user-email",
  "x-request-id",
] as const;

function getBackendApiBaseUrl(): string {
  const raw = process.env.BACKEND_API_URL || "http://localhost:8000/api/v1";
  return raw.replace(/\/+$/, "");
}

function getApiAccessKey(): string | undefined {
  const raw = process.env.API_ACCESS_KEY;
  if (raw) {
    const trimmed = raw.trim();
    if (trimmed) return trimmed;
  }

  const rotated = process.env.API_ACCESS_KEYS;
  if (!rotated) return undefined;
  const first = rotated
    .split(",")
    .map((value) => value.trim())
    .find((value) => Boolean(value));
  return first ? first : undefined;
}

function buildBackendUrl(requestUrl: URL, pathParts: string[]): string {
  const base = getBackendApiBaseUrl();
  const encodedPath = pathParts.map((part) => encodeURIComponent(part)).join("/");
  const joined = encodedPath ? `${base}/${encodedPath}` : base;
  const target = new URL(joined);
  target.search = requestUrl.search;
  return target.toString();
}

function buildBackendRequestHeaders(original: Headers): Headers {
  const headers = new Headers();

  for (const headerName of FORWARDED_REQUEST_HEADERS) {
    const value = original.get(headerName);
    if (value) headers.set(headerName, value);
  }

  const apiKey = getApiAccessKey();
  if (apiKey) headers.set("X-API-Key", apiKey);

  return headers;
}

async function proxyRequest(request: Request, context: ProxyContext): Promise<Response> {
  const requestUrl = new URL(request.url);
  const { path } = await context.params;
  const pathParts = path ?? [];

  const body = request.method === "GET" || request.method === "HEAD" ? undefined : request.body;

  const init: RequestInit & { duplex?: "half" } = {
    method: request.method,
    headers: buildBackendRequestHeaders(request.headers),
    body,
    redirect: "manual",
  };
  if (body) init.duplex = "half";

  const backendResponse = await fetch(buildBackendUrl(requestUrl, pathParts), init);

  const responseHeaders = new Headers();
  for (const [name, value] of backendResponse.headers.entries()) {
    if (HOP_BY_HOP_RESPONSE_HEADERS.has(name.toLowerCase())) continue;
    responseHeaders.set(name, value);
  }

  return new Response(backendResponse.body, {
    status: backendResponse.status,
    statusText: backendResponse.statusText,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function POST(request: NextRequest, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function PUT(request: NextRequest, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function PATCH(request: NextRequest, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function DELETE(request: NextRequest, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function OPTIONS(request: NextRequest, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}
