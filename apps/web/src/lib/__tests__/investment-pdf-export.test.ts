/**
 * Tests for Investment PDF Export Utility
 */

import { exportInvestmentToPDF } from '../investment-pdf-export';
import type { AdvancedInvestmentResult } from '../types';

// Mock jsPDF
jest.mock('jspdf', () => {
  const mockDoc = {
    setFontSize: jest.fn(),
    setFont: jest.fn(),
    setTextColor: jest.fn(),
    setDrawColor: jest.fn(),
    line: jest.fn(),
    text: jest.fn(),
    addPage: jest.fn(),
    setPage: jest.fn(),
    getNumberOfPages: jest.fn(() => 1),
    internal: {
      pageSize: {
        getWidth: jest.fn(() => 210),
        getHeight: jest.fn(() => 297),
      },
    },
    splitTextToSize: jest.fn((text: string) => [text]),
    save: jest.fn(),
  };

  return jest.fn(() => mockDoc);
});

// Mock window.URL.createObjectURL / revokeObjectURL
global.URL.createObjectURL = jest.fn(() => 'blob:test');
global.URL.revokeObjectURL = jest.fn();

describe('exportInvestmentToPDF', () => {
  const mockResult: AdvancedInvestmentResult = {
    // Basic metrics
    monthly_cash_flow: 250.5,
    annual_cash_flow: 3006,
    cash_on_cash_roi: 8.55,
    cap_rate: 7.2,
    gross_yield: 12.0,
    net_yield: 6.01,
    total_investment: 35000,
    monthly_income: 1800,
    monthly_expenses: 1549.5,
    annual_income: 21600,
    annual_expenses: 18594,
    monthly_mortgage: 1079.5,
    investment_score: 75,
    score_breakdown: { cash_flow: 80, roi: 70, risk: 75 },

    // Advanced metrics
    risk_score: 72,
    total_projected_cash_flow: 35000,
    final_equity: 285000,
    irr: 12.5,
    annual_depreciation: 5236,
    tax_benefit: 1257,
    total_tax_deductions: 15000,

    // Lists
    risk_factors: ['High vacancy rate in area', 'Older property may need repairs'],
    recommendations: ['Consider property management', 'Set aside reserve fund'],

    // Projections
    cash_flow_projection: [
      { year: 1, cash_flow: 3006, cumulative_cash_flow: 3006, equity: 50000, noi: 12000, gross_income: 21600, operating_expenses: 9600, mortgage_payment: 12954, property_value: 206000, loan_balance: 156000 },
      { year: 2, cash_flow: 3150, cumulative_cash_flow: 6156, equity: 56000, noi: 12480, gross_income: 22032, operating_expenses: 9552, mortgage_payment: 12954, property_value: 212180, loan_balance: 154000 },
    ],
    appreciation_scenarios: [
      { name: 'pessimistic', annual_rate: 1, projected_values: { 1: 202000, 2: 204020 }, total_appreciation_percent: 2, total_appreciation_amount: 4000 },
      { name: 'realistic', annual_rate: 3, projected_values: { 1: 206000, 2: 212180 }, total_appreciation_percent: 6, total_appreciation_amount: 12180 },
      { name: 'optimistic', annual_rate: 5, projected_values: { 1: 210000, 2: 220500 }, total_appreciation_percent: 10, total_appreciation_amount: 20500 },
    ],
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should create and save a PDF document', async () => {
    await exportInvestmentToPDF(mockResult);

    // jsPDF should have been called
    expect(jest.requireMock('jspdf')).toHaveBeenCalled();
  });

  it('should use custom filename when provided', async () => {
    const customFilename = 'my-investment-report';
    await exportInvestmentToPDF(mockResult, { filename: customFilename });

    // The save function should be called with the custom filename
    const jsPDF = jest.requireMock('jspdf');
    const doc = new jsPDF();
    expect(doc.save).toHaveBeenCalledWith(expect.stringContaining(customFilename));
  });

  it('should include date in filename by default', async () => {
    await exportInvestmentToPDF(mockResult, { includeDate: true });

    const jsPDF = jest.requireMock('jspdf');
    const doc = new jsPDF();
    const saveCall = doc.save.mock.calls[0][0];
    // Should contain date pattern YYYY-MM-DD
    expect(saveCall).toMatch(/\d{4}-\d{2}-\d{2}/);
  });

  it('should not include date in filename when includeDate is false', async () => {
    await exportInvestmentToPDF(mockResult, { includeDate: false, filename: 'test' });

    const jsPDF = jest.requireMock('jspdf');
    const doc = new jsPDF();
    const saveCall = doc.save.mock.calls[0][0];
    // Should just be 'test.pdf' without date
    expect(saveCall).toBe('test.pdf');
  });

  it('should use custom title when provided', async () => {
    const customTitle = 'My Custom Report Title';
    await exportInvestmentToPDF(mockResult, { title: customTitle });

    const jsPDF = jest.requireMock('jspdf');
    const doc = new jsPDF();
    // Title should be set
    expect(doc.text).toHaveBeenCalledWith(customTitle, expect.any(Number), expect.any(Number));
  });

  it('should handle result with missing optional fields', async () => {
    const minimalResult: AdvancedInvestmentResult = {
      ...mockResult,
      risk_factors: [],
      recommendations: [],
      cash_flow_projection: [],
      appreciation_scenarios: [],
      score_breakdown: {},
    };

    await expect(exportInvestmentToPDF(minimalResult)).resolves.not.toThrow();
  });

  it('should handle negative cash flow values', async () => {
    const negativeResult: AdvancedInvestmentResult = {
      ...mockResult,
      monthly_cash_flow: -500,
      annual_cash_flow: -6000,
      cash_on_cash_roi: -15,
      net_yield: -3,
      irr: -5,
      total_projected_cash_flow: -60000,
    };

    await expect(exportInvestmentToPDF(negativeResult)).resolves.not.toThrow();
  });

  it('should handle zero values', async () => {
    const zeroResult: AdvancedInvestmentResult = {
      ...mockResult,
      monthly_cash_flow: 0,
      annual_cash_flow: 0,
      cash_on_cash_roi: 0,
      cap_rate: 0,
      gross_yield: 0,
      net_yield: 0,
      investment_score: 0,
      risk_score: 0,
    };

    await expect(exportInvestmentToPDF(zeroResult)).resolves.not.toThrow();
  });

  it('should handle null IRR', async () => {
    const nullIrrResult: AdvancedInvestmentResult = {
      ...mockResult,
      irr: null,
    };

    await expect(exportInvestmentToPDF(nullIrrResult)).resolves.not.toThrow();
  });
});
