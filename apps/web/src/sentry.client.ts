/**
 * Sentry client initialization for Next.js frontend.
 *
 * Configures Sentry SDK with user context from JWT tokens,
 * PII filtering, and session replay for debugging.
 */

import * as Sentry from '@sentry/nextjs';
import { browserTracingIntegration } from '@sentry/nextjs';
import { replayIntegration } from '@sentry/nextjs';

// PII fields to redact from Sentry events
const PII_FIELDS = new Set([
  'email',
  'password',
  'token',
  'authorization',
  'cookie',
  'x-api-key',
  'x-session-token',
  'query',
  'message',
  'question',
]);

/**
 * Filter PII from event before sending to Sentry.
 */
function beforeSend(event: Sentry.Event, _hint: Sentry.EventHint) {
  // Redact PII from request headers
  const request = event.request;
  if (request?.headers && typeof request.headers === 'object') {
    const headers = request.headers as Record<string, string>;
    Object.keys(headers).forEach((key) => {
      const normalizedKey = key.toLowerCase().replace(/-/g, '').replace(/_/g, '');
      if (PII_FIELDS.has(normalizedKey)) {
        headers[key] = '[Redacted]';
      }
    });
  }

  // Redact PII from request body
  if (request?.data && typeof request.data === 'object') {
    const data = request.data as Record<string, unknown>;
    Object.keys(data).forEach((key) => {
      if (PII_FIELDS.has(key.toLowerCase())) {
        data[key] = '[Redacted]';
      }
    });
  }

  // Redact from extra context
  if (event.extra && typeof event.extra === 'object') {
    const extra = event.extra as Record<string, unknown>;
    Object.keys(extra).forEach((key) => {
      if (PII_FIELDS.has(key.toLowerCase())) {
        extra[key] = '[Redacted]';
      }
    });
  }

  return event;
}

/**
 * Extract user context from JWT token in localStorage.
 * Returns hashed email for privacy (raw email never sent to Sentry).
 */
function getUserContext() {
  try {
    const token = localStorage.getItem('access_token');
    if (!token) {
      return null;
    }

    // Decode JWT payload (base64url)
    const parts = token.split('.');
    if (parts.length !== 3) {
      return null;
    }

    const payload = JSON.parse(atob(parts[1]));
    const userId = payload.sub;
    const email = payload.email;

    if (!userId) {
      return null;
    }

    // Hash email for privacy (SHA-256)
    let emailHash: string | undefined;
    if (email) {
      const encoder = new TextEncoder();
      const data = encoder.encode(email);
      crypto.subtle.digest('SHA-256', data).then((hashBuffer) => {
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        emailHash = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
      });
    }

    return {
      id: userId,
      emailHash,
    };
  } catch {
    return null;
  }
}

/**
 * Initialize Sentry for browser.
 */
export function initSentry() {
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  const environment = process.env.NEXT_PUBLIC_ENVIRONMENT || 'development';

  if (!dsn) {
    console.log('Sentry DSN not configured — error tracking disabled');
    return;
  }

  Sentry.init({
    dsn,
    environment,
    tracesSampleRate: environment === 'production' ? 0.1 : 0,
    replaysSessionSampleRate: environment === 'production' ? 0.1 : 0,
    replaysOnErrorSampleRate: 1.0,

    integrations: [
      browserTracingIntegration(),
      replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],

    beforeSend: beforeSend as Sentry.BrowserOptions['beforeSend'],

    // Don't send default PII
    sendDefaultPii: false,

    // Attach stack traces
    attachStacktrace: true,
    maxBreadcrumbs: 50,
  });

  // Set default tags for all events
  Sentry.setTag('component', 'frontend');
  Sentry.setTag('runtime', 'nextjs');

  // Set initial user context from JWT
  const user = getUserContext();
  if (user) {
    Sentry.setUser(user);
  }

  console.log(`Sentry initialized: env=${environment}`);
}

/**
 * Update Sentry user context after login/logout.
 */
export function updateSentryUser() {
  const user = getUserContext();
  if (user) {
    Sentry.setUser(user);
  } else {
    Sentry.setUser(null);
  }
}

/**
 * Add breadcrumb for debugging user actions.
 */
export function addBreadcrumb(
  category: string,
  message: string,
  level: Sentry.SeverityLevel = 'info',
  data?: Record<string, unknown>
) {
  Sentry.addBreadcrumb({
    category,
    message,
    level,
    data,
  });
}

/**
 * Capture error with additional context.
 */
export function captureError(error: Error, context?: Record<string, unknown>) {
  Sentry.captureException(error, {
    extra: context,
  });
}

/**
 * Capture message for non-error events.
 */
export function captureMessage(message: string, level: Sentry.SeverityLevel = 'info') {
  Sentry.captureMessage(message, level);
}
