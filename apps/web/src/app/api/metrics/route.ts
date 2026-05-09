/**
 * Proxy for /metrics endpoint (Task #57)
 * Prometheus metrics endpoint (text/plain).
 */

import { NextRequest, NextResponse } from 'next/server';

export async function GET(_request: NextRequest) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
  const url = `${backendUrl}/metrics`;

  const response = await fetch(url, {
    headers: {
      'X-API-Key': process.env.API_ACCESS_KEY || '',
    },
  });

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: {
      'Content-Type': 'text/plain',
    },
  });
}
