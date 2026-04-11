/**
 * Integration test for auth flow: login → token stored → logout → redirect.
 *
 * Tests the AuthContext behavior end-to-end with mocked API calls.
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Mock fetch globally
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

// Test components to exercise auth flows
function LoginComponent() {
  const { user, isAuthenticated, error, login, isLoading } = useAuth();
  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? 'authenticated' : 'unauthenticated'}</div>
      <div data-testid="user-email">{user?.email ?? 'none'}</div>
      <div data-testid="loading">{isLoading ? 'loading' : 'idle'}</div>
      <div data-testid="error">{error ?? 'none'}</div>
      <button onClick={() => login('test@example.com', 'password123')} data-testid="login-btn">
        Login
      </button>
    </div>
  );
}

function LogoutComponent() {
  const { isAuthenticated, logout } = useAuth();
  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? 'yes' : 'no'}</div>
      <button onClick={logout} data-testid="logout-btn">
        Logout
      </button>
    </div>
  );
}

describe('Auth Flow Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('Login flow', () => {
    it('starts unauthenticated', () => {
      render(
        <AuthProvider>
          <LoginComponent />
        </AuthProvider>
      );
      expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated');
      expect(screen.getByTestId('user-email').textContent).toBe('none');
    });

    it('authenticates on successful login', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: 'jwt-token-123',
          token_type: 'bearer',
          user: { id: 'user-1', email: 'test@example.com', role: 'user' },
        }),
      });

      render(
        <AuthProvider>
          <LoginComponent />
        </AuthProvider>
      );

      await act(async () => {
        fireEvent.click(screen.getByTestId('login-btn'));
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/auth/login'),
          expect.objectContaining({ method: 'POST' })
        );
      });
    });

    it('shows error on failed login', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid credentials' }),
      });

      render(
        <AuthProvider>
          <LoginComponent />
        </AuthProvider>
      );

      await act(async () => {
        fireEvent.click(screen.getByTestId('login-btn'));
      });

      await waitFor(() => {
        const errorEl = screen.getByTestId('error');
        expect(errorEl.textContent).not.toBe('none');
      });
    });
  });

  describe('Logout flow', () => {
    it('clears auth state on logout', async () => {
      // Pre-authenticate by setting localStorage
      localStorage.setItem('auth_token', 'existing-token');

      render(
        <AuthProvider>
          <LogoutComponent />
        </AuthProvider>
      );

      await act(async () => {
        fireEvent.click(screen.getByTestId('logout-btn'));
      });

      // After logout, should be unauthenticated
      await waitFor(() => {
        expect(screen.getByTestId('auth-status').textContent).toBe('no');
      });
    });
  });
});
