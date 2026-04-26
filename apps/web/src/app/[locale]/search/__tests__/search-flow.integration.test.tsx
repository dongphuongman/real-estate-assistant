/**
 * Integration test for search flow: query → results → filters → pagination.
 *
 * Tests the search API client behavior end-to-end with mocked fetch.
 * Follows the same pattern as AuthContext.test.tsx (mock global fetch).
 */

import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Mock fetch globally before any imports
const mockFetch = jest.fn();
(globalThis as unknown as { fetch: jest.Mock }).fetch = mockFetch;

// Import after fetch is mocked
import { searchProperties } from '@/lib/api';
import type { SearchRequest } from '@/lib/types';

function createMockResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: new Headers({ 'X-Request-ID': 'req-123' }),
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as Response;
}

describe('Search Flow Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
  });

  it('searches and returns results', async () => {
    mockFetch.mockResolvedValueOnce(
      createMockResponse({
        results: [
          {
            id: 'prop-1',
            title: '2BR Apartment Krakow',
            city: 'Krakow',
            price: 450000,
            area_sqm: 65,
            rooms: 2,
          },
        ],
        total: 1,
      })
    );

    const request: SearchRequest = {
      query: 'apartments in Krakow',
      sort_by: 'relevance',
      sort_order: 'desc',
    };
    const response = await searchProperties(request);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(response.results).toHaveLength(1);
    expect(response.results[0].title).toBe('2BR Apartment Krakow');
    expect(response.total).toBe(1);
  });

  it('handles empty results gracefully', async () => {
    mockFetch.mockResolvedValueOnce(createMockResponse({ results: [], total: 0 }));

    const response = await searchProperties({
      query: 'nonexistent location xyz',
    });

    expect(response.results).toEqual([]);
    expect(response.total).toBe(0);
  });

  it('handles API error gracefully', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      headers: new Headers(),
      json: async () => ({ detail: 'Search service unavailable' }),
      text: async () => JSON.stringify({ detail: 'Search service unavailable' }),
    } as Response);

    await expect(searchProperties({ query: 'test query' })).rejects.toThrow(
      'Search service unavailable'
    );
  });

  it('sends filters in request body', async () => {
    mockFetch.mockResolvedValueOnce(createMockResponse({ results: [], total: 0 }));

    await searchProperties({
      query: 'apartments',
      filters: {
        min_price: 100000,
        max_price: 500000,
        rooms: 3,
        property_type: 'apartment',
      },
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const call = mockFetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.filters.min_price).toBe(100000);
    expect(body.filters.max_price).toBe(500000);
    expect(body.filters.rooms).toBe(3);
    expect(body.filters.property_type).toBe('apartment');
  });

  it('handles pagination parameters', async () => {
    mockFetch.mockResolvedValueOnce(createMockResponse({ results: [], total: 100 }));

    await searchProperties({
      query: 'apartments',
      page: 2,
      page_size: 10,
    });

    const call = mockFetch.mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.page).toBe(2);
    expect(body.page_size).toBe(10);
  });
});
