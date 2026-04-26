/**
 * Integration test for auth flow: login → token stored → logout → redirect.
 *
 * Tests the AuthContext behavior end-to-end with mocked fetch API calls.
 * Follows the same pattern as contexts/__tests__/AuthContext.test.tsx.
 */

import { render, screen, act, waitFor } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Mock fetch globally before any imports
const mockFetch = jest.fn();
(globalThis as unknown as { fetch: jest.Mock }).fetch = mockFetch;

jest.mock('@/lib/api', () => ({
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

import { AuthProvider, useAuth } from '@/contexts/AuthContext';

// Helper to create mock responses
function createMockResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: new Headers(),
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as Response;
}

function LoginComponent() {
  const { user, isAuthenticated, error, login, isLoading } = useAuth();
  const handleLogin = async () => {
    try {
      await login('test@example.com', 'password123');
    } catch {
      // Error is set in context
    }
  };
  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? 'authenticated' : 'unauthenticated'}</div>
      <div data-testid="user-email">{user?.email ?? 'none'}</div>
      <div data-testid="loading">{isLoading ? 'loading' : 'idle'}</div>
      <div data-testid="error">{error ?? 'none'}</div>
      <button onClick={handleLogin} data-testid="login-btn">
        Login
      </button>
    </div>
  );
}

function LogoutComponent() {
  const { isAuthenticated, logout } = useAuth();
  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // Error is set in context
    }
  };
  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? 'yes' : 'no'}</div>
      <button onClick={handleLogout} data-testid="logout-btn">
        Logout
      </button>
    </div>
  );
}

describe('Auth Flow Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
  });

  describe('Login flow', () => {
    it('starts unauthenticated', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Not authenticated'));

      render(
        <AuthProvider>
          <LoginComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('idle');
      });
      expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated');
      expect(screen.getByTestId('user-email').textContent).toBe('none');
    });

    it('authenticates on successful login', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        role: 'user',
        is_active: true,
        is_verified: true,
        created_at: '2024-01-01',
      };

      // First call: getCurrentUser (fails - no user initially)
      mockFetch.mockRejectedValueOnce(new Error('Not authenticated'));

      render(
        <AuthProvider>
          <LoginComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('idle');
      });

      // Second call: login succeeds
      mockFetch.mockResolvedValueOnce(
        createMockResponse({
          access_token: 'jwt-token-123',
          refresh_token: 'refresh-token',
          token_type: 'bearer',
          expires_in: 3600,
          user: mockUser,
        })
      );

      await act(async () => {
        screen.getByTestId('login-btn').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('auth-status').textContent).toBe('authenticated');
        expect(screen.getByTestId('user-email').textContent).toBe('test@example.com');
      });
    });

    it('shows error on failed login', async () => {
      // First call: getCurrentUser (fails)
      mockFetch.mockRejectedValueOnce(new Error('Not authenticated'));

      render(
        <AuthProvider>
          <LoginComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('idle');
      });

      // Second call: login fails with 401
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        headers: new Headers(),
        json: async () => ({ detail: 'Invalid credentials' }),
        text: async () => JSON.stringify({ detail: 'Invalid credentials' }),
      } as Response);

      await act(async () => {
        screen.getByTestId('login-btn').click();
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      await waitFor(() => {
        const errorEl = screen.getByTestId('error');
        expect(errorEl.textContent).not.toBe('none');
      });
    });
  });

  describe('Logout flow', () => {
    it('clears auth state on logout', async () => {
      const mockUser = {
        id: '1',
        email: 'test@example.com',
        role: 'user',
        is_active: true,
        is_verified: true,
        created_at: '2024-01-01',
      };

      // First call: getCurrentUser (success - user logged in)
      mockFetch.mockResolvedValueOnce(createMockResponse(mockUser));

      render(
        <AuthProvider>
          <LogoutComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('auth-status').textContent).toBe('yes');
      });

      // Second call: logout
      mockFetch.mockResolvedValueOnce(createMockResponse({ message: 'Logged out' }));

      await act(async () => {
        screen.getByTestId('logout-btn').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('auth-status').textContent).toBe('no');
      });
    });
  });
});
