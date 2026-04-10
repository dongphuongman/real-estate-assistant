/**
 * Favorites, Collections, Saved Searches, and Filter Presets API.
 */

import type {
  Favorite,
  FavoriteCheckResponse,
  FavoriteCreate,
  FavoriteListResponse,
  FavoriteUpdate,
  Collection,
  CollectionCreate,
  CollectionListResponse,
  CollectionUpdate,
  SavedSearch,
  SavedSearchCreate,
  SavedSearchListResponse,
  SavedSearchUpdate,
  FilterPreset,
  FilterPresetCreate,
  FilterPresetListResponse,
  FilterPresetUpdate,
} from '../types';

import { getApiUrl, buildHeaders, safeFetch, ApiError, handleResponse } from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';

// Saved Searches API functions for Task #36
export async function getSavedSearches(
  includeInactive: boolean = false
): Promise<SavedSearchListResponse> {
  const url = `${getApiUrl()}/saved-searches?include_inactive=${includeInactive}`;
  const response = await safeFetch(url, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<SavedSearchListResponse>(response);
}

export async function createSavedSearch(data: SavedSearchCreate): Promise<SavedSearch> {
  const response = await safeFetch(`${getApiUrl()}/saved-searches`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<SavedSearch>(response);
}

export async function getSavedSearch(id: string): Promise<SavedSearch> {
  const response = await safeFetch(`${getApiUrl()}/saved-searches/${id}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<SavedSearch>(response);
}

export async function updateSavedSearch(id: string, data: SavedSearchUpdate): Promise<SavedSearch> {
  const response = await safeFetch(`${getApiUrl()}/saved-searches/${id}`, {
    method: 'PATCH',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<SavedSearch>(response);
}

export async function deleteSavedSearch(id: string): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/saved-searches/${id}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    const requestId = response.headers.get('X-Request-ID') || undefined;
    throw new ApiError(
      errorText || 'Failed to delete saved search',
      response.status,
      requestId || undefined
    );
  }
}

export async function toggleSavedSearchAlert(id: string, enabled: boolean): Promise<SavedSearch> {
  const response = await safeFetch(
    `${getApiUrl()}/saved-searches/${id}/toggle-alert?enabled=${enabled}`,
    {
      method: 'POST',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<SavedSearch>(response);
}

export async function markSavedSearchUsed(id: string): Promise<SavedSearch> {
  const response = await safeFetch(`${getApiUrl()}/saved-searches/${id}/use`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<SavedSearch>(response);
}

// Favorites API functions for Task #37
export async function getFavorites(
  collectionId?: string,
  limit: number = 50,
  offset: number = 0
): Promise<FavoriteListResponse> {
  const params = new URLSearchParams();
  if (collectionId) params.append('collection_id', collectionId);
  params.append('limit', String(limit));
  params.append('offset', String(offset));

  const response = await safeFetch(`${getApiUrl()}/favorites?${params}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<FavoriteListResponse>(response);
}

export async function addFavorite(data: FavoriteCreate): Promise<Favorite> {
  const response = await safeFetch(`${getApiUrl()}/favorites`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<Favorite>(response);
}

export async function removeFavorite(favoriteId: string): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/favorites/${favoriteId}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    throw new ApiError(errorText || 'Failed to remove favorite', response.status);
  }
}

export async function removeFavoriteByProperty(propertyId: string): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/favorites/by-property/${propertyId}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    throw new ApiError(errorText || 'Failed to remove favorite', response.status);
  }
}

