// Mock for next-intl/navigation to avoid ESM issues in Jest
import React from 'react';

export const useRouter = () => ({
  push: jest.fn(),
  replace: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  refresh: jest.fn(),
  prefetch: jest.fn(),
});

export const usePathname = () => '/';
export const useSearchParams = () => new URLSearchParams();
export const useLocale = () => 'en';

export const Link: React.FC<{ href: string; children: React.ReactNode; locale?: string }> = ({
  href,
  children,
}) => {
  return <a href={href}>{children}</a>;
};

export const redirect = jest.fn();
export const getPathname = jest.fn(() => '/');
export const createSharedPathnamesNavigation = () => ({
  Link,
  redirect,
  usePathname,
  useRouter,
});

const nextIntlNavigationMock = {
  useRouter,
  usePathname,
  useSearchParams,
  useLocale,
  Link,
  redirect,
  getPathname,
  createSharedPathnamesNavigation,
};

export default nextIntlNavigationMock;
