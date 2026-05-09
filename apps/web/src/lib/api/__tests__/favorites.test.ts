/**
 * Tests for favorites.ts — Saved Searches, Favorites, Collections, Filter Presets.
 */

import { jest } from '@jest/globals';
import type {
  SavedSearchListResponse,
  SavedSearch,
  SavedSearchCreate,
  SavedSearchUpdate,
  FavoriteListResponse,
  Favorite,
  FavoriteCheckResponse,
  FavoriteCreate,
  FavoriteUpdate,
  CollectionListResponse,
  Collection,
  CollectionCreate,
  CollectionUpdate,
  FilterPresetListResponse,
  FilterPreset,
  FilterPresetCreate,
  FilterPresetUpdate,
} from '../../types';
import { ApiError } from '../client';

// Mock fetch globally
(globalThis as unknown as { fetch: jest.Mock }).fetch = jest.fn();
const mockFetch = globalThis.fetch as jest.Mock;

// Helper to create a successful JSON response
function okResponse<T>(data: T) {
  return {
    ok: true,
    json: async () => data,
    status: 200,
    headers: { get: () => null },
  };
}

// Helper to create an error response
function errorResponse(status: number, detail: string) {
  return {
    ok: false,
    status,
    statusText: 'Error',
    text: async () => JSON.stringify({ detail }),
    json: async () => ({ detail }),
    headers: { get: () => null },
  };
}

// We must import after fetch is mocked
import {
  getSavedSearches,
  createSavedSearch,
  getSavedSearch,
  updateSavedSearch,
  deleteSavedSearch,
  toggleSavedSearchAlert,
  markSavedSearchUsed,
  getFavorites,
  addFavorite,
  removeFavorite,
  removeFavoriteByProperty,
  checkFavorite,
  getFavoriteIds,
  updateFavorite,
  moveFavoriteToCollection,
  getCollections,
  createCollection,
  getDefaultCollection,
  getCollection,
  updateCollection,
  deleteCollection,
  getFilterPresets,
  getFilterPreset,
  getDefaultFilterPreset,
  createFilterPreset,
  updateFilterPreset,
  deleteFilterPreset,
  markFilterPresetUsed,
  setFilterPresetDefault,
} from '../favorites';

beforeEach(() => {
  jest.clearAllMocks();
});

// =============================================================================
// Saved Searches
// =============================================================================
describe('Saved Searches API', () => {
  const sampleSearch: SavedSearch = {
    id: 'ss-1',
    user_id: 'u-1',
    name: 'Berlin Apts',
    filters: { city: 'Berlin' },
    alert_frequency: 'daily',
    is_active: true,
    notify_on_new: true,
    notify_on_price_drop: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    use_count: 0,
  };

  describe('getSavedSearches', () => {
    it('fetches with include_inactive=false by default', async () => {
      const data: SavedSearchListResponse = { items: [sampleSearch], total: 1 };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      const result = await getSavedSearches();

      expect(result.total).toBe(1);
      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('include_inactive=false');
    });

    it('passes include_inactive=true', async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ items: [], total: 0 }));

      await getSavedSearches(true);

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('include_inactive=true');
    });

    it('throws on error response', async () => {
      mockFetch.mockResolvedValueOnce(errorResponse(500, 'Server error'));

      await expect(getSavedSearches()).rejects.toThrow(ApiError);
    });
  });

  describe('createSavedSearch', () => {
    it('sends POST with correct body', async () => {
      const input: SavedSearchCreate = {
        name: 'Test',
        filters: { city: 'Warsaw' },
        alert_frequency: 'weekly',
      };
      mockFetch.mockResolvedValueOnce(okResponse(sampleSearch));

      const result = await createSavedSearch(input);

      expect(result.id).toBe('ss-1');
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(JSON.parse(opts.body)).toEqual(input);
    });

    it('throws on validation error', async () => {
      mockFetch.mockResolvedValueOnce(errorResponse(422, 'Validation failed'));

      await expect(createSavedSearch({ name: '', filters: {} })).rejects.toThrow(ApiError);
    });
  });

  describe('getSavedSearch', () => {
    it('fetches a single saved search by id', async () => {
      mockFetch.mockResolvedValueOnce(okResponse(sampleSearch));

      const result = await getSavedSearch('ss-1');

      expect(result.id).toBe('ss-1');
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('/saved-searches/ss-1');
      expect(url).not.toContain('/saved-searches/ss-1/');
    });

    it('throws on 404', async () => {
      mockFetch.mockResolvedValueOnce(errorResponse(404, 'Not found'));

      await expect(getSavedSearch('bad-id')).rejects.toThrow(ApiError);
    });
  });

  describe('updateSavedSearch', () => {
    it('sends PATCH with update data', async () => {
      const update: SavedSearchUpdate = { name: 'Updated' };
      mockFetch.mockResolvedValueOnce(okResponse({ ...sampleSearch, name: 'Updated' }));

      const result = await updateSavedSearch('ss-1', update);

      expect(result.name).toBe('Updated');
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('PATCH');
      expect(JSON.parse(opts.body)).toEqual(update);
    });
  });

  describe('deleteSavedSearch', () => {
    it('succeeds on ok response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

      await expect(deleteSavedSearch('ss-1')).resolves.toBeUndefined();
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('DELETE');
      expect(url).toContain('/saved-searches/ss-1');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'Not found',
        headers: { get: () => null },
      });

      await expect(deleteSavedSearch('ss-1')).rejects.toThrow(ApiError);
    });

    it('uses fallback message when text() rejects', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => {
          throw new Error('text failed');
        },
        headers: { get: () => null },
      });

      await expect(deleteSavedSearch('ss-1')).rejects.toThrow('Failed to delete saved search');
    });

    it('includes request ID from header if present', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Server error',
        headers: { get: (name: string) => (name === 'X-Request-ID' ? 'req-abc' : null) },
      });

      try {
        await deleteSavedSearch('ss-1');
        fail('Should have thrown');
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError);
        expect((e as ApiError).request_id).toBe('req-abc');
      }
    });
  });

  describe('toggleSavedSearchAlert', () => {
    it('sends POST with enabled=true', async () => {
      mockFetch.mockResolvedValueOnce(okResponse(sampleSearch));

      await toggleSavedSearchAlert('ss-1', true);

      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(url).toContain('enabled=true');
    });

    it('sends POST with enabled=false', async () => {
      mockFetch.mockResolvedValueOnce(okResponse(sampleSearch));

      await toggleSavedSearchAlert('ss-1', false);

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('enabled=false');
    });
  });

  describe('markSavedSearchUsed', () => {
    it('sends POST to /use endpoint', async () => {
      const updated = { ...sampleSearch, use_count: 1 };
      mockFetch.mockResolvedValueOnce(okResponse(updated));

      const result = await markSavedSearchUsed('ss-1');

      expect(result.use_count).toBe(1);
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(url).toContain('/saved-searches/ss-1/use');
    });
  });
});

