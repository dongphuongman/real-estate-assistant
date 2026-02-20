import { NextResponse, type NextRequest } from 'next/server';

/**
 * Next.js Middleware for route protection.
 *
 * This middleware runs before each request to protect routes that require authentication.
 * It checks for valid session cookies and redirects unauthenticated users to the login page.
 *
 * Public routes (accessible without authentication):
 * - /auth/* - Authentication pages
 * - /api/v1/auth/* - Auth API endpoints
 * - /_next/* - Next.js internals
 * - /static/* - Static files
 * - /favicon.ico - Favicon
 *
 * Protected routes (require authentication):
 * - All other routes
 *
 * Note: This middleware checks for the access_token cookie set by the backend.
 * For more granular permission control, use the ProtectedRoute component on specific pages.
 */

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public routes that don't require authentication
  const isPublicRoute =
    pathname.startsWith('/auth/') ||
    pathname.startsWith('/api/v1/auth/') ||
    pathname.startsWith('/_next/') ||
    pathname.startsWith('/static/') ||
    pathname === '/favicon.ico';

  if (isPublicRoute) {
    return NextResponse.next();
  }

  // Check for access_token cookie (set by backend auth)
  const accessToken = request.cookies.get('access_token')?.value;

  if (!accessToken) {
    // No access token found, redirect to login
    const loginUrl = new URL('/auth/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Token exists, allow request
  // Note: The token will be validated on the backend when making API calls
  return NextResponse.next();
}

/**
 * Configure which routes the middleware should run on.
 *
 * By default, it runs on all routes except for:
 * - /api/v1/* - API routes (they have their own auth via the backend)
 * - /_next/* - Next.js internals
 * - /_vercel/* - Vercel internals
 * - /static/* - Static files
 * - /favicon.ico - Favicon
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - api routes that don't need middleware (handled by backend)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api/v1/|_next/static|_next/image|favicon.ico|static).*)',
  ],
};
