export const useRouter = () => ({
  push: jest.fn(),
  replace: jest.fn(),
  prefetch: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  refresh: jest.fn(),
  pathname: '/',
  query: {},
  asPath: '/',
  route: '/',
  events: {
    on: jest.fn(),
    off: jest.fn(),
    emit: jest.fn(),
  },
});

export const usePathname = () => '/';
export const useSearchParams = () => new URLSearchParams();
export const useParams = () => ({});
export const redirect = jest.fn();
export const notFound = jest.fn();