// =============================================================================
// Favorites
// =============================================================================
describe('Favorites API', () => {
  const sampleFavorite: Favorite = {
    id: 'fav-1',
    user_id: 'u-1',
    property_id: 'prop-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  describe('getFavorites', () => {
    it('uses default limit=50 and offset=0', async () => {
      const data: FavoriteListResponse = { items: [], total: 0, unavailable_count: 0 };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      await getFavorites();

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('limit=50');
      expect(url).toContain('offset=0');
      expect(url).not.toContain('collection_id');
    });

    it('includes collection_id when provided', async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ items: [], total: 0, unavailable_count: 0 }));

      await getFavorites('col-1');

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('collection_id=col-1');
    });

    it('passes custom limit and offset', async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ items: [], total: 0, unavailable_count: 0 }));

      await getFavorites(undefined, 10, 20);

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('limit=10');
      expect(url).toContain('offset=20');
    });

    it('returns favorites list', async () => {
      const data: FavoriteListResponse = {
        items: [
          {
            id: 'fav-1',
            user_id: 'u-1',
            property_id: 'prop-1',
            is_available: true,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
        unavailable_count: 0,
      };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      const result = await getFavorites();
      expect(result.items).toHaveLength(1);
      expect(result.total).toBe(1);
    });
  });

  describe('addFavorite', () => {
    it('sends POST with property_id', async () => {
      const input: FavoriteCreate = { property_id: 'prop-1' };
      mockFetch.mockResolvedValueOnce(okResponse(sampleFavorite));

      const result = await addFavorite(input);

      expect(result.property_id).toBe('prop-1');
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(JSON.parse(opts.body)).toEqual(input);
    });

    it('includes optional collection_id and notes', async () => {
      const input: FavoriteCreate = {
        property_id: 'prop-1',
        collection_id: 'col-1',
        notes: 'Great place',
      };
      mockFetch.mockResolvedValueOnce(okResponse(sampleFavorite));

      await addFavorite(input);

      const [, opts] = mockFetch.mock.calls[0];
      expect(JSON.parse(opts.body)).toEqual(input);
    });
  });

  describe('removeFavorite', () => {
    it('succeeds on ok response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

      await expect(removeFavorite('fav-1')).resolves.toBeUndefined();
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('DELETE');
      expect(url).toContain('/favorites/fav-1');
    });

    it('throws ApiError when response is not ok', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'Not found',
      });

      await expect(removeFavorite('fav-999')).rejects.toThrow(ApiError);
    });

    it('uses fallback message when text() rejects', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => {
          throw new Error('fail');
        },
      });

      await expect(removeFavorite('fav-1')).rejects.toThrow('Failed to remove favorite');
    });
  });

  describe('removeFavoriteByProperty', () => {
    it('sends DELETE to by-property endpoint', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

      await expect(removeFavoriteByProperty('prop-1')).resolves.toBeUndefined();
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('DELETE');
      expect(url).toContain('/favorites/by-property/prop-1');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'Not found',
      });

      await expect(removeFavoriteByProperty('prop-x')).rejects.toThrow(ApiError);
    });

    it('uses fallback message when text() rejects', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => {
          throw new Error('fail');
        },
      });

      await expect(removeFavoriteByProperty('prop-1')).rejects.toThrow('Failed to remove favorite');
    });
  });

  describe('checkFavorite', () => {
    it('returns is_favorited=true with favorite_id', async () => {
      const data: FavoriteCheckResponse = {
        is_favorited: true,
        favorite_id: 'fav-1',
      };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      const result = await checkFavorite('prop-1');

      expect(result.is_favorited).toBe(true);
      expect(result.favorite_id).toBe('fav-1');
    });

    it('returns is_favorited=false when not favorited', async () => {
      const data: FavoriteCheckResponse = { is_favorited: false };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      const result = await checkFavorite('prop-2');

      expect(result.is_favorited).toBe(false);
    });

    it('sends GET to /favorites/check/:propertyId', async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ is_favorited: false }));

      await checkFavorite('prop-99');

      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('GET');
      expect(url).toContain('/favorites/check/prop-99');
    });
  });

  describe('getFavoriteIds', () => {
    it('returns array of property IDs', async () => {
      mockFetch.mockResolvedValueOnce(okResponse(['prop-1', 'prop-2']));

      const result = await getFavoriteIds();

      expect(result).toEqual(['prop-1', 'prop-2']);
    });

    it('returns empty array', async () => {
      mockFetch.mockResolvedValueOnce(okResponse([]));

      const result = await getFavoriteIds();

      expect(result).toEqual([]);
    });
  });

  describe('updateFavorite', () => {
    it('sends PATCH with update data', async () => {
      const update: FavoriteUpdate = { notes: 'Updated notes' };
      mockFetch.mockResolvedValueOnce(okResponse({ ...sampleFavorite, notes: 'Updated notes' }));

      const result = await updateFavorite('fav-1', update);

      expect(result.notes).toBe('Updated notes');
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('PATCH');
      expect(url).toContain('/favorites/fav-1');
    });
  });

  describe('moveFavoriteToCollection', () => {
    it('sends POST to move endpoint', async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ ...sampleFavorite, collection_id: 'col-2' }));

      const result = await moveFavoriteToCollection('fav-1', 'col-2');

      expect(result.collection_id).toBe('col-2');
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(url).toContain('/favorites/fav-1/move/col-2');
    });
  });
});

