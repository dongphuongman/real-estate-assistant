import { describe, it, expect } from '@jest/globals';
import {
  PropertySchema,
  PropertiesResponseSchema,
  UserSchema,
  AuthResponseSchema,
  LoginRequestSchema,
  RegisterRequestSchema,
  ChatMessageSchema,
  ChatRequestSchema,
  ChatResponseSchema,
  ApiErrorSchema,
  MarketAnomalySchema,
  SearchFiltersSchema,
  SearchRequestSchema,
  PropertyTypeEnum,
  ListingTypeEnum,
} from '@/lib/schemas';

describe('PropertyTypeEnum', () => {
  it('accepts valid property types', () => {
    expect(PropertyTypeEnum.parse('apartment')).toBe('apartment');
    expect(PropertyTypeEnum.parse('house')).toBe('house');
    expect(PropertyTypeEnum.parse('studio')).toBe('studio');
    expect(PropertyTypeEnum.parse('loft')).toBe('loft');
    expect(PropertyTypeEnum.parse('townhouse')).toBe('townhouse');
    expect(PropertyTypeEnum.parse('other')).toBe('other');
  });

  it('rejects invalid property type', () => {
    expect(() => PropertyTypeEnum.parse('villa')).toThrow();
  });
});

describe('ListingTypeEnum', () => {
  it('accepts valid listing types', () => {
    expect(ListingTypeEnum.parse('rent')).toBe('rent');
    expect(ListingTypeEnum.parse('sale')).toBe('sale');
    expect(ListingTypeEnum.parse('room')).toBe('room');
    expect(ListingTypeEnum.parse('sublease')).toBe('sublease');
  });

  it('rejects invalid listing type', () => {
    expect(() => ListingTypeEnum.parse('lease')).toThrow();
  });
});

describe('PropertySchema', () => {
  const validProperty = {
    city: 'Berlin',
    property_type: 'apartment',
    listing_type: 'rent',
  };

  it('validates a minimal property', () => {
    const result = PropertySchema.parse(validProperty);
    expect(result.city).toBe('Berlin');
    expect(result.property_type).toBe('apartment');
    expect(result.listing_type).toBe('rent');
  });

  it('validates a full property', () => {
    const result = PropertySchema.parse({
      id: 'p-1',
      city: 'Warsaw',
      property_type: 'house',
      listing_type: 'sale',
      latitude: 52.22,
      longitude: 21.01,
      price: 500000,
      area_sqm: 85,
      bedrooms: 3,
      bathrooms: 2,
      title: 'Nice house',
      description: 'Spacious',
      address: 'ul. Test 1',
      district: 'Mokotow',
      images: ['img1.jpg'],
      url: 'https://example.com',
      source: 'test',
      created_at: '2024-01-01',
      updated_at: '2024-01-02',
    });
    expect(result.id).toBe('p-1');
    expect(result.price).toBe(500000);
  });

  it('rejects missing city', () => {
    expect(() =>
      PropertySchema.parse({ property_type: 'apartment', listing_type: 'rent' })
    ).toThrow();
  });

  it('rejects invalid property_type', () => {
    expect(() => PropertySchema.parse({ ...validProperty, property_type: 'castle' })).toThrow();
  });

  it('allows optional fields to be undefined', () => {
    const result = PropertySchema.parse(validProperty);
    expect(result.id).toBeUndefined();
    expect(result.price).toBeUndefined();
    expect(result.images).toBeUndefined();
  });
});

