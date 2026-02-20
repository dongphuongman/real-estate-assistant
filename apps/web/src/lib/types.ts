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
  property_type: 'apartment' | 'house' | 'studio' | 'loft' | 'townhouse' | 'other';
  listing_type: 'rent' | 'sale' | 'room' | 'sublease';
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
  negotiation_rate?: 'high' | 'middle' | 'low';
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
  sort_by?: 'relevance' | 'price' | 'price_per_sqm' | 'area_sqm' | 'year_built';
  sort_order?: 'asc' | 'desc';
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  stream?: boolean;
  include_intermediate_steps?: boolean;
}

export interface ChatResponse {
  response: string;
  sources: Array<{
    content: string;
    metadata: Record<string, unknown>;
  }>;
  sources_truncated?: boolean;
  session_id?: string;
  intermediate_steps?: Array<Record<string, unknown>>;
}

export interface RagUploadResponse {
  message: string;
  chunks_indexed: number;
  errors: string[];
}

export interface RagResetResponse {
  message: string;
  documents_removed: number;
  documents_remaining: number;
}

export interface RagQaRequest {
  question: string;
  top_k?: number;
  provider?: string;
  model?: string;
}

export interface RagQaCitation {
  source: string;
  chunk_index: number;
}

export interface RagQaResponse {
  answer: string;
  citations: RagQaCitation[];
  llm_used: boolean;
  provider: string | null;
  model: string | null;
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

export interface TCOInput {
  property_price: number;
  down_payment_percent?: number;
  interest_rate?: number;
  loan_years?: number;
  monthly_hoa?: number;
  annual_property_tax?: number;
  annual_insurance?: number;
  monthly_utilities?: number;
  monthly_internet?: number;
  monthly_parking?: number;
  maintenance_percent?: number;
}

export interface TCOResult {
  // Mortgage components
  monthly_payment: number;
  total_interest: number;
  down_payment: number;
  loan_amount: number;
  // TCO components (monthly)
  monthly_mortgage: number;
  monthly_property_tax: number;
  monthly_insurance: number;
  monthly_hoa: number;
  monthly_utilities: number;
  monthly_internet: number;
  monthly_parking: number;
  monthly_maintenance: number;
  monthly_tco: number;
  // TCO components (annual)
  annual_mortgage: number;
  annual_property_tax: number;
  annual_insurance: number;
  annual_hoa: number;
  annual_utilities: number;
  annual_internet: number;
  annual_parking: number;
  annual_maintenance: number;
  annual_tco: number;
  // Total over loan term
  total_ownership_cost: number;
  total_all_costs: number;
  breakdown: Record<string, number>;
}

export interface NotificationSettings {
  email_digest: boolean;
  frequency: 'daily' | 'weekly';
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
  runtime_error?: string | null;
}

export interface ModelRuntimeTestResponse {
  provider: string;
  is_local: boolean;
  runtime_available?: boolean | null;
  available_models?: string[] | null;
  runtime_error?: string | null;
}

export interface ModelPreferences {
  preferred_provider: string | null;
  preferred_model: string | null;
}

export type ExportFormat = 'csv' | 'xlsx' | 'json' | 'md' | 'pdf';

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

// Admin API types for data ingestion
export interface IngestRequest {
  file_urls?: string[];
  force?: boolean;
  sheet_name?: string;
  header_row?: number;
  source_name?: string;
}

export interface IngestResponse {
  message: string;
  properties_processed: number;
  errors: string[];
  source_type?: string;
  source_name?: string;
}

export interface ExcelSheetsRequest {
  file_url: string;
}

export interface ExcelSheetsResponse {
  file_url: string;
  sheet_names: string[];
  default_sheet?: string;
  row_count: Record<string, number>;
}

// Portal/API Integration types for TASK-006
export interface PortalAdapterInfo {
  name: string;
  display_name: string;
  configured: boolean;
  has_api_key: boolean;
  rate_limit?: { requests: number; window_seconds: number } | null;
}

export interface PortalAdaptersResponse {
  adapters: PortalAdapterInfo[];
  count: number;
}

export interface PortalFiltersRequest {
  portal: string;
  city?: string;
  min_price?: number;
  max_price?: number;
  min_rooms?: number;
  max_rooms?: number;
  property_type?: string;
  listing_type?: string;
  limit?: number;
  source_name?: string;
}

export interface PortalIngestResponse {
  success: boolean;
  message: string;
  portal: string;
  properties_processed: number;
  source_type: string;
  source_name?: string;
  errors: string[];
  filters_applied?: Record<string, unknown>;
}

// Investment Analysis types for TASK-019
export interface InvestmentAnalysisInput {
  property_price: number;
  monthly_rent: number;
  down_payment_percent?: number;
  closing_costs?: number;
  renovation_costs?: number;
  interest_rate?: number;
  loan_years?: number;
  property_tax_monthly?: number;
  insurance_monthly?: number;
  hoa_monthly?: number;
  maintenance_percent?: number;
  vacancy_rate?: number;
  management_percent?: number;
}

export interface InvestmentAnalysisResult {
  monthly_cash_flow: number;
  annual_cash_flow: number;
  cash_on_cash_roi: number;
  cap_rate: number;
  gross_yield: number;
  net_yield: number;
  total_investment: number;
  monthly_income: number;
  monthly_expenses: number;
  annual_income: number;
  annual_expenses: number;
  monthly_mortgage: number;
  investment_score: number;
  score_breakdown: Record<string, number>;
}

export interface CompareInvestmentsRequest {
  property_ids: string[];
}

export interface ComparedInvestmentProperty {
  property_id?: string;
  price?: number;
  monthly_rent?: number;
  monthly_cash_flow?: number;
  cash_on_cash_roi?: number;
  cap_rate?: number;
  investment_score?: number;
}

export interface CompareInvestmentsResponse {
  properties: ComparedInvestmentProperty[];
  summary: Record<string, unknown>;
}

// Neighborhood Quality Index types for TASK-020
export interface NeighborhoodQualityInput {
  property_id: string;
  latitude?: number;
  longitude?: number;
  city?: string;
  neighborhood?: string;
}

export interface NeighborhoodQualityResult {
  property_id: string;
  overall_score: number;
  safety_score: number;
  schools_score: number;
  amenities_score: number;
  walkability_score: number;
  green_space_score: number;
  score_breakdown: Record<string, number>;
  data_sources: string[];
  latitude?: number;
  longitude?: number;
  city?: string;
  neighborhood?: string;
}

// Saved Search types for Task #36
export type AlertFrequency = 'instant' | 'daily' | 'weekly' | 'none';

export interface SavedSearch {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  filters: Record<string, unknown>;
  alert_frequency: AlertFrequency;
  is_active: boolean;
  notify_on_new: boolean;
  notify_on_price_drop: boolean;
  created_at: string;
  updated_at: string;
  last_used_at?: string;
  use_count: number;
}

export interface SavedSearchCreate {
  name: string;
  description?: string;
  filters: Record<string, unknown>;
  alert_frequency?: AlertFrequency;
  notify_on_new?: boolean;
  notify_on_price_drop?: boolean;
}

export interface SavedSearchUpdate {
  name?: string;
  description?: string;
  filters?: Record<string, unknown>;
  alert_frequency?: AlertFrequency;
  is_active?: boolean;
  notify_on_new?: boolean;
  notify_on_price_drop?: boolean;
}

export interface SavedSearchListResponse {
  items: SavedSearch[];
  total: number;
}

// Collection types for Task #37
export interface Collection {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  favorite_count: number;
}

export interface CollectionCreate {
  name: string;
  description?: string;
}

export interface CollectionUpdate {
  name?: string;
  description?: string;
}

export interface CollectionListResponse {
  items: Collection[];
  total: number;
}

// Favorite types for Task #37
export interface Favorite {
  id: string;
  user_id: string;
  property_id: string;
  collection_id?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface FavoriteWithProperty extends Favorite {
  property?: Property;
  is_available: boolean;
}

export interface FavoriteCreate {
  property_id: string;
  collection_id?: string;
  notes?: string;
}

export interface FavoriteUpdate {
  collection_id?: string;
  notes?: string;
}

export interface FavoriteListResponse {
  items: FavoriteWithProperty[];
  total: number;
  unavailable_count: number;
}

export interface FavoriteCheckResponse {
  is_favorited: boolean;
  favorite_id?: string;
  collection_id?: string;
  notes?: string;
}

// Price History types for Task #38
export interface PriceSnapshot {
  id: string;
  property_id: string;
  price: number;
  price_per_sqm?: number;
  currency?: string;
  source?: string;
  recorded_at: string;
}

export interface PriceHistory {
  property_id: string;
  snapshots: PriceSnapshot[];
  total: number;
  current_price?: number;
  first_recorded?: string;
  last_recorded?: string;
  price_change_percent?: number;
  trend: 'increasing' | 'decreasing' | 'stable' | 'insufficient_data';
}

export interface MarketTrendPoint {
  period: string;
  start_date: string;
  end_date: string;
  average_price: number;
  median_price: number;
  volume: number;
  avg_price_per_sqm?: number;
}

export interface MarketTrends {
  city?: string;
  district?: string;
  interval: 'month' | 'quarter' | 'year';
  data_points: MarketTrendPoint[];
  trend_direction: 'increasing' | 'decreasing' | 'stable' | 'insufficient_data';
  change_percent?: number;
  confidence: 'high' | 'medium' | 'low';
}

export interface MarketIndicators {
  city?: string;
  overall_trend: 'rising' | 'falling' | 'stable';
  avg_price_change_1m?: number;
  avg_price_change_3m?: number;
  avg_price_change_6m?: number;
  avg_price_change_1y?: number;
  total_listings: number;
  new_listings_7d: number;
  price_drops_7d: number;
  hottest_districts: Array<{ name: string; avg_price: number; count: number }>;
  coldest_districts: Array<{ name: string; avg_price: number; count: number }>;
}
