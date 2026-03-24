// Mock for next/navigation hooks to avoid ESM issues in Jest
// This complements the next-intl/navigation mock

const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  refresh: jest.fn(),
  prefetch: jest.fn(),
};

export const useRouter = () => mockRouter;

export const usePathname = () => '/';

export const useSearchParams = () => new URLSearchParams();

export const redirect = jest.fn();

export const notFound = jest.fn();

// Reset mocks between tests
beforeEach(() => {
  jest.clearAllMocks();
});

const nextNavigationMock = {
  useRouter,
  usePathname,
  useSearchParams,
  redirect,
  notFound,
};

export default nextNavigationMock;
