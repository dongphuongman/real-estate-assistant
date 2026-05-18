import { NextRequest } from 'next/server';
import { getBackendApiBaseUrl, getApiAccessKey, filterResponseHeaders } from '@/lib/proxy-utils';

export const runtime = 'nodejs';

async function proxyRequest(): Promise<Response> {
  const baseUrl = getBackendApiBaseUrl().replace(/\/api\/v1\/?$/, '');
  const targetUrl = `${baseUrl}/health`;

  const headers = new Headers();
  const apiKey = getApiAccessKey();
  if (apiKey) {
    headers.set('X-API-Key', apiKey);
  }

  try {
    const response = await fetch(targetUrl, { method: 'GET', headers });

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: filterResponseHeaders(response.headers),
    });
  } catch (error) {
    return new Response(
      JSON.stringify({
        detail: 'Backend health check unavailable',
        error: error instanceof Error ? error.message : 'Unknown error',
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

export async function GET(): Promise<Response> {
  return proxyRequest();
}
