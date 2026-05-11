export const useRouter = () => ({
  push: jest.fn(),
  replace: jest.fn(),
  prefetch: jest.fn(),
  back: jest.fn(),
  forward: jest.fn(),
  refresh: jest.fn(),
  pathname: '/',
  query: {},
});

export const usePathname = () => '/';
export const useParams = () => ({});
export const redirect = jest.fn();
export const Link = ({ children, href }: { children: React.ReactNode; href: string }) => (
  <a href={href}>{children}</a>
);
