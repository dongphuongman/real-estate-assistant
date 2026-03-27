/**
 * Port configuration for frontend.
 *
 * Reads from environment variables or .env.ports equivalent.
 * Priority: BACKEND_API_URL env > NEXT_PUBLIC_API_URL > BACKEND_PORT > default
 */

/**
 * Get the backend API URL for frontend to use.
 *
 * Priority:
 * 1. BACKEND_API_URL environment variable (server-side only)
 * 2. NEXT_PUBLIC_API_URL environment variable
 * 3. Constructed from BACKEND_PORT
 * 4. Default: http://localhost:8000/api/v1
 */
export function getBackendApiUrl(): string {
  // Server-side: check BACKEND_API_URL first
  if (typeof process !== 'undefined' && process.env) {
    if (process.env.BACKEND_API_URL) {
      return process.env.BACKEND_API_URL;
    }

    // If NEXT_PUBLIC_API_URL is absolute, use it
    if (process.env.NEXT_PUBLIC_API_URL) {
      const url = process.env.NEXT_PUBLIC_API_URL;
      if (url.startsWith('http://') || url.startsWith('https://')) {
        return url;
      }
    }

    // Construct from BACKEND_PORT
    if (process.env.BACKEND_PORT) {
      const port = parseInt(process.env.BACKEND_PORT, 10);
      if (!isNaN(port)) {
        return `http://localhost:${port}/api/v1`;
      }
    }
  }

  // Default
  return 'http://localhost:8000/api/v1';
}

/**
 * Get the frontend port.
 *
 * Priority:
 * 1. PORT environment variable
 * 2. FRONTEND_PORT environment variable
 * 3. Default: 3000
 */
export function getFrontendPort(): number {
  if (typeof process !== 'undefined' && process.env) {
    const port = process.env.PORT || process.env.FRONTEND_PORT;
    if (port) {
      const parsed = parseInt(port, 10);
      if (!isNaN(parsed)) {
        return parsed;
      }
    }
  }
  return 3000;
}

/**
 * Get the frontend URL.
 *
 * Priority:
 * 1. FRONTEND_URL environment variable
 * 2. Constructed from FRONTEND_PORT
 * 3. Default: http://localhost:3000
 */
export function getFrontendUrl(): string {
  if (typeof process !== 'undefined' && process.env) {
    if (process.env.FRONTEND_URL) {
      return process.env.FRONTEND_URL;
    }

    const port = getFrontendPort();
    if (port !== 3000) {
      return `http://localhost:${port}`;
    }
  }
  return 'http://localhost:3000';
}

/**
 * Get all port configuration as an object.
 */
export function getPortConfig(): {
  backendApiUrl: string;
  frontendPort: number;
  frontendUrl: string;
} {
  return {
    backendApiUrl: getBackendApiUrl(),
    frontendPort: getFrontendPort(),
    frontendUrl: getFrontendUrl(),
  };
}

/**
 * Check if we're running with dynamic ports (i.e., .env.ports exists).
 * This can be used to enable/disable features based on port mode.
 */
export function isDynamicPortMode(): boolean {
  // If BACKEND_PORT is set and not the default, we're in dynamic mode
  if (typeof process !== 'undefined' && process.env) {
    const backendPort = process.env.BACKEND_PORT;
    if (backendPort && backendPort !== '8000') {
      return true;
    }
    const frontendPort = process.env.FRONTEND_PORT || process.env.PORT;
    if (frontendPort && frontendPort !== '3000') {
      return true;
    }
  }
  return false;
}

// Default export for convenience
export default {
  getBackendApiUrl,
  getFrontendPort,
  getFrontendUrl,
  getPortConfig,
  isDynamicPortMode,
};
