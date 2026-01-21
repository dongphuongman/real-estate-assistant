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
  filters?: Record<string, unknown>;
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
    metadata: Record<string, unknown>;
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

export interface NotificationSettings {
  email_digest: boolean;
  frequency: "daily" | "weekly";
  expert_mode: boolean;
  marketing_emails: boolean;
}

export interface ModelPricing {
  input_price_per_1m: number;
  output_price_per_1m: number;
  currency: string;
}

export interface ModelCatalogItem {
  id: string;
  display_name: string;
  provider_name: string;
  context_window: number;
  pricing: ModelPricing | null;
  capabilities: string[];
  description: string | null;
  recommended_for: string[];
}

export interface ModelProviderCatalog {
  name: string;
  display_name: string;
  is_local: boolean;
  requires_api_key: boolean;
  models: ModelCatalogItem[];
  runtime_available?: boolean | null;
  available_models?: string[] | null;
}

export interface ModelPreferences {
  preferred_provider: string | null;
  preferred_model: string | null;
}

export type ExportFormat = "csv" | "xlsx" | "json" | "md" | "pdf";

export interface ExportPropertiesRequest {
  format: ExportFormat;
  property_ids?: string[];
  search?: SearchRequest;
  columns?: string[];
  include_header?: boolean;
  csv_delimiter?: string;
  csv_decimal?: string;
  include_summary?: boolean;
  include_statistics?: boolean;
  include_metadata?: boolean;
  pretty?: boolean;
  max_properties?: number | null;
}

export interface ExportSearchRequest {
  format: ExportFormat;
  search: SearchRequest;
}

export interface PromptTemplateVariableInfo {
  name: string;
  description: string;
  required: boolean;
  example?: string | null;
}

export interface PromptTemplateInfo {
  id: string;
  title: string;
  category: string;
  description: string;
  template_text: string;
  variables: PromptTemplateVariableInfo[];
}

export interface PromptTemplateApplyResponse {
  template_id: string;
  rendered_text: string;
}
