/**
 * Tests for push.ts — Web Push notification utilities.
 *
 * Mocks Notification API, navigator.serviceWorker, and PushManager
 * to achieve comprehensive coverage of all exported functions.
 */

import { jest } from '@jest/globals';

// Suppress console output during tests
const mockConsoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
const mockConsoleInfo = jest.spyOn(console, 'info').mockImplementation(() => {});
const mockConsoleWarn = jest.spyOn(console, 'warn').mockImplementation(() => {});

// ─── Mock Notification API ────────────────────────────────────────────────
const mockRequestPermission = jest.fn<Promise<NotificationPermission>, []>();

class MockNotification {
  static permission: NotificationPermission = 'default';
  static requestPermission = mockRequestPermission;
}

// @ts-expect-error - mocking Notification global
global.Notification = MockNotification;

// ─── Mock PushManager ─────────────────────────────────────────────────────
const mockGetSubscription = jest.fn<Promise<PushSubscription | null>, []>();
const mockSubscribe = jest.fn<Promise<PushSubscription>, [PushSubscriptionOptionsInit]>();

const mockPushManager = {
  getSubscription: mockGetSubscription,
  subscribe: mockSubscribe,
  supportedContentEncodings: ['aes128gcm', 'aesgcm'] as readonly string[],
  permissionState: jest.fn<Promise<PushPermissionState>, [PushSubscriptionOptionsInit?]>(),
};

// ─── Mock ServiceWorkerRegistration ───────────────────────────────────────
const mockShowNotification = jest.fn<Promise<void>, [string, NotificationOptions?]>();

const mockRegistration = {
  pushManager: mockPushManager,
  showNotification: mockShowNotification,
  active: {} as ServiceWorker,
  installing: null as ServiceWorker | null,
  waiting: null as ServiceWorker | null,
  scope: '/',
  updateViaCache: 'all' as ServiceWorkerUpdateViaCache,
  unregister: jest.fn<Promise<boolean>, []>(),
  update: jest.fn<Promise<void>, []>(),
};

// ─── Replace navigator.serviceWorker entirely ─────────────────────────────
// We create a full mock with a `ready` getter that returns a fresh Promise each time.
const mockServiceWorker = {
  get ready(): Promise<typeof mockRegistration> {
    return Promise.resolve(mockRegistration);
  },
  register: jest.fn(),
  getRegistration: jest.fn(),
  getRegistrations: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
};

// Completely replace navigator.serviceWorker via the prototype chain
Object.defineProperty(global.navigator, 'serviceWorker', {
  value: mockServiceWorker,
  writable: true,
  configurable: true,
});

// ─── Set up PushManager in window ─────────────────────────────────────────
// isPushSupported checks: 'PushManager' in window
(window as Record<string, unknown>).PushManager = function PushManager() {};

// ─── Helper: create mock PushSubscription ─────────────────────────────────
function createMockSubscription(overrides?: {
  endpoint?: string;
  p256dh?: Uint8Array;
  auth?: Uint8Array;
  unsubscribeResult?: boolean;
}): PushSubscription {
  const p256dh = overrides?.p256dh ?? new Uint8Array([1, 2, 3, 4]);
  const auth = overrides?.auth ?? new Uint8Array([5, 6, 7, 8]);

  return {
    endpoint: overrides?.endpoint ?? 'https://push.example.com/subscription/123',
    expirationTime: null,
    getKey: jest.fn((name: PushEncryptionKeyName): ArrayBuffer | null => {
      if (name === 'p256dh') return p256dh.buffer as ArrayBuffer;
      if (name === 'auth') return auth.buffer as ArrayBuffer;
      return null;
    }),
    toJSON: jest.fn(),
    unsubscribe: jest
      .fn<Promise<boolean>, []>()
      .mockResolvedValue(overrides?.unsubscribeResult ?? true),
  } as unknown as PushSubscription;
}

