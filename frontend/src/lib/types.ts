export interface Property {
  id?: string;
  title?: string;
  description?: string;
  country?: string;
  region?: string;
  city: string;
  district?: string;
  neighborhood?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  property_type: "apartment" | "house" | "studio" | "loft" | "townhouse" | "other";
  listing_type: "rent" | "sale" | "room" | "sublease";
  rooms?: number;
  bathrooms?: number;
  area_sqm?: number;
  floor?: number;
  total_floors?: number;
  year_built?: number;
  energy_rating?: string;
  price?: number;
  currency?: string;
  price_media?: number;
  price_delta?: number;
  deposit?: number;
  negotiation_rate?: "high" | "middle" | "low";
  has_parking: boolean;
  has_garden: boolean;
  has_pool: boolean;
  has_garage: boolean;
  has_bike_room: boolean;
  amenities?: string[];
  images?: string[];
}

export interface SearchResultItem {
  property: Property;
  score: number;
}

export interface SearchResponse {
  results: SearchResultItem[];
  count: number;
}

export interface SearchRequest {
  query: string;
  limit?: number;
  filters?: Record<string, any>;
  alpha?: number;
  lat?: number;
  lon?: number;
  radius_km?: number;
  sort_by?: "relevance" | "price" | "price_per_sqm" | "area_sqm" | "year_built";
  sort_order?: "asc" | "desc";
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  stream?: boolean;
}

export interface ChatResponse {
  response: string;
  sources: Array<{
    content: string;
    metadata: any;
  }>;
  session_id?: string;
}

export interface MortgageInput {
  property_price: number;
  down_payment_percent?: number;
  interest_rate?: number;
  loan_years?: number;
}

export interface MortgageResult {
  monthly_payment: number;
  total_interest: number;
  total_cost: number;
  down_payment: number;
  loan_amount: number;
  breakdown: Record<string, number>;
}
