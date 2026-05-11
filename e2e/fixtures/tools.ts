/**
 * Tools test fixtures for E2E tests.
 * Provides sample data for mortgage calculator, property comparison, and neighborhood quality.
 */

export interface TestMortgageInput {
  property_price: number;
  down_payment_percent: number;
  interest_rate: number;
  loan_years: number;
}

export interface TestMortgageResult {
  monthly_payment: number;
  total_interest: number;
  total_cost: number;
  down_payment_amount: number;
  loan_amount: number;
}

export interface TestComparisonResult {
  properties: Array<{
    id: string;
    title: string;
    price: number;
    rooms: number;
    area: number;
    city: string;
  }>;
  summary: {
    count: number;
    min_price: number;
    max_price: number;
    price_difference: number;
    avg_price: number;
    avg_area: number;
  };
}

export interface TestNeighborhoodQualityResult {
  property_id: string;
  overall_score: number;
  safety_score: number;
  schools_score: number;
  amenities_score: number;
  walkability_score: number;
  green_space_score: number;
  city: string;
  neighborhood: string;
  latitude: number;
  longitude: number;
  data_sources: string[];
}

/**
 * Sample mortgage calculation input.
 */
export const TEST_MORTGAGE_INPUT: TestMortgageInput = {
  property_price: 450000,
  down_payment_percent: 20,
  interest_rate: 6.5,
  loan_years: 30,
};

/**
 * Sample mortgage calculation result matching the API response.
 */
export const TEST_MORTGAGE_RESULT: TestMortgageResult = {
  monthly_payment: 2275.53,
  total_interest: 543190.80,
  total_cost: 903190.80,
  down_payment_amount: 90000,
  loan_amount: 360000,
};

/**
 * Sample property comparison result.
 */
export const TEST_COMPARISON_RESULT: TestComparisonResult = {
  properties: [
    { id: 'prop-001', title: 'Modern 2-Bedroom Apartment in Mitte', price: 1200, rooms: 2, area: 75, city: 'Berlin' },
    { id: 'prop-002', title: 'Spacious 3-Bedroom Flat in Prenzlauer Berg', price: 1500, rooms: 3, area: 95, city: 'Berlin' },
  ],
  summary: {
    count: 2,
    min_price: 1200,
    max_price: 1500,
    price_difference: 300,
    avg_price: 1350,
    avg_area: 85,
  },
};

/**
 * Sample neighborhood quality result.
 */
export const TEST_NEIGHBORHOOD_QUALITY: TestNeighborhoodQualityResult = {
  property_id: 'prop-001',
  overall_score: 78.5,
  safety_score: 82,
  schools_score: 75,
  amenities_score: 85,
  walkability_score: 72,
  green_space_score: 68,
  city: 'Berlin',
  neighborhood: 'Mitte',
  latitude: 52.52,
  longitude: 13.405,
  data_sources: ['osm', 'government', 'user_reports'],
};

/**
 * Build a mortgage result for custom inputs.
 */
export function buildMortgageResult(input: TestMortgageInput): TestMortgageResult {
  const downPaymentAmount = input.property_price * (input.down_payment_percent / 100);
  const loanAmount = input.property_price - downPaymentAmount;
  const monthlyRate = input.interest_rate / 100 / 12;
  const totalPayments = input.loan_years * 12;

  let monthlyPayment: number;
  if (monthlyRate === 0) {
    monthlyPayment = loanAmount / totalPayments;
  } else {
    monthlyPayment =
      (loanAmount * (monthlyRate * Math.pow(1 + monthlyRate, totalPayments))) /
      (Math.pow(1 + monthlyRate, totalPayments) - 1);
  }

  const totalCost = monthlyPayment * totalPayments;
  const totalInterest = totalCost - loanAmount;

  return {
    monthly_payment: Math.round(monthlyPayment * 100) / 100,
    total_interest: Math.round(totalInterest * 100) / 100,
    total_cost: Math.round(totalCost * 100) / 100,
    down_payment_amount: Math.round(downPaymentAmount * 100) / 100,
    loan_amount: Math.round(loanAmount * 100) / 100,
  };
}
