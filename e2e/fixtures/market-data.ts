/**
 * Market data test fixtures for E2E tests.
 * Provides sample market indicators, trends, and time series data.
 */

export interface TestMarketTrendPoint {
  period: string;
  start_date: string;
  end_date: string;
  average_price: number;
  median_price: number;
  volume: number;
  avg_price_per_sqm?: number;
}

export interface TestMarketIndicators {
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

export interface TestMarketTrends {
  city?: string;
  district?: string;
  interval: 'month' | 'quarter' | 'year';
  data_points: TestMarketTrendPoint[];
  trend_direction: 'increasing' | 'decreasing' | 'stable' | 'insufficient_data';
  change_percent?: number;
  confidence: 'high' | 'medium' | 'low';
}

/**
 * Sample market indicators for default view.
 */
export const TEST_MARKET_INDICATORS: TestMarketIndicators = {
  overall_trend: 'rising',
  avg_price_change_1m: 1.2,
  avg_price_change_3m: 3.5,
  avg_price_change_6m: 5.8,
  avg_price_change_1y: 8.1,
  total_listings: 1250,
  new_listings_7d: 42,
  price_drops_7d: 18,
  hottest_districts: [
    { name: 'Mitte', avg_price: 5200, count: 85 },
    { name: 'Prenzlauer Berg', avg_price: 4800, count: 72 },
    { name: 'Charlottenburg', avg_price: 4600, count: 68 },
  ],
  coldest_districts: [
    { name: 'Marzahn', avg_price: 2100, count: 30 },
    { name: 'Spandau', avg_price: 2300, count: 45 },
    { name: 'Neukoelln', avg_price: 2800, count: 55 },
  ],
};

/**
 * Sample market indicators filtered by city.
 */
export const TEST_MARKET_INDICATORS_KRAKOW: TestMarketIndicators = {
  city: 'Krakow',
  overall_trend: 'stable',
  avg_price_change_1m: 0.3,
  avg_price_change_3m: 1.1,
  total_listings: 620,
  new_listings_7d: 15,
  price_drops_7d: 8,
  hottest_districts: [
    { name: 'Stare Miasto', avg_price: 12500, count: 22 },
    { name: 'Kazimierz', avg_price: 11000, count: 18 },
  ],
  coldest_districts: [
    { name: 'Nowa Huta', avg_price: 5800, count: 35 },
    { name: 'Bierznow', avg_price: 6500, count: 28 },
  ],
};

/**
 * Sample market trends time series (monthly data).
 */
export const TEST_MARKET_TRENDS: TestMarketTrends = {
  interval: 'month',
  data_points: [
    { period: '2025-07', start_date: '2025-07-01', end_date: '2025-07-31', average_price: 420000, median_price: 395000, volume: 120, avg_price_per_sqm: 5200 },
    { period: '2025-08', start_date: '2025-08-01', end_date: '2025-08-31', average_price: 425000, median_price: 400000, volume: 115, avg_price_per_sqm: 5300 },
    { period: '2025-09', start_date: '2025-09-01', end_date: '2025-09-30', average_price: 432000, median_price: 408000, volume: 130, avg_price_per_sqm: 5350 },
    { period: '2025-10', start_date: '2025-10-01', end_date: '2025-10-31', average_price: 438000, median_price: 412000, volume: 125, avg_price_per_sqm: 5400 },
    { period: '2025-11', start_date: '2025-11-01', end_date: '2025-11-30', average_price: 445000, median_price: 420000, volume: 118, avg_price_per_sqm: 5480 },
    { period: '2025-12', start_date: '2025-12-01', end_date: '2025-12-31', average_price: 450000, median_price: 425000, volume: 110, avg_price_per_sqm: 5500 },
  ],
  trend_direction: 'increasing',
  change_percent: 7.1,
  confidence: 'high',
};

/**
 * Sample market trends filtered by city (Krakow).
 */
export const TEST_MARKET_TRENDS_KRAKOW: TestMarketTrends = {
  city: 'Krakow',
  interval: 'month',
  data_points: [
    { period: '2025-07', start_date: '2025-07-01', end_date: '2025-07-31', average_price: 580000, median_price: 550000, volume: 65, avg_price_per_sqm: 9200 },
    { period: '2025-08', start_date: '2025-08-01', end_date: '2025-08-31', average_price: 582000, median_price: 552000, volume: 60, avg_price_per_sqm: 9250 },
    { period: '2025-09', start_date: '2025-09-01', end_date: '2025-09-30', average_price: 585000, median_price: 555000, volume: 70, avg_price_per_sqm: 9280 },
    { period: '2025-10', start_date: '2025-10-01', end_date: '2025-10-31', average_price: 583000, median_price: 553000, volume: 68, avg_price_per_sqm: 9260 },
    { period: '2025-11', start_date: '2025-11-01', end_date: '2025-11-30', average_price: 586000, median_price: 556000, volume: 62, avg_price_per_sqm: 9300 },
    { period: '2025-12', start_date: '2025-12-01', end_date: '2025-12-31', average_price: 588000, median_price: 558000, volume: 58, avg_price_per_sqm: 9320 },
  ],
  trend_direction: 'stable',
  change_percent: 1.4,
  confidence: 'medium',
};

/**
 * Quarterly aggregate trends.
 */
export const TEST_MARKET_TRENDS_QUARTERLY: TestMarketTrends = {
  interval: 'quarter',
  data_points: [
    { period: 'Q3 2025', start_date: '2025-07-01', end_date: '2025-09-30', average_price: 425667, median_price: 401000, volume: 365 },
    { period: 'Q4 2025', start_date: '2025-10-01', end_date: '2025-12-31', average_price: 444333, median_price: 419000, volume: 353 },
  ],
  trend_direction: 'increasing',
  change_percent: 4.4,
  confidence: 'medium',
};
