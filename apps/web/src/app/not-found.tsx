import Link from 'next/link';
import { Home, Search } from 'lucide-react';

/**
 * Custom 404 page (Task #68).
 */
export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center">
      <h1 className="text-6xl font-bold text-muted-foreground/30 mb-4">404</h1>
      <h2 className="text-xl font-semibold mb-2">Page not found</h2>
      <p className="text-muted-foreground mb-6 max-w-md">
        The page you are looking for does not exist or has been moved.
      </p>
      <div className="flex gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Home className="h-4 w-4" />
          Go home
        </Link>
        <Link
          href="/search"
          className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
        >
          <Search className="h-4 w-4" />
          Search properties
        </Link>
      </div>
    </div>
  );
}
