import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';

// Mock navigator before importing the module
const mockPushManager = {
  getSubscription: jest.fn(),
  subscribe: jest.fn(),
};

const mockServiceWorkerRegistration = {
  pushManager: mockPushManager,
  endpoint: 'https://push.example.com',
  showNotification: jest.fn(),
};

const mockServiceWorker = {
  ready: Promise.resolve(mockServiceWorkerRegistration),
};

const mockNotification = {
  requestPermission: jest.fn(),
  permission: 'default' as NotificationPermission,
};

// Set up global mocks
Object.defineProperty(global, 'navigator', {
  value: {
    serviceWorker: mockServiceWorker,
    Notification: mockNotification,
  },
  writable: true,
});

// Mock console methods
const originalConsole = { ...console };
beforeEach(() => {
  console.warn = jest.fn();
  console.log = jest.fn();
  console.error = jest.fn();
});

afterEach(() => {
  console.warn = originalConsole.warn;
  console.log = originalConsole.log;
  console.error = originalConsole.error;
});

// Import after mocks are set up
import {
  isPushSupported,
  requestNotificationPermission,
  getNotificationPermission,
  subscribeToPush,
  unsubscribeFromPush,
  getPushSubscription,
} from '../push';

describe('push notifications', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('isPushSupported', () => {
    it('should return true when serviceWorker and PushManager are available', () => {
      expect(isPushSupported()).toBe(true);
    });

    it('should return false when serviceWorker is not available', () => {
      Object.defineProperty(global, 'navigator', {
        value: {},
        writable: true,
      });
      expect(isPushSupported()).toBe(false);
      // Restore
      Object.defineProperty(global, 'navigator', {
        value: {
          serviceWorker: mockServiceWorker,
          Notification: mockNotification,
        },
        writable: true,
      });
    });
  });

  describe('getNotificationPermission', () => {
    it('should return current permission status', () => {
      mockNotification.permission = 'granted' as NotificationPermission;
      expect(getNotificationPermission()).toBe('granted');
    });

    it('should return denied when permission is denied', () => {
      mockNotification.permission = 'denied' as NotificationPermission;
      expect(getNotificationPermission()).toBe('denied');
    });
  });

  describe('requestNotificationPermission', () => {
    it('should return granted when user grants permission', async () => {
      mockNotification.requestPermission.mockResolvedValue('granted');
      const result = await requestNotificationPermission();
      expect(result).toBe('granted');
    });

    it('should return denied when user denies permission', async () => {
      mockNotification.requestPermission.mockResolvedValue('denied');
      const result = await requestNotificationPermission();
      expect(result).toBe('denied');
    });

    it('should return denied when Notification is not available', async () => {
      const originalNotification = mockNotification;
      Object.defineProperty(global.navigator, 'Notification', {
        value: undefined,
        writable: true,
      });
      const result = await requestNotificationPermission();
      expect(result).toBe('denied');
      expect(console.warn).toHaveBeenCalledWith('[Push] Push notifications are not supported');
      // Restore
      Object.defineProperty(global.navigator, 'Notification', {
        value: originalNotification,
        writable: true,
      });
    });
  });

  describe('getPushSubscription', () => {
    it('should return null when push is not supported', async () => {
      Object.defineProperty(global, 'navigator', {
        value: { Notification: mockNotification },
        writable: true,
      });
      const result = await getPushSubscription();
      expect(result).toBeNull();
      // Restore
      Object.defineProperty(global, 'navigator', {
        value: {
          serviceWorker: mockServiceWorker,
          Notification: mockNotification,
        },
        writable: true,
      });
    });

    it('should return subscription when available', async () => {
      const mockSubscription = { endpoint: 'https://push.example.com/sub/123' };
      mockPushManager.getSubscription.mockResolvedValue(mockSubscription);
      const result = await getPushSubscription();
      expect(result).toBe(mockSubscription);
    });

    it('should return null when error occurs', async () => {
      mockPushManager.getSubscription.mockRejectedValue(new Error('Get subscription error'));
      const result = await getPushSubscription();
      expect(result).toBeNull();
      expect(console.error).toHaveBeenCalledWith(
        '[Push] Error getting subscription:',
        expect.any(Error)
      );
    });
  });

  describe('subscribeToPush', () => {
    it('should return null when permission is denied', async () => {
      mockNotification.requestPermission.mockResolvedValue('denied');
      const result = await subscribeToPush();
      expect(result).toBeNull();
      expect(console.log).toHaveBeenCalledWith('[Push] Permission status:', 'denied');
    });

    it('should subscribe when permission is granted', async () => {
      mockNotification.requestPermission.mockResolvedValue('granted');
      const mockSubscription = { endpoint: 'https://push.example.com/sub/123' };
      mockPushManager.subscribe.mockResolvedValue(mockSubscription);
      const result = await subscribeToPush();
      expect(result).toBe(mockSubscription);
    });

    it('should return null when subscription fails', async () => {
      mockNotification.requestPermission.mockResolvedValue('granted');
      mockPushManager.subscribe.mockRejectedValue(new Error('Subscribe error'));
      const result = await subscribeToPush();
      expect(result).toBeNull();
      expect(console.error).toHaveBeenCalledWith('[Push] Error subscribing:', expect.any(Error));
    });
  });

  describe('unsubscribeFromPush', () => {
    it('should return true when successfully unsubscribed', async () => {
      const mockSubscription = {
        unsubscribe: jest.fn().mockResolvedValue(true),
      };
      mockPushManager.getSubscription.mockResolvedValue(mockSubscription);
      const result = await unsubscribeFromPush();
      expect(result).toBe(true);
      expect(mockSubscription.unsubscribe).toHaveBeenCalled();
      expect(console.log).toHaveBeenCalledWith('[Push] Successfully unsubscribed');
    });

    it('should return true when no subscription exists', async () => {
      mockPushManager.getSubscription.mockResolvedValue(null);
      const result = await unsubscribeFromPush();
      expect(result).toBe(true);
    });

    it('should return false when error occurs', async () => {
      mockPushManager.getSubscription.mockRejectedValue(new Error('Unsubscribe error'));
      const result = await unsubscribeFromPush();
      expect(result).toBe(false);
      expect(console.error).toHaveBeenCalledWith('[Push] Error unsubscribing:', expect.any(Error));
    });
  });
});
