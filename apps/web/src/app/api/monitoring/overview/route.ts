/**
 * Proxy for /monitoring/overview endpoint (Task #57)
 * High-level monitoring overview for dashboard.
 */

import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
  const url = `${backendUrl}/monitoring/overview`;

  const response = await fetch(url, {
    headers: {
      'X-API-Key': process.env.API_ACCESS_KEY || '',
    },
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
