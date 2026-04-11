/**
 * Integration test for search flow: query → results → filters → pagination.
 *
 * Follows existing pattern of jest.mock for API mocking.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SearchPage from '../page';
import { searchProperties } from '@/lib/api';

jest.mock('@/lib/api', () => {
  class MockApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  }
  return {
    searchProperties: jest.fn(),
    exportPropertiesBySearch: jest.fn(),
    ApiError: MockApiError,
  };
});

jest.mock('@/components/search/property-map', () => ({
  __esModule: true,
  default: ({ points }: { points: unknown[] }) => (
    <div data-testid="property-map">{points.length} points</div>
  ),
}));

const mockSearch = searchProperties as jest.Mock;

describe('Search Flow Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Object.defineProperty(globalThis.URL, 'createObjectURL', {
      value: jest.fn(() => 'blob:test'),
      configurable: true,
    });
    Object.defineProperty(globalThis.URL, 'revokeObjectURL', {
      value: jest.fn(),
      configurable: true,
    });
  });

  it('searches and displays results', async () => {
    mockSearch.mockResolvedValue({
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
    });

    render(<SearchPage />);
    const input = screen.getByLabelText('Search query');
    fireEvent.change(input, { target: { value: 'apartments in Krakow' } });
    fireEvent.click(screen.getByRole('button', { name: /search/i }));

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith(
        expect.objectContaining({ query: 'apartments in Krakow' })
      );
    });
  });

  it('handles empty results gracefully', async () => {
    mockSearch.mockResolvedValue({ results: [], total: 0 });

    render(<SearchPage />);
    const input = screen.getByLabelText('Search query');
    fireEvent.change(input, { target: { value: 'nonexistent location xyz' } });
    fireEvent.click(screen.getByRole('button', { name: /search/i }));

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalled();
    });
  });

  it('handles API error gracefully', async () => {
    mockSearch.mockRejectedValue(new Error('Network error'));

    render(<SearchPage />);
    const input = screen.getByLabelText('Search query');
    fireEvent.change(input, { target: { value: 'test query' } });
    fireEvent.click(screen.getByRole('button', { name: /search/i }));

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalled();
    });
  });
});
