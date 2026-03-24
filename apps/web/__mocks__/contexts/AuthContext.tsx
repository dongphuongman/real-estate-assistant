import React from 'react';

// Mock for Auth/Auth context
export const useAuth = jest.fn(() => ({
  user: { id: 'test-user', email: 'test@test.com' },
  isAuthenticated: true,
  isLoading: false,
  login: jest.fn(async () => ({ success: true })),
  logout: jest.fn(async () => ({ success: true })),
  register: jest.fn(async () => ({ success: true })),
  token: 'test-token',
}));

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <>{children}</>;
};