// =============================================================================
// Collections
// =============================================================================
describe('Collections API', () => {
  const sampleCollection: Collection = {
    id: 'col-1',
    user_id: 'u-1',
    name: 'My Collection',
    is_default: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    favorite_count: 3,
  };

  describe('getCollections', () => {
    it('fetches all collections', async () => {
      const data: CollectionListResponse = { items: [sampleCollection], total: 1 };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      const result = await getCollections();

      expect(result.items).toHaveLength(1);
      expect(result.total).toBe(1);
    });

    it('sends GET request', async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ items: [], total: 0 }));

      await getCollections();

      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('GET');
    });
  });

  describe('createCollection', () => {
    it('sends POST with name', async () => {
      const input: CollectionCreate = { name: 'New Col', description: 'Desc' };
      mockFetch.mockResolvedValueOnce(okResponse(sampleCollection));

      await createCollection(input);

      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(JSON.parse(opts.body)).toEqual(input);
    });
  });

  describe('getDefaultCollection', () => {
    it('fetches /collections/default', async () => {
      const defaultCol = { ...sampleCollection, is_default: true };
      mockFetch.mockResolvedValueOnce(okResponse(defaultCol));

      const result = await getDefaultCollection();

      expect(result.is_default).toBe(true);
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('/collections/default');
    });
  });

  describe('getCollection', () => {
    it('fetches collection by id', async () => {
      mockFetch.mockResolvedValueOnce(okResponse(sampleCollection));

      const result = await getCollection('col-1');

      expect(result.id).toBe('col-1');
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('/collections/col-1');
    });
  });

  describe('updateCollection', () => {
    it('sends PUT with update data', async () => {
      const update: CollectionUpdate = { name: 'Renamed' };
      mockFetch.mockResolvedValueOnce(okResponse({ ...sampleCollection, name: 'Renamed' }));

      const result = await updateCollection('col-1', update);

      expect(result.name).toBe('Renamed');
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('PUT');
      expect(url).toContain('/collections/col-1');
    });
  });

  describe('deleteCollection', () => {
    it('succeeds on ok response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

      await expect(deleteCollection('col-1')).resolves.toBeUndefined();
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('DELETE');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => 'Not found',
      });

      await expect(deleteCollection('col-999')).rejects.toThrow(ApiError);
    });

    it('uses fallback message when text() rejects', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => {
          throw new Error('fail');
        },
      });

      await expect(deleteCollection('col-1')).rejects.toThrow('Failed to delete collection');
    });
  });
});

