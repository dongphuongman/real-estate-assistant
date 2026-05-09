/**
 * Proxy for /monitoring/test-alert endpoint (Task #57)
 * Test alert endpoint for monitoring notifications.
 */

import { NextRequest, NextResponse } from 'next/server';

export async function POST(_request: NextRequest) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
  const url = `${backendUrl}/monitoring/test-alert`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'X-API-Key': process.env.API_ACCESS_KEY || '',
    },
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
