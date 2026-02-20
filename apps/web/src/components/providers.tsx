'use client';

import { type ReactNode } from 'react';
import { AuthProvider } from '@/contexts/AuthContext';
import { FavoritesProvider } from '@/contexts/FavoritesContext';

interface ProvidersProps {
  children: ReactNode;
}

/**
 * Client component that wraps the app with all required context providers.
 * This is used in the root layout to provide auth context throughout the app.
 */
export function Providers({ children }: ProvidersProps) {
  return (
    <AuthProvider>
      <FavoritesProvider>{children}</FavoritesProvider>
    </AuthProvider>
  );
}
