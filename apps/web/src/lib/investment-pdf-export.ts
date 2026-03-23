/**
 * PDF Export Utility for Investment Analysis Results
 *
 * Uses jsPDF to generate PDF exports of investment analysis
 */

import jsPDF from 'jspdf';
import type { AdvancedInvestmentResult } from './types';

interface InvestmentPDFOptions {
  title?: string;
  filename?: string;
  includeDate?: boolean;
}

/**
 * Format currency for PDF display
 */
function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format percentage for PDF display
 */
function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`;
}

/**
 * Generate a PDF from investment analysis result data
 */
export async function exportInvestmentToPDF(
  result: AdvancedInvestmentResult,
  options: InvestmentPDFOptions = {}
): Promise<void> {
  const {
    title = 'Investment Analysis Report',
    filename = 'investment-analysis',
    includeDate = true,
  } = options;

  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 20;
  let y = 20;

  // Title
  doc.setFontSize(18);
  doc.setFont('helvetica', 'bold');
  doc.text(title, margin, y);
  y += 10;

  // Date
  if (includeDate) {
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100);
    doc.text(`Generated: ${new Date().toLocaleDateString()}`, margin, y);
    y += 15;
  }

  doc.setTextColor(0);

  // Key Metrics Section
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text('Key Metrics', margin, y);
  y += 8;

  // Draw separator line
  doc.setDrawColor(200);
  doc.line(margin, y - 2, pageWidth - margin, y - 2);

  // Metrics data in two columns
  const metrics = [
    ['Monthly Cash Flow', formatCurrency(result.monthly_cash_flow)],
    ['Annual Cash Flow', formatCurrency(result.annual_cash_flow)],
    ['Cash-on-Cash ROI', formatPercent(result.cash_on_cash_roi)],
    ['Cap Rate', formatPercent(result.cap_rate)],
    ['Gross Yield', formatPercent(result.gross_yield)],
    ['Net Yield', formatPercent(result.net_yield)],
    ['Total Investment', formatCurrency(result.total_investment)],
    ['Investment Score', `${result.investment_score.toFixed(0)}/100`],
  ];

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');

  const leftColX = margin;
  const rightColX = margin + 80;
  let leftY = y;
  let rightY = y;

  metrics.forEach((metric, index) => {
    const [label, value] = metric;
    if (index < metrics.length / 2) {
      doc.setFont('helvetica', 'bold');
      doc.text(label + ':', leftColX, leftY);
      doc.setFont('helvetica', 'normal');
      doc.text(value, leftColX + 45, leftY);
      leftY += 6;
    } else {
      doc.setFont('helvetica', 'bold');
      doc.text(label + ':', rightColX, rightY);
      doc.setFont('helvetica', 'normal');
      doc.text(value, rightColX + 45, rightY);
      rightY += 6;
    }
  });

  y = Math.max(leftY, rightY) + 10;

  // Income and Expenses Section
  if (y > pageHeight - 60) {
    doc.addPage();
    y = 20;
  }

  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text('Income & Expenses', margin, y);
  y += 8;

  doc.line(margin, y - 2, pageWidth - margin, y - 2);
  y += 5;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');

  const incomeExpenses = [
    ['Monthly Income', formatCurrency(result.monthly_income)],
    ['Monthly Expenses', formatCurrency(result.monthly_expenses)],
    ['Annual Income', formatCurrency(result.annual_income)],
    ['Annual Expenses', formatCurrency(result.annual_expenses)],
    ['Monthly Mortgage', formatCurrency(result.monthly_mortgage)],
  ];

  incomeExpenses.forEach(([label, value]) => {
    doc.setFont('helvetica', 'bold');
    doc.text(label + ':', margin, y);
    doc.setFont('helvetica', 'normal');
    doc.text(value, margin + 60, y);
    y += 6;
  });

  // Investment Score Breakdown
  if (result.score_breakdown && Object.keys(result.score_breakdown).length > 0) {
    y += 8;

    if (y > pageHeight - 50) {
      doc.addPage();
      y = 20;
    }

    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text('Score Breakdown', margin, y);
    y += 8;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');

    Object.entries(result.score_breakdown).forEach(([key, value]) => {
      const label = key
        .split('_')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
      doc.text(`${label}:`, margin + 5, y);
      doc.text(`${value.toFixed(1)}`, margin + 60, y);
      y += 5;
    });
  }

  // Advanced Metrics
  y += 10;

  if (y > pageHeight - 50) {
    doc.addPage();
    y = 20;
  }

  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.text('Advanced Metrics', margin, y);
  y += 8;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');

  const advancedMetrics = [
    ['Risk Score', `${result.risk_score}/100`],
    ['Total Projected Cash Flow', formatCurrency(result.total_projected_cash_flow)],
    ['Final Equity', formatCurrency(result.final_equity)],
    ['IRR', result.irr !== null ? formatPercent(result.irr) : 'N/A'],
    ['Annual Depreciation', formatCurrency(result.annual_depreciation)],
    ['Tax Benefit', formatCurrency(result.tax_benefit)],
  ];

  advancedMetrics.forEach(([label, value]) => {
    doc.setFont('helvetica', 'bold');
    doc.text(label + ':', margin, y);
    doc.setFont('helvetica', 'normal');
    doc.text(value, margin + 60, y);
    y += 6;
  });

  // Risk Factors
  if (result.risk_factors && result.risk_factors.length > 0) {
    y += 8;

    if (y > pageHeight - 40) {
      doc.addPage();
      y = 20;
    }

    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text('Risk Factors', margin, y);
    y += 8;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');

    result.risk_factors.forEach((factor) => {
      const lines = doc.splitTextToSize(`\u2022 ${factor}`, pageWidth - 2 * margin - 5);
      lines.forEach((line: string) => {
        doc.text(line, margin + 5, y);
        y += 5;
      });
    });
  }

  // Recommendations
  if (result.recommendations && result.recommendations.length > 0) {
    y += 8;

    if (y > pageHeight - 40) {
      doc.addPage();
      y = 20;
    }

    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text('Recommendations', margin, y);
    y += 8;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');

    result.recommendations.forEach((rec) => {
      const lines = doc.splitTextToSize(`\u2022 ${rec}`, pageWidth - 2 * margin - 5);
      lines.forEach((line: string) => {
        doc.text(line, margin + 5, y);
        y += 5;
      });
    });
  }

  // Cash Flow Projection Summary
  if (result.cash_flow_projection && result.cash_flow_projection.length > 0) {
    y += 10;

    if (y > pageHeight - 50) {
      doc.addPage();
      y = 20;
    }

    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text('Cash Flow Projection Summary', margin, y);
    y += 8;

    // Table header
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.text('Year', margin, y);
    doc.text('Cash Flow', margin + 25, y);
    doc.text('Cumulative', margin + 60, y);
    doc.text('Equity', margin + 95, y);
    doc.line(margin, y + 2, pageWidth - margin, y + 2);
    y += 6;

    // Show first 5 years and last year
    const projectionsToShow = [
      ...result.cash_flow_projection.slice(0, 5),
      result.cash_flow_projection[result.cash_flow_projection.length - 1],
    ];

    doc.setFont('helvetica', 'normal');
    projectionsToShow.forEach((proj) => {
      if (y > pageHeight - 20) {
        doc.addPage();
        y = 20;
        doc.setFont('helvetica', 'bold');
        doc.text('Year', margin, y);
        doc.text('Cash Flow', margin + 25, y);
        doc.text('Cumulative', margin + 60, y);
        doc.text('Equity', margin + 95, y);
        doc.line(margin, y + 2, pageWidth - margin, y + 2);
        y += 6;
        doc.setFont('helvetica', 'normal');
      }
      doc.text(`${proj.year}`, margin, y);
      doc.text(formatCurrency(proj.cash_flow), margin + 25, y);
      doc.text(formatCurrency(proj.cumulative_cash_flow), margin + 60, y);
      doc.text(formatCurrency(proj.equity), margin + 95, y);
      y += 5;
    });
  }

  // Footer
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(150);
    doc.text(
      `Page ${i} of ${pageCount}`,
      pageWidth / 2,
      pageHeight - 10,
      { align: 'center' }
    );
    doc.text(
      'AI Real Estate Assistant - Investment Analysis',
      pageWidth / 2,
      pageHeight - 6,
      { align: 'center' }
    );
  }

  // Save the PDF
  const dateSuffix = includeDate ? `-${new Date().toISOString().split('T')[0]}` : '';
  doc.save(`${filename}${dateSuffix}.pdf`);
}