export async function checkFavorite(propertyId: string): Promise<FavoriteCheckResponse> {
  const response = await safeFetch(`${getApiUrl()}/favorites/check/${propertyId}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<FavoriteCheckResponse>(response);
}

export async function getFavoriteIds(): Promise<string[]> {
  const response = await safeFetch(`${getApiUrl()}/favorites/ids`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<string[]>(response);
}

export async function updateFavorite(favoriteId: string, data: FavoriteUpdate): Promise<Favorite> {
  const response = await safeFetch(`${getApiUrl()}/favorites/${favoriteId}`, {
    method: 'PATCH',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<Favorite>(response);
}

export async function moveFavoriteToCollection(
  favoriteId: string,
  collectionId: string
): Promise<Favorite> {
  const response = await safeFetch(`${getApiUrl()}/favorites/${favoriteId}/move/${collectionId}`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<Favorite>(response);
}

// Collections API functions for Task #37
export async function getCollections(): Promise<CollectionListResponse> {
  const response = await safeFetch(`${getApiUrl()}/collections`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<CollectionListResponse>(response);
}

export async function createCollection(data: CollectionCreate): Promise<Collection> {
  const response = await safeFetch(`${getApiUrl()}/collections`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<Collection>(response);
}

export async function getDefaultCollection(): Promise<Collection> {
  const response = await safeFetch(`${getApiUrl()}/collections/default`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<Collection>(response);
}

export async function getCollection(id: string): Promise<Collection> {
  const response = await safeFetch(`${getApiUrl()}/collections/${id}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<Collection>(response);
}

export async function updateCollection(id: string, data: CollectionUpdate): Promise<Collection> {
  const response = await safeFetch(`${getApiUrl()}/collections/${id}`, {
    method: 'PUT',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<Collection>(response);
}

export async function deleteCollection(id: string): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/collections/${id}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  if (!response.ok) {
    const errorText = await response.text().catch(() => '');
    throw new ApiError(errorText || 'Failed to delete collection', response.status);
  }
}

// =============================================================================
// Filter Presets API (Task #75: Advanced Filter Presets)
// =============================================================================

/**
 * Get all filter presets for the current user
 */
export async function getFilterPresets(
  limit: number = 50,
  offset: number = 0
): Promise<FilterPresetListResponse> {
  const response = await safeFetch(
    `${getApiUrl()}/filter-presets?limit=${limit}&offset=${offset}`,
    {
      method: 'GET',
      headers: buildHeaders(),
      credentials: 'include',
    }
  );
  return handleResponse<FilterPresetListResponse>(response);
}

/**
 * Get a single filter preset by ID
 */
export async function getFilterPreset(id: string): Promise<FilterPreset> {
  const response = await safeFetch(`${getApiUrl()}/filter-presets/${id}`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<FilterPreset>(response);
}

/**
 * Get the user's default filter preset
 */
export async function getDefaultFilterPreset(): Promise<FilterPreset> {
  const response = await safeFetch(`${getApiUrl()}/filter-presets/default`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<FilterPreset>(response);
}

/**
 * Create a new filter preset
 */
export async function createFilterPreset(data: FilterPresetCreate): Promise<FilterPreset> {
  const response = await safeFetch(`${getApiUrl()}/filter-presets`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<FilterPreset>(response);
}

/**
 * Update an existing filter preset
 */
export async function updateFilterPreset(
  id: string,
  data: FilterPresetUpdate
): Promise<FilterPreset> {
  const response = await safeFetch(`${getApiUrl()}/filter-presets/${id}`, {
    method: 'PATCH',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse<FilterPreset>(response);
}

/**
 * Delete a filter preset
 */
export async function deleteFilterPreset(id: string): Promise<void> {
  const response = await safeFetch(`${getApiUrl()}/filter-presets/${id}`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  await handleResponse<void>(response);
}

/**
 * Mark a filter preset as used (increment usage count)
 */
export async function markFilterPresetUsed(id: string): Promise<FilterPreset> {
  const response = await safeFetch(`${getApiUrl()}/filter-presets/${id}/use`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<FilterPreset>(response);
}

/**
 * Set a filter preset as the default
 */
export async function setFilterPresetDefault(id: string): Promise<FilterPreset> {
  const response = await safeFetch(`${getApiUrl()}/filter-presets/${id}/set-default`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<FilterPreset>(response);
}
