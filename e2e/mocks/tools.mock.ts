/**
 * Tools API mock handlers for E2E tests.
 * Provides mock responses for mortgage calculator, property comparison, and neighborhood quality.
 */

import { Route } from '@playwright/test';
import {
  TEST_MORTGAGE_RESULT,
  TEST_COMPARISON_RESULT,
  TEST_NEIGHBORHOOD_QUALITY,
  buildMortgageResult,
} from '../fixtures/tools';

/**
 * Mock POST /api/v1/tools/mortgage-calculator.
 * Parses the request body to return a realistic calculation.
 */
export async function mockMortgageCalculator(route: Route): Promise<void> {
  const body = await route.request().postDataJSON();

  const result = buildMortgageResult({
    property_price: body?.property_price ?? 450000,
    down_payment_percent: body?.down_payment_percent ?? 20,
    interest_rate: body?.interest_rate ?? 6.5,
    loan_years: body?.loan_years ?? 30,
  });

  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(result),
  });
}

/**
 * Mock POST /api/v1/tools/mortgage-calculator returning the default fixture (no parsing).
 */
export async function mockMortgageCalculatorDefault(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(TEST_MORTGAGE_RESULT),
  });
}

/**
 * Mock POST /api/v1/tools/mortgage-calculator returning validation error.
 */
export async function mockMortgageCalculatorValidationError(route: Route): Promise<void> {
  await route.fulfill({
    status: 422,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({
      detail: [
        {
          loc: ['body', 'property_price'],
          msg: 'ensure this value is greater than 0',
          type: 'value_error.number.not_gt',
        },
      ],
    }),
  });
}

/**
 * Mock POST /api/v1/tools/mortgage-calculator returning server error.
 */
export async function mockMortgageCalculatorError(route: Route): Promise<void> {
  await route.fulfill({
    status: 500,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({ detail: 'Mortgage calculation failed' }),
  });
}

/**
 * Mock POST /api/v1/tools/compare-properties.
 */
export async function mockCompareProperties(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(TEST_COMPARISON_RESULT),
  });
}

/**
 * Mock POST /api/v1/tools/compare-properties returning error.
 */
export async function mockComparePropertiesError(route: Route): Promise<void> {
  await route.fulfill({
    status: 500,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({ detail: 'Property comparison failed' }),
  });
}

/**
 * Mock POST /api/v1/tools/neighborhood-quality.
 */
export async function mockNeighborhoodQuality(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(TEST_NEIGHBORHOOD_QUALITY),
  });
}

/**
 * Mock POST /api/v1/tools/neighborhood-quality returning error.
 */
export async function mockNeighborhoodQualityError(route: Route): Promise<void> {
  await route.fulfill({
    status: 500,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({ detail: 'Neighborhood quality analysis failed' }),
  });
}
