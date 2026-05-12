/**
 * Zod schemas for runtime validation of API responses.
 *
 * These schemas provide runtime type safety for critical API responses,
 * complementing TypeScript's compile-time type checking.
 *
 * Usage:
 * ```typescript
 * import { PropertySchema, PropertiesResponseSchema } from '@/lib/schemas';
 *
 * // Validate single property
 * const property = PropertySchema.parse(apiResponse);
 *
 * // Validate paginated response
 * const response = PropertiesResponseSchema.parse(apiResponse);
 * ```
 */

import { z } from 'zod';

// =============================================================================
// Property Schemas
// =============================================================================

export const PropertyTypeEnum = z.enum([
  'apartment',
  'house',
  'studio',
  'loft',
  'townhouse',
  'other',
]);

export const ListingTypeEnum = z.enum(['rent', 'sale', 'room', 'sublease']);

export const PropertySchema = z.object({
  id: z.string().optional(),
  city: z.string(),
  property_type: PropertyTypeEnum,
  listing_type: ListingTypeEnum,
  latitude: z.number().optional(),
  longitude: z.number().optional(),
  price: z.number().optional(),
  area_sqm: z.number().optional(),
  bedrooms: z.number().optional(),
  bathrooms: z.number().optional(),
  title: z.string().optional(),
  description: z.string().optional(),
  address: z.string().optional(),
  district: z.string().optional(),
  images: z.array(z.string()).optional(),
  url: z.string().optional(),
  source: z.string().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export const PropertiesResponseSchema = z.object({
  properties: z.array(PropertySchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

// =============================================================================
// Authentication Schemas
// =============================================================================

export const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  name: z.string().optional(),
  is_active: z.boolean(),
  is_verified: z.boolean(),
  created_at: z.string(),
});

export const AuthResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string().optional(),
  token_type: z.literal('bearer'),
  expires_in: z.number(),
  user: UserSchema,
});

export const LoginRequestSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

export const RegisterRequestSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  name: z.string().optional(),
});

// =============================================================================
// Chat Schemas
// =============================================================================

export const ChatMessageSchema = z.object({
  role: z.enum(['user', 'assistant', 'system']),
  content: z.string(),
  timestamp: z.string().optional(),
});

export const ChatRequestSchema = z.object({
  message: z.string().min(1),
  session_id: z.string().optional(),
  stream: z.boolean().optional().default(false),
  include_intermediate_steps: z.boolean().optional().default(false),
});

export const ChatResponseSchema = z.object({
  response: z.string(),
  session_id: z.string(),
  sources: z.array(z.any()).optional(),
  intermediate_steps: z.array(z.any()).optional(),
});

// =============================================================================
// API Error Schema
// =============================================================================

export const ApiErrorSchema = z.object({
  detail: z.string(),
  error_code: z.string().optional(),
  request_id: z.string().optional(),
});

// =============================================================================
// Market Anomaly Schema
// =============================================================================

export const MarketAnomalySchema = z.object({
  id: z.string(),
  property_id: z.string(),
  anomaly_type: z.string(),
  severity: z.enum(['low', 'medium', 'high']),
  description: z.string(),
  detected_at: z.string(),
  data: z.record(z.string(), z.any()).optional(),
});

// =============================================================================
// Search Schemas
// =============================================================================

export const SearchFiltersSchema = z.object({
  city: z.string().optional(),
  property_type: PropertyTypeEnum.optional(),
  listing_type: ListingTypeEnum.optional(),
  min_price: z.number().optional(),
  max_price: z.number().optional(),
  min_area: z.number().optional(),
  max_area: z.number().optional(),
  bedrooms: z.number().optional(),
  bathrooms: z.number().optional(),
  district: z.string().optional(),
});

export const SearchRequestSchema = z.object({
  query: z.string().optional(),
  filters: SearchFiltersSchema.optional(),
  page: z.number().optional().default(1),
  page_size: z.number().optional().default(20),
  sort_by: z.string().optional(),
  sort_order: z.enum(['asc', 'desc']).optional(),
});

// =============================================================================
// Type exports (inferred from schemas)
// =============================================================================

export type Property = z.infer<typeof PropertySchema>;
export type PropertiesResponse = z.infer<typeof PropertiesResponseSchema>;
export type User = z.infer<typeof UserSchema>;
export type AuthResponse = z.infer<typeof AuthResponseSchema>;
export type ChatResponse = z.infer<typeof ChatResponseSchema>;
export type ApiError = z.infer<typeof ApiErrorSchema>;
export type MarketAnomaly = z.infer<typeof MarketAnomalySchema>;
export type SearchFilters = z.infer<typeof SearchFiltersSchema>;
export type SearchRequest = z.infer<typeof SearchRequestSchema>;
