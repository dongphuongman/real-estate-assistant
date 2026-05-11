/**
 * Saved searches test fixtures for E2E tests.
 * Provides sample saved search data for list, toggle, and delete tests.
 */

export interface TestSavedSearch {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  filters: Record<string, unknown>;
  alert_frequency: 'instant' | 'daily' | 'weekly' | 'none';
  is_active: boolean;
  notify_on_new: boolean;
  notify_on_price_drop: boolean;
  created_at: string;
  updated_at: string;
  last_used_at?: string;
  use_count: number;
}

/**
 * Sample saved searches for list and interaction tests.
 */
export const TEST_SAVED_SEARCHES: TestSavedSearch[] = [
  {
    id: 'ss-001',
    user_id: 'test-user-basic-001',
    name: '2-bedroom Berlin',
    description: 'Looking for 2-bedroom apartments in Berlin',
    filters: { city: 'Berlin', min_rooms: 2, max_rooms: 2, property_types: ['apartment'] },
    alert_frequency: 'daily',
    is_active: true,
    notify_on_new: true,
    notify_on_price_drop: false,
    created_at: '2025-12-01T10:00:00Z',
    updated_at: '2025-12-15T14:30:00Z',
    last_used_at: '2025-12-15T14:30:00Z',
    use_count: 12,
  },
  {
    id: 'ss-002',
    user_id: 'test-user-basic-001',
    name: 'Apartment Krakow under 500k',
    description: 'Affordable apartments in Krakow',
    filters: { city: 'Krakow', max_price: 500000, property_types: ['apartment'] },
    alert_frequency: 'weekly',
    is_active: false,
    notify_on_new: false,
    notify_on_price_drop: true,
    created_at: '2025-11-20T08:00:00Z',
    updated_at: '2025-12-10T09:15:00Z',
    last_used_at: '2025-12-10T09:15:00Z',
    use_count: 5,
  },
  {
    id: 'ss-003',
    user_id: 'test-user-basic-001',
    name: 'Warsaw houses with garden',
    filters: { city: 'Warsaw', property_types: ['house'], features: ['garden'] },
    alert_frequency: 'instant',
    is_active: true,
    notify_on_new: true,
    notify_on_price_drop: true,
    created_at: '2025-10-05T16:00:00Z',
    updated_at: '2025-12-20T11:00:00Z',
    last_used_at: '2025-12-20T11:00:00Z',
    use_count: 28,
  },
];

/**
 * Get all test saved searches.
 */
export function getTestSavedSearches(): TestSavedSearch[] {
  return TEST_SAVED_SEARCHES;
}

/**
 * Get a test saved search by ID.
 */
export function getTestSavedSearchById(id: string): TestSavedSearch | undefined {
  return TEST_SAVED_SEARCHES.find((s) => s.id === id);
}

/**
 * Get the first active saved search.
 */
export function getActiveSavedSearch(): TestSavedSearch {
  const active = TEST_SAVED_SEARCHES.find((s) => s.is_active);
  if (!active) throw new Error('No active saved search in test fixtures');
  return active;
}

/**
 * Get the first inactive saved search.
 */
export function getInactiveSavedSearch(): TestSavedSearch {
  const inactive = TEST_SAVED_SEARCHES.find((s) => !s.is_active);
  if (!inactive) throw new Error('No inactive saved search in test fixtures');
  return inactive;
}
