/**
 * api.ts - Backward-compatible re-exports.
 *
 * All functions have been moved to domain-specific modules under ./api/.
 * This file re-exports everything so existing imports like
 * `import { searchProperties } from '@/lib/api'` continue to work unchanged.
 *
 * @see ./api/index.ts for the barrel export
 */
export * from './api/index';