// =============================================================================
// Filter Presets
// =============================================================================
describe('Filter Presets API', () => {
  const samplePreset: FilterPreset = {
    id: 'fp-1',
    user_id: 'u-1',
    name: 'My Preset',
    filters: { city: 'Berlin' },
    is_default: false,
    use_count: 0,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  describe('getFilterPresets', () => {
    it('uses default limit=50 and offset=0', async () => {
      const data: FilterPresetListResponse = { items: [], total: 0 };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      await getFilterPresets();

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('limit=50');
      expect(url).toContain('offset=0');
    });

    it('passes custom limit and offset', async () => {
      mockFetch.mockResolvedValueOnce(okResponse({ items: [], total: 0 }));

      await getFilterPresets(10, 5);

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('limit=10');
      expect(url).toContain('offset=5');
    });

    it('returns presets list', async () => {
      const data: FilterPresetListResponse = { items: [samplePreset], total: 1 };
      mockFetch.mockResolvedValueOnce(okResponse(data));

      const result = await getFilterPresets();
      expect(result.items).toHaveLength(1);
    });
  });

  describe('getFilterPreset', () => {
    it('fetches single preset by id', async () => {
      mockFetch.mockResolvedValueOnce(okResponse(samplePreset));

      const result = await getFilterPreset('fp-1');

      expect(result.id).toBe('fp-1');
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('/filter-presets/fp-1');
    });
  });

  describe('getDefaultFilterPreset', () => {
    it('fetches /filter-presets/default', async () => {
      const defaultPreset = { ...samplePreset, is_default: true };
      mockFetch.mockResolvedValueOnce(okResponse(defaultPreset));

      const result = await getDefaultFilterPreset();

      expect(result.is_default).toBe(true);
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('/filter-presets/default');
    });
  });

  describe('createFilterPreset', () => {
    it('sends POST with preset data', async () => {
      const input: FilterPresetCreate = {
        name: 'New Preset',
        filters: { city: 'Krakow' },
        is_default: false,
      };
      mockFetch.mockResolvedValueOnce(okResponse(samplePreset));

      await createFilterPreset(input);

      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(JSON.parse(opts.body)).toEqual(input);
    });
  });

  describe('updateFilterPreset', () => {
    it('sends PATCH with update data', async () => {
      const update: FilterPresetUpdate = { name: 'Renamed' };
      mockFetch.mockResolvedValueOnce(okResponse({ ...samplePreset, name: 'Renamed' }));

      const result = await updateFilterPreset('fp-1', update);

      expect(result.name).toBe('Renamed');
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('PATCH');
      expect(url).toContain('/filter-presets/fp-1');
    });
  });

  describe('deleteFilterPreset', () => {
    it('succeeds on ok response', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => null, status: 200 });

      await expect(deleteFilterPreset('fp-1')).resolves.toBeUndefined();
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('DELETE');
      expect(url).toContain('/filter-presets/fp-1');
    });

    it('throws on error response', async () => {
      mockFetch.mockResolvedValueOnce(errorResponse(404, 'Not found'));

      await expect(deleteFilterPreset('fp-x')).rejects.toThrow(ApiError);
    });
  });

  describe('markFilterPresetUsed', () => {
    it('sends POST to /use endpoint', async () => {
      const updated = { ...samplePreset, use_count: 1 };
      mockFetch.mockResolvedValueOnce(okResponse(updated));

      const result = await markFilterPresetUsed('fp-1');

      expect(result.use_count).toBe(1);
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(url).toContain('/filter-presets/fp-1/use');
    });
  });

  describe('setFilterPresetDefault', () => {
    it('sends POST to /set-default endpoint', async () => {
      const updated = { ...samplePreset, is_default: true };
      mockFetch.mockResolvedValueOnce(okResponse(updated));

      const result = await setFilterPresetDefault('fp-1');

      expect(result.is_default).toBe(true);
      const [url, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(url).toContain('/filter-presets/fp-1/set-default');
    });
  });
});