beforeEach(() => {
  // Reset all mocks and set fresh defaults
  mockGetSubscription.mockReset();
  mockSubscribe.mockReset();
  mockShowNotification.mockReset();
  mockRequestPermission.mockReset();

  MockNotification.permission = 'default';
  mockRequestPermission.mockResolvedValue('granted');

  mockGetSubscription.mockResolvedValue(null);
  mockSubscribe.mockResolvedValue(createMockSubscription());
  mockShowNotification.mockResolvedValue(undefined);

  // Ensure navigator.serviceWorker is properly set up
  Object.defineProperty(global.navigator, 'serviceWorker', {
    value: mockServiceWorker,
    writable: true,
    configurable: true,
  });
});

afterAll(() => {
  mockConsoleError.mockRestore();
  mockConsoleInfo.mockRestore();
  mockConsoleWarn.mockRestore();
});

// Import after all mocks are in place
import {
  isPushSupported,
  getNotificationPermission,
  areNotificationsEnabled,
  requestNotificationPermission,
  getPushSubscription,
  isSubscribedToPush,
  subscribeToPush,
  unsubscribeFromPush,
  getSubscriptionDetails,
  showLocalNotification,
} from '../push';

// =============================================================================
// isPushSupported
// =============================================================================
describe('isPushSupported', () => {
  it('returns true when PushManager and serviceWorker are available', () => {
    expect(isPushSupported()).toBe(true);
  });

  it('returns false when PushManager is deleted from window', () => {
    const saved = (window as Record<string, unknown>).PushManager;
    delete (window as Record<string, unknown>).PushManager;
    expect(isPushSupported()).toBe(false);
    (window as Record<string, unknown>).PushManager = saved;
  });

  it('returns false when navigator.serviceWorker is undefined', () => {
    // Delete serviceWorker property entirely so 'serviceWorker' in navigator is false
    delete (global.navigator as Record<string, unknown>).serviceWorker;
    expect(isPushSupported()).toBe(false);
    // Restore
    Object.defineProperty(global.navigator, 'serviceWorker', {
      value: mockServiceWorker,
      writable: true,
      configurable: true,
    });
  });
});

// =============================================================================
// getNotificationPermission
// =============================================================================
describe('getNotificationPermission', () => {
  it('returns granted', () => {
    MockNotification.permission = 'granted';
    expect(getNotificationPermission()).toBe('granted');
  });

  it('returns denied', () => {
    MockNotification.permission = 'denied';
    expect(getNotificationPermission()).toBe('denied');
  });

  it('returns default', () => {
    MockNotification.permission = 'default';
    expect(getNotificationPermission()).toBe('default');
  });
});

// =============================================================================
// areNotificationsEnabled
// =============================================================================
describe('areNotificationsEnabled', () => {
  it('returns true when permission is granted', () => {
    MockNotification.permission = 'granted';
    expect(areNotificationsEnabled()).toBe(true);
  });

  it('returns false when permission is denied', () => {
    MockNotification.permission = 'denied';
    expect(areNotificationsEnabled()).toBe(false);
  });

  it('returns false when permission is default', () => {
    MockNotification.permission = 'default';
    expect(areNotificationsEnabled()).toBe(false);
  });
});

// =============================================================================
// requestNotificationPermission
// =============================================================================
describe('requestNotificationPermission', () => {
  it('returns granted when user grants permission', async () => {
    mockRequestPermission.mockResolvedValueOnce('granted');
    const result = await requestNotificationPermission();
    expect(result).toBe('granted');
  });

  it('returns denied when user denies permission', async () => {
    mockRequestPermission.mockResolvedValueOnce('denied');
    const result = await requestNotificationPermission();
    expect(result).toBe('denied');
  });

  it('returns denied when push is not supported', async () => {
    const saved = (window as Record<string, unknown>).PushManager;
    delete (window as Record<string, unknown>).PushManager;
    const result = await requestNotificationPermission();
    expect(result).toBe('denied');
    (window as Record<string, unknown>).PushManager = saved;
  });

  it('returns denied when requestPermission throws', async () => {
    mockRequestPermission.mockRejectedValueOnce(new Error('API error'));
    const result = await requestNotificationPermission();
    expect(result).toBe('denied');
  });
});

