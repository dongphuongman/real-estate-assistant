export const runtime = "nodejs";

type ProxyContext = {
  params: {
    path?: string[];
  };
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
  const raw = process.env.API_ACCESS_KEY || process.env.NEXT_PUBLIC_API_KEY;
  if (!raw) return undefined;
  const trimmed = raw.trim();
  return trimmed ? trimmed : undefined;
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
  const pathParts = context.params.path ?? [];

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

export async function GET(request: Request, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function POST(request: Request, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function PUT(request: Request, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function PATCH(request: Request, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function DELETE(request: Request, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function OPTIONS(request: Request, context: ProxyContext): Promise<Response> {
  return proxyRequest(request, context);
}
