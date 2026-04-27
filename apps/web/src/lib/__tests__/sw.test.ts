import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Mock logger
jest.mock('@/lib/logger', () => ({
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
}));

// Store for window event listeners
const eventListeners: Record<string, ((...args: unknown[]) => void)[]> = {};

// Setup mocks on global window (already exists in jsdom)
const mockRegister = jest.fn();
const mockGetRegistration = jest.fn();
const mockUnregister = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
  for (const key in eventListeners) delete eventListeners[key];

  // Mock navigator.serviceWorker on existing global
  Object.defineProperty(globalThis, 'navigator', {
    value: {
      serviceWorker: {
        register: mockRegister,
        getRegistration: mockGetRegistration,
        controller: null,
      },
    },
    writable: true,
    configurable: true,
  });

  // Mock matchMedia on jsdom window
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockReturnValue({ matches: false }),
  });

  // Spy on window.addEventListener to capture listeners
  jest
    .spyOn(window, 'addEventListener')
    .mockImplementation(
      (event: string, fn: EventListenerOrEventListenerObject | ((...args: unknown[]) => void)) => {
        if (!eventListeners[event]) eventListeners[event] = [];
        if (typeof fn === 'function') eventListeners[event].push(fn);
      }
    );

  jest.spyOn(window, 'dispatchEvent').mockReturnValue(true);
});

import {
  registerServiceWorker,
  canInstallPWA,
  promptPWAInstall,
  isStandalonePWA,
  isServiceWorkerActive,
  getServiceWorkerRegistration,
  unregisterServiceWorker,
} from '@/lib/sw';

describe('registerServiceWorker', () => {
  it('adds load, beforeinstallprompt, appinstalled listeners', () => {
    registerServiceWorker();

    const events = (window.addEventListener as jest.Mock).mock.calls.map((c) => c[0]);
    expect(events).toContain('load');
    expect(events).toContain('beforeinstallprompt');
    expect(events).toContain('appinstalled');
  });

  it('registers service worker on load', async () => {
    mockRegister.mockResolvedValue({
      scope: '/',
      addEventListener: jest.fn(),
      installing: null,
    });

    registerServiceWorker();

    const loadListeners = eventListeners['load'];
    expect(loadListeners).toBeDefined();
    expect(loadListeners!.length).toBeGreaterThan(0);

    await loadListeners![0]();
    expect(mockRegister).toHaveBeenCalledWith('/sw.js', { scope: '/' });
  });

  it('handles registration failure gracefully', async () => {
    mockRegister.mockRejectedValue(new Error('Failed'));

    registerServiceWorker();

    const loadListeners = eventListeners['load'];
    if (loadListeners) {
      await loadListeners[0](); // Should not throw
    }
  });

  it('handles beforeinstallprompt event', () => {
    registerServiceWorker();

    const listeners = eventListeners['beforeinstallprompt'];
    expect(listeners).toBeDefined();

    const fakeEvent = { preventDefault: jest.fn() };
    if (listeners) {
      listeners[0](fakeEvent);
      expect(fakeEvent.preventDefault).toHaveBeenCalled();
    }
  });

  it('handles appinstalled event', () => {
    registerServiceWorker();

    const listeners = eventListeners['appinstalled'];
    expect(listeners).toBeDefined();
    if (listeners) {
      listeners[0](); // Should not throw
    }
  });
});

describe('canInstallPWA', () => {
  it('returns false when no deferred prompt', () => {
    expect(canInstallPWA()).toBe(false);
  });
});

describe('promptPWAInstall', () => {
  it('returns false when no deferred prompt', async () => {
    const result = await promptPWAInstall();
    expect(result).toBe(false);
  });
});

describe('isStandalonePWA', () => {
  it('returns false when matchMedia returns false', () => {
    (window.matchMedia as jest.Mock).mockReturnValue({ matches: false });
    expect(isStandalonePWA()).toBe(false);
  });

  it('returns true when matchMedia matches standalone', () => {
    (window.matchMedia as jest.Mock).mockReturnValue({ matches: true });
    expect(isStandalonePWA()).toBe(true);
  });
});

describe('isServiceWorkerActive', () => {
  it('returns false when no controller', () => {
    expect(isServiceWorkerActive()).toBe(false);
  });

  it('returns true when controller exists', () => {
    Object.defineProperty(globalThis, 'navigator', {
      value: {
        serviceWorker: {
          controller: { state: 'activated' },
        },
      },
      writable: true,
      configurable: true,
    });

    expect(isServiceWorkerActive()).toBe(true);
  });
});

describe('getServiceWorkerRegistration', () => {
  it('returns null when no registration', async () => {
    mockGetRegistration.mockResolvedValue(undefined);
    const result = await getServiceWorkerRegistration();
    expect(result).toBeNull();
  });

  it('returns registration when found', async () => {
    const mockReg = { scope: '/' };
    mockGetRegistration.mockResolvedValue(mockReg);
    const result = await getServiceWorkerRegistration();
    expect(result).toBe(mockReg);
  });
});

describe('unregisterServiceWorker', () => {
  it('returns false when no registration', async () => {
    mockGetRegistration.mockResolvedValue(undefined);
    const result = await unregisterServiceWorker();
    expect(result).toBe(false);
  });

  it('returns true when unregistration succeeds', async () => {
    mockGetRegistration.mockResolvedValue({ unregister: mockUnregister });
    mockUnregister.mockResolvedValue(true);
    const result = await unregisterServiceWorker();
    expect(result).toBe(true);
  });

  it('returns false when unregistration fails', async () => {
    mockGetRegistration.mockResolvedValue({ unregister: mockUnregister });
    mockUnregister.mockResolvedValue(false);
    const result = await unregisterServiceWorker();
    expect(result).toBe(false);
  });
});