// =============================================================================
// getPushSubscription
// =============================================================================
describe('getPushSubscription', () => {
  it('returns subscription when available', async () => {
    const sub = createMockSubscription();
    mockGetSubscription.mockResolvedValueOnce(sub);
    const result = await getPushSubscription();
    expect(result).toBe(sub);
  });

  it('returns null when not subscribed', async () => {
    mockGetSubscription.mockResolvedValueOnce(null);
    const result = await getPushSubscription();
    expect(result).toBeNull();
  });

  it('returns null when push is not supported', async () => {
    const saved = (window as Record<string, unknown>).PushManager;
    delete (window as Record<string, unknown>).PushManager;
    const result = await getPushSubscription();
    expect(result).toBeNull();
    (window as Record<string, unknown>).PushManager = saved;
  });

  it('returns null when serviceWorker.ready rejects', async () => {
    const failingSW = {
      get ready() {
        return Promise.reject(new Error('No SW'));
      },
    };
    Object.defineProperty(global.navigator, 'serviceWorker', {
      value: failingSW,
      writable: true,
      configurable: true,
    });
    const result = await getPushSubscription();
    expect(result).toBeNull();
  });
});

// =============================================================================
// isSubscribedToPush
// =============================================================================
describe('isSubscribedToPush', () => {
  it('returns true when subscription exists', async () => {
    mockGetSubscription.mockResolvedValueOnce(createMockSubscription());
    expect(await isSubscribedToPush()).toBe(true);
  });

  it('returns false when no subscription', async () => {
    mockGetSubscription.mockResolvedValueOnce(null);
    expect(await isSubscribedToPush()).toBe(false);
  });
});

// =============================================================================
// subscribeToPush
// =============================================================================
describe('subscribeToPush', () => {
  it('creates new subscription and returns it', async () => {
    mockGetSubscription.mockResolvedValueOnce(null);
    const newSub = createMockSubscription();
    mockSubscribe.mockResolvedValueOnce(newSub);

    const result = await subscribeToPush(
      'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkOsGsGhXHg'
    );
    expect(result).toBe(newSub);
    expect(mockSubscribe).toHaveBeenCalledTimes(1);
    expect(mockSubscribe.mock.calls[0][0].userVisibleOnly).toBe(true);
  });

  it('returns existing subscription without creating new one', async () => {
    const existingSub = createMockSubscription();
    mockGetSubscription.mockResolvedValueOnce(existingSub);

    const result = await subscribeToPush(
      'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkOsGsGhXHg'
    );
    expect(result).toBe(existingSub);
    expect(mockSubscribe).not.toHaveBeenCalled();
  });

  it('returns null when push is not supported', async () => {
    const saved = (window as Record<string, unknown>).PushManager;
    delete (window as Record<string, unknown>).PushManager;
    const result = await subscribeToPush('test-key');
    expect(result).toBeNull();
    (window as Record<string, unknown>).PushManager = saved;
  });

  it('returns null when permission is not granted', async () => {
    mockRequestPermission.mockResolvedValueOnce('denied');
    const result = await subscribeToPush('test-key');
    expect(result).toBeNull();
  });

  it('returns null when subscribe throws', async () => {
    mockGetSubscription.mockResolvedValueOnce(null);
    mockSubscribe.mockRejectedValueOnce(new Error('Subscribe failed'));
    const result = await subscribeToPush(
      'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkOsGsGhXHg'
    );
    expect(result).toBeNull();
  });
});

// =============================================================================
// unsubscribeFromPush
// =============================================================================
describe('unsubscribeFromPush', () => {
  it('returns true when no subscription exists (nothing to do)', async () => {
    mockGetSubscription.mockResolvedValueOnce(null);
    expect(await unsubscribeFromPush()).toBe(true);
  });

  it('returns true when unsubscribe succeeds', async () => {
    const sub = createMockSubscription({ unsubscribeResult: true });
    mockGetSubscription.mockResolvedValueOnce(sub);
    expect(await unsubscribeFromPush()).toBe(true);
  });

  it('returns false when unsubscribe returns false', async () => {
    const sub = createMockSubscription({ unsubscribeResult: false });
    mockGetSubscription.mockResolvedValueOnce(sub);
    expect(await unsubscribeFromPush()).toBe(false);
  });

  it('returns false when unsubscribe throws', async () => {
    const sub = createMockSubscription();
    (sub.unsubscribe as jest.Mock).mockRejectedValueOnce(new Error('Unsub failed'));
    mockGetSubscription.mockResolvedValueOnce(sub);
    expect(await unsubscribeFromPush()).toBe(false);
  });
});