describe('PropertiesResponseSchema', () => {
  it('validates a valid response', () => {
    const result = PropertiesResponseSchema.parse({
      properties: [{ city: 'Berlin', property_type: 'apartment', listing_type: 'rent' }],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
    expect(result.properties).toHaveLength(1);
    expect(result.total).toBe(1);
  });

  it('rejects missing fields', () => {
    expect(() => PropertiesResponseSchema.parse({ properties: [] })).toThrow();
  });

  it('rejects invalid property in array', () => {
    expect(() =>
      PropertiesResponseSchema.parse({
        properties: [{ invalid: true }],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      })
    ).toThrow();
  });
});

describe('UserSchema', () => {
  it('validates a valid user', () => {
    const result = UserSchema.parse({
      id: 'u-1',
      email: 'test@example.com',
      is_active: true,
      is_verified: false,
      created_at: '2024-01-01',
    });
    expect(result.id).toBe('u-1');
    expect(result.name).toBeUndefined();
  });

  it('validates user with name', () => {
    const result = UserSchema.parse({
      id: 'u-2',
      email: 'a@b.com',
      name: 'Test User',
      is_active: true,
      is_verified: true,
      created_at: '2024-01-01',
    });
    expect(result.name).toBe('Test User');
  });

  it('rejects invalid email', () => {
    expect(() =>
      UserSchema.parse({
        id: 'u-3',
        email: 'not-an-email',
        is_active: true,
        is_verified: false,
        created_at: '2024-01-01',
      })
    ).toThrow();
  });

  it('rejects missing required fields', () => {
    expect(() => UserSchema.parse({ id: 'u-4' })).toThrow();
  });
});

describe('AuthResponseSchema', () => {
  it('validates a valid auth response', () => {
    const result = AuthResponseSchema.parse({
      access_token: 'token-abc',
      token_type: 'bearer',
      expires_in: 3600,
      user: {
        id: 'u-1',
        email: 'test@example.com',
        is_active: true,
        is_verified: true,
        created_at: '2024-01-01',
      },
    });
    expect(result.access_token).toBe('token-abc');
    expect(result.refresh_token).toBeUndefined();
  });

  it('validates auth response with refresh token', () => {
    const result = AuthResponseSchema.parse({
      access_token: 'token-abc',
      refresh_token: 'refresh-xyz',
      token_type: 'bearer',
      expires_in: 3600,
      user: {
        id: 'u-1',
        email: 'test@example.com',
        is_active: true,
        is_verified: true,
        created_at: '2024-01-01',
      },
    });
    expect(result.refresh_token).toBe('refresh-xyz');
  });

  it('rejects wrong token_type', () => {
    expect(() =>
      AuthResponseSchema.parse({
        access_token: 'token',
        token_type: 'basic',
        expires_in: 3600,
        user: {
          id: 'u-1',
          email: 'a@b.com',
          is_active: true,
          is_verified: true,
          created_at: '2024-01-01',
        },
      })
    ).toThrow();
  });
});

describe('LoginRequestSchema', () => {
  it('validates a valid login request', () => {
    const result = LoginRequestSchema.parse({ email: 'test@example.com', password: 'password123' });
    expect(result.email).toBe('test@example.com');
  });

  it('rejects short password', () => {
    expect(() =>
      LoginRequestSchema.parse({ email: 'test@example.com', password: 'short' })
    ).toThrow();
  });

  it('rejects invalid email', () => {
    expect(() =>
      LoginRequestSchema.parse({ email: 'not-email', password: 'password123' })
    ).toThrow();
  });
});

describe('RegisterRequestSchema', () => {
  it('validates a valid register request', () => {
    const result = RegisterRequestSchema.parse({
      email: 'new@example.com',
      password: 'password123',
    });
    expect(result.name).toBeUndefined();
  });

  it('validates register request with name', () => {
    const result = RegisterRequestSchema.parse({
      email: 'new@example.com',
      password: 'password123',
      name: 'New User',
    });
    expect(result.name).toBe('New User');
  });

  it('rejects short password', () => {
    expect(() => RegisterRequestSchema.parse({ email: 'a@b.com', password: '1234567' })).toThrow();
  });
});

describe('ChatMessageSchema', () => {
  it('validates user message', () => {
    const result = ChatMessageSchema.parse({ role: 'user', content: 'Hello' });
    expect(result.role).toBe('user');
    expect(result.timestamp).toBeUndefined();
  });

  it('validates assistant message with timestamp', () => {
    const result = ChatMessageSchema.parse({
      role: 'assistant',
      content: 'Hi there',
      timestamp: '2024-01-01',
    });
    expect(result.timestamp).toBe('2024-01-01');
  });

  it('validates system message', () => {
    expect(ChatMessageSchema.parse({ role: 'system', content: 'You are helpful' }).role).toBe(
      'system'
    );
  });

  it('rejects invalid role', () => {
    expect(() => ChatMessageSchema.parse({ role: 'admin', content: 'test' })).toThrow();
  });
});

describe('ChatRequestSchema', () => {
  it('validates minimal chat request', () => {
    const result = ChatRequestSchema.parse({ message: 'Hello' });
    expect(result.stream).toBe(false);
    expect(result.include_intermediate_steps).toBe(false);
    expect(result.page).toBeUndefined();
  });

  it('validates full chat request', () => {
    const result = ChatRequestSchema.parse({
      message: 'Test',
      session_id: 'sess-1',
      stream: true,
      include_intermediate_steps: true,
    });
    expect(result.session_id).toBe('sess-1');
    expect(result.stream).toBe(true);
  });

  it('rejects empty message', () => {
    expect(() => ChatRequestSchema.parse({ message: '' })).toThrow();
  });
});

describe('ChatResponseSchema', () => {
  it('validates a valid chat response', () => {
    const result = ChatResponseSchema.parse({ response: 'Answer', session_id: 'sess-1' });
    expect(result.sources).toBeUndefined();
  });

  it('validates chat response with sources', () => {
    const result = ChatResponseSchema.parse({
      response: 'Answer',
      session_id: 'sess-1',
      sources: [{ title: 'Doc 1' }],
      intermediate_steps: [{ step: 1 }],
    });
    expect(result.sources).toHaveLength(1);
    expect(result.intermediate_steps).toHaveLength(1);
  });
});

describe('ApiErrorSchema', () => {
  it('validates a minimal error', () => {
    const result = ApiErrorSchema.parse({ detail: 'Not found' });
    expect(result.error_code).toBeUndefined();
    expect(result.request_id).toBeUndefined();
  });

  it('validates a full error', () => {
    const result = ApiErrorSchema.parse({
      detail: 'Unauthorized',
      error_code: 'AUTH_001',
      request_id: 'req-123',
    });
    expect(result.error_code).toBe('AUTH_001');
    expect(result.request_id).toBe('req-123');
  });

  it('rejects missing detail', () => {
    expect(() => ApiErrorSchema.parse({ error_code: 'ERR' })).toThrow();
  });
});

describe('MarketAnomalySchema', () => {
  it('validates a valid anomaly', () => {
    const result = MarketAnomalySchema.parse({
      id: 'a-1',
      property_id: 'p-1',
      anomaly_type: 'price_spike',
      severity: 'high',
      description: 'Price increased 50%',
      detected_at: '2024-01-01',
    });
    expect(result.data).toBeUndefined();
  });

  it('validates anomaly with data', () => {
    const result = MarketAnomalySchema.parse({
      id: 'a-2',
      property_id: 'p-2',
      anomaly_type: 'price_drop',
      severity: 'low',
      description: 'Price dropped',
      detected_at: '2024-01-01',
      data: { old_price: 500000, new_price: 300000 },
    });
    expect(result.data).toBeDefined();
  });

  it('rejects invalid severity', () => {
    expect(() =>
      MarketAnomalySchema.parse({
        id: 'a-3',
        property_id: 'p-3',
        anomaly_type: 'test',
        severity: 'critical',
        description: 'Test',
        detected_at: '2024-01-01',
      })
    ).toThrow();
  });

  it('rejects missing required fields', () => {
    expect(() => MarketAnomalySchema.parse({ id: 'a-4' })).toThrow();
  });
});

describe('SearchFiltersSchema', () => {
  it('validates empty filters', () => {
    const result = SearchFiltersSchema.parse({});
    expect(result.city).toBeUndefined();
  });

  it('validates full filters', () => {
    const result = SearchFiltersSchema.parse({
      city: 'Berlin',
      property_type: 'apartment',
      listing_type: 'rent',
      min_price: 100000,
      max_price: 500000,
      min_area: 30,
      max_area: 100,
      bedrooms: 2,
      bathrooms: 1,
      district: 'Mitte',
    });
    expect(result.city).toBe('Berlin');
    expect(result.bedrooms).toBe(2);
  });

  it('rejects invalid property_type in filter', () => {
    expect(() => SearchFiltersSchema.parse({ property_type: 'castle' })).toThrow();
  });
});

describe('SearchRequestSchema', () => {
  it('provides defaults for page/page_size', () => {
    const result = SearchRequestSchema.parse({});
    expect(result.page).toBe(1);
    expect(result.page_size).toBe(20);
  });

  it('validates full search request', () => {
    const result = SearchRequestSchema.parse({
      query: 'apartments Berlin',
      filters: { city: 'Berlin' },
      page: 2,
      page_size: 10,
      sort_by: 'price',
      sort_order: 'asc',
    });
    expect(result.query).toBe('apartments Berlin');
    expect(result.filters?.city).toBe('Berlin');
    expect(result.sort_order).toBe('asc');
  });

  it('rejects invalid sort_order', () => {
    expect(() => SearchRequestSchema.parse({ sort_order: 'random' })).toThrow();
  });
});
