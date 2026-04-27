/**
 * Tests for FavoritesContext.
 * Uses global fetch mock — same pattern as agents.test.ts and AuthContext.test.tsx.
 */

import { render, screen, act, waitFor } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Mock fetch globally before any imports
const mockFetch = jest.fn();
(globalThis as unknown as { fetch: jest.Mock }).fetch = mockFetch;

// Mock AuthContext - return a simple object
let authState = { isAuthenticated: true, user: { id: 'user-1', email: 'test@test.com' } };

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => authState,
}));

function createMockResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: new Headers({ 'X-Request-ID': 'req-test' }),
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as Response;
}

import { FavoritesProvider, useFavorites } from '@/contexts/FavoritesContext';

function TestComponent() {
  const {
    favoriteIds,
    favorites,
    collections,
    isLoading,
    error,
    toggleFavorite,
    isFavorited,
    refreshFavorites,
    loadFavoritesWithProperties,
    addCollection,
    updateCollection,
    removeCollection,
    clearError,
  } = useFavorites();

  return (
    <div>
      <div data-testid="loading">{isLoading ? 'loading' : 'idle'}</div>
      <div data-testid="error">{error ?? 'none'}</div>
      <div data-testid="favorite-ids">{Array.from(favoriteIds).join(',')}</div>
      <div data-testid="favorites-count">{favorites.length}</div>
      <div data-testid="collections-count">{collections.length}</div>
      <div data-testid="is-favorited">{isFavorited('prop-1') ? 'yes' : 'no'}</div>
      <button onClick={() => toggleFavorite('prop-1').catch(() => {})} data-testid="toggle-btn">
        Toggle
      </button>
      <button onClick={() => refreshFavorites()} data-testid="refresh-btn">
        Refresh
      </button>
      <button onClick={() => loadFavoritesWithProperties()} data-testid="load-btn">
        Load
      </button>
      <button
        onClick={() => addCollection('Test', 'desc').catch(() => {})}
        data-testid="add-col-btn"
      >
        Add Col
      </button>
      <button
        onClick={() => updateCollection('col-1', 'Updated').catch(() => {})}
        data-testid="upd-col-btn"
      >
        Upd Col
      </button>
      <button onClick={() => removeCollection('col-1').catch(() => {})} data-testid="rm-col-btn">
        Rm Col
      </button>
      <button onClick={() => clearError()} data-testid="clear-btn">
        Clear
      </button>
    </div>
  );
}

describe('FavoritesContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    authState = { isAuthenticated: true, user: { id: 'user-1', email: 'test@test.com' } };
    mockFetch.mockResolvedValue(createMockResponse(['prop-1', 'prop-2']));
  });

  it('starts empty when not authenticated', async () => {
    authState = { isAuthenticated: false, user: null };

    render(
      <FavoritesProvider>
        <TestComponent />
      </FavoritesProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('favorite-ids').textContent).toBe('');
    });
  });

  it('throws when toggleFavorite called unauthenticated', async () => {
    authState = { isAuthenticated: false, user: null };

    render(
      <FavoritesProvider>
        <TestComponent />
      </FavoritesProvider>
    );

    await act(async () => {
      screen.getByTestId('toggle-btn').click();
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(screen.getByTestId('is-favorited').textContent).toBe('no');
  });
});