// =============================================================================
// getSubscriptionDetails
// =============================================================================
describe('getSubscriptionDetails', () => {
  it('returns null when no subscription', async () => {
    mockGetSubscription.mockResolvedValueOnce(null);
    expect(await getSubscriptionDetails()).toBeNull();
  });

  it('returns null when getKey returns null for p256dh', async () => {
    const sub = {
      endpoint: 'https://push.example.com/sub',
      getKey: jest.fn((name: string): ArrayBuffer | null => {
        if (name === 'p256dh') return null;
        return new Uint8Array([5, 6, 7, 8]).buffer as ArrayBuffer;
      }),
    } as unknown as PushSubscription;
    mockGetSubscription.mockResolvedValueOnce(sub);
    expect(await getSubscriptionDetails()).toBeNull();
  });

  it('returns null when getKey returns null for auth', async () => {
    const sub = {
      endpoint: 'https://push.example.com/sub',
      getKey: jest.fn((name: string): ArrayBuffer | null => {
        if (name === 'auth') return null;
        return new Uint8Array([1, 2, 3, 4]).buffer as ArrayBuffer;
      }),
    } as unknown as PushSubscription;
    mockGetSubscription.mockResolvedValueOnce(sub);
    expect(await getSubscriptionDetails()).toBeNull();
  });

  it('returns subscription details with endpoint and keys', async () => {
    const p256dh = new Uint8Array([1, 2, 3, 4]);
    const auth = new Uint8Array([5, 6, 7, 8]);
    const sub = {
      endpoint: 'https://push.example.com/sub/abc',
      getKey: jest.fn((name: string): ArrayBuffer | null => {
        if (name === 'p256dh') return p256dh.buffer as ArrayBuffer;
        if (name === 'auth') return auth.buffer as ArrayBuffer;
        return null;
      }),
    } as unknown as PushSubscription;
    mockGetSubscription.mockResolvedValueOnce(sub);

    const details = await getSubscriptionDetails();
    expect(details).not.toBeNull();
    expect(details!.endpoint).toBe('https://push.example.com/sub/abc');
    expect(details!.keys.p256dh).toBe(btoa(String.fromCharCode(...p256dh)));
    expect(details!.keys.auth).toBe(btoa(String.fromCharCode(...auth)));
  });
});

// =============================================================================
// showLocalNotification
// =============================================================================
describe('showLocalNotification', () => {
  it('shows notification with default icon and badge', async () => {
    MockNotification.permission = 'granted';
    await showLocalNotification('Hello', { body: 'World' });
    expect(mockShowNotification).toHaveBeenCalledWith(
      'Hello',
      expect.objectContaining({
        icon: '/icon-192x192.png',
        badge: '/icon-192x192.png',
        body: 'World',
      })
    );
  });

  it('does nothing when push is not supported', async () => {
    const saved = (window as Record<string, unknown>).PushManager;
    delete (window as Record<string, unknown>).PushManager;
    await showLocalNotification('Test');
    expect(mockShowNotification).not.toHaveBeenCalled();
    (window as Record<string, unknown>).PushManager = saved;
  });

  it('does nothing when permission is not granted', async () => {
    MockNotification.permission = 'denied';
    await showLocalNotification('Test');
    expect(mockShowNotification).not.toHaveBeenCalled();
  });

  it('swallows errors from showNotification', async () => {
    MockNotification.permission = 'granted';
    mockShowNotification.mockRejectedValueOnce(new Error('SW error'));
    await expect(showLocalNotification('Test')).resolves.toBeUndefined();
  });

  it('allows custom options to override defaults', async () => {
    MockNotification.permission = 'granted';
    await showLocalNotification('Title', { icon: '/custom-icon.png', body: 'Custom body' });
    expect(mockShowNotification).toHaveBeenCalledWith(
      'Title',
      expect.objectContaining({
        icon: '/custom-icon.png',
        badge: '/icon-192x192.png',
        body: 'Custom body',
      })
    );
  });
});
