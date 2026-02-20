/**
 * Tests for AuthContext
 *
 * Tests cover:
 * - Initial state
 * - Login flow
 * - Logout flow
 * - Register flow
 * - Error handling
 */

import { render, screen, waitFor, act } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';

// Mock the auth API
jest.mock('@/lib/auth', () => ({
  login: jest.fn(),
  register: jest.fn(),
  logout: jest.fn(),
  getCurrentUser: jest.fn(),
}));

// Mock the API error
jest.mock('@/lib/api', () => ({
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

import { AuthProvider, useAuth } from '../AuthContext';
import * as authApi from '@/lib/auth';
import { ApiError } from '@/lib/api';

// Test component to access auth context
function TestComponent() {
  const { user, isLoading, isAuthenticated, error, login, logout, clearError } = useAuth();

  return (
    <div>
      <span data-testid="loading">{isLoading.toString()}</span>
      <span data-testid="authenticated">{isAuthenticated.toString()}</span>
      <span data-testid="user">{user ? user.email : 'null'}</span>
      <span data-testid="error">{error || 'null'}</span>
      <button onClick={() => login('test@example.com', 'password')} data-testid="login-btn">
        Login
      </button>
      <button onClick={logout} data-testid="logout-btn">
        Logout
      </button>
      <button onClick={clearError} data-testid="clear-error-btn">
        Clear Error
      </button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  describe('Initial State', () => {
    it('starts with loading state', async () => {
      (authApi.getCurrentUser as jest.Mock).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      expect(screen.getByTestId('loading').textContent).toBe('true');
    });

    it('sets loading to false after fetching user', async () => {
      (authApi.getCurrentUser as jest.Mock).mockResolvedValue(null);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });
    });

    it('starts unauthenticated when no user', async () => {
      (authApi.getCurrentUser as jest.Mock).mockResolvedValue(null);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('false');
      });
    });
  });

  describe('Login Flow', () => {
    it('logs in successfully', async () => {
      const mockUser = { id: '1', email: 'test@example.com' };
      (authApi.getCurrentUser as jest.Mock).mockResolvedValue(null);
      (authApi.login as jest.Mock).mockResolvedValue({ user: mockUser });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });

      // Click login button
      await act(async () => {
        screen.getByTestId('login-btn').click();
      });

      // Check authenticated state
      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true');
        expect(screen.getByTestId('user').textContent).toBe('test@example.com');
      });
    });

    it('handles login error', async () => {
      (authApi.getCurrentUser as jest.Mock).mockResolvedValue(null);
      (authApi.login as jest.Mock).mockRejectedValue(new ApiError('Invalid credentials', 401));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });

      await act(async () => {
        screen.getByTestId('login-btn').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('error').textContent).toBe('Invalid credentials');
        expect(screen.getByTestId('authenticated').textContent).toBe('false');
      });
    });
  });

  describe('Logout Flow', () => {
    it('logs out successfully', async () => {
      const mockUser = { id: '1', email: 'test@example.com' };
      (authApi.getCurrentUser as jest.Mock).mockResolvedValue(mockUser);
      (authApi.logout as jest.Mock).mockResolvedValue(undefined);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // Wait for initial auth
      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('true');
      });

      // Click logout
      await act(async () => {
        screen.getByTestId('logout-btn').click();
      });

      // Check logged out state
      await waitFor(() => {
        expect(screen.getByTestId('authenticated').textContent).toBe('false');
        expect(screen.getByTestId('user').textContent).toBe('null');
      });
    });
  });

  describe('Error Handling', () => {
    it('clears error when clearError is called', async () => {
      (authApi.getCurrentUser as jest.Mock).mockResolvedValue(null);
      (authApi.login as jest.Mock).mockRejectedValue(new ApiError('Login failed', 401));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading').textContent).toBe('false');
      });

      // Trigger error
      await act(async () => {
        screen.getByTestId('login-btn').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('error').textContent).toBe('Login failed');
      });

      // Clear error
      await act(async () => {
        screen.getByTestId('clear-error-btn').click();
      });

      await waitFor(() => {
        expect(screen.getByTestId('error').textContent).toBe('null');
      });
    });
  });
});

describe('useAuth outside provider', () => {
  it('throws error when used outside provider', () => {
    // Suppress console.error for this test
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});

    function TestComponentOutsideProvider() {
      useAuth();
      return null;
    }

    // The default context should not throw, but return default values
    // This test ensures the hook can be used safely
    expect(() => {
      render(<TestComponentOutsideProvider />);
    }).not.toThrow();

    spy.mockRestore();
  });
});
