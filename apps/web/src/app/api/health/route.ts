/**
 * Proxy for /health endpoint (Task #57)
 * Monitoring endpoint for liveness probes.
 */

import { NextRequest, NextResponse } from 'next/server';

export async function GET(_request: NextRequest) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
  const url = `${backendUrl}/health`;

  const response = await fetch(url, {
    headers: {
      'X-API-Key': process.env.API_ACCESS_KEY || '',
    },
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
