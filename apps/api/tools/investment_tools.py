"""
Investment property analysis tools.

Provides standard and advanced investment calculators with ROI,
cap rate, cash flow projections, tax implications, and risk assessment.
"""

from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from tools.mortgage_tools import MortgageCalculatorTool


class InvestmentAnalysisInput(BaseModel):
    """Input for investment property analysis."""

    # Property basics
    property_price: float = Field(description="Purchase price of the property", gt=0)
    monthly_rent: float = Field(description="Expected monthly rental income", gt=0)

    # Purchase costs
    down_payment_percent: float = Field(
        default=20.0, description="Down payment as percentage (e.g., 20 for 20%)", ge=0, le=100
    )
    closing_costs: float = Field(default=0.0, description="Closing costs (one-time)", ge=0)
    renovation_costs: float = Field(
        default=0.0, description="Renovation/buy-and-hold costs (one-time)", ge=0
    )

    # Financing
    interest_rate: float = Field(
        default=4.5, description="Annual interest rate as percentage (e.g., 4.5 for 4.5%)", ge=0
    )
    loan_years: int = Field(default=30, description="Loan term in years", gt=0, le=50)

    # Operating expenses (monthly)
    property_tax_monthly: float = Field(default=0.0, description="Monthly property tax", ge=0)
    insurance_monthly: float = Field(default=0.0, description="Monthly home insurance", ge=0)
    hoa_monthly: float = Field(default=0.0, description="Monthly HOA/condo fees", ge=0)
    maintenance_percent: float = Field(
        default=1.0, description="Annual maintenance as % of property value", ge=0
    )
    vacancy_rate: float = Field(default=5.0, description="Vacancy rate percentage", ge=0, le=100)
    management_percent: float = Field(
        default=0.0, description="Property management fee % of rent", ge=0
    )


class InvestmentAnalysisResult(BaseModel):
    """Result from investment property analysis."""

    # Key metrics
    monthly_cash_flow: float
    annual_cash_flow: float
    cash_on_cash_roi: float
    cap_rate: float
    gross_yield: float
    net_yield: float
    total_investment: float

    # Breakdowns
    monthly_income: float
    monthly_expenses: float
    annual_income: float
    annual_expenses: float
    monthly_mortgage: float

    # Investment scoring
    investment_score: float
    score_breakdown: Dict[str, float]


class InvestmentCalculatorTool(BaseTool):
    """Tool for calculating investment property metrics."""

    name: str = "investment_analyzer"
    description: str = (
        "Calculate investment property metrics including ROI, cap rate, "
        "cash flow, and rental yield. "
        "Input includes property price, monthly rent, financing details, and operating expenses. "
        "Returns comprehensive investment analysis with scoring."
    )
    args_schema: type[InvestmentAnalysisInput] = InvestmentAnalysisInput

    @staticmethod
    def calculate(
        property_price: float,
        monthly_rent: float,
        down_payment_percent: float = 20.0,
        closing_costs: float = 0.0,
        renovation_costs: float = 0.0,
        interest_rate: float = 4.5,
        loan_years: int = 30,
        property_tax_monthly: float = 0.0,
        insurance_monthly: float = 0.0,
        hoa_monthly: float = 0.0,
        maintenance_percent: float = 1.0,
        vacancy_rate: float = 5.0,
        management_percent: float = 0.0,
    ) -> InvestmentAnalysisResult:
        """
        Calculate comprehensive investment property metrics.

        Returns InvestmentAnalysisResult with ROI, cap rate, cash flow, yield, and investment score.
        """
        # Calculate mortgage using existing calculator
        mortgage_result = MortgageCalculatorTool.calculate(
            property_price=property_price,
            down_payment_percent=down_payment_percent,
            interest_rate=interest_rate,
            loan_years=loan_years,
        )

        # Total cash invested (down payment + closing costs + renovation)
        total_investment = mortgage_result.down_payment + closing_costs + renovation_costs

        # Monthly operating expenses
        monthly_maintenance = (property_price * maintenance_percent / 100) / 12
        monthly_vacancy = monthly_rent * (vacancy_rate / 100)
        monthly_management = monthly_rent * (management_percent / 100)

        monthly_operating_expenses = (
            property_tax_monthly
            + insurance_monthly
            + hoa_monthly
            + monthly_maintenance
            + monthly_vacancy
            + monthly_management
        )

        # Monthly and annual income/expense calculations
        monthly_income = monthly_rent
        monthly_expenses = mortgage_result.monthly_payment + monthly_operating_expenses
        monthly_cash_flow = monthly_income - monthly_expenses

        annual_income = monthly_rent * 12
        annual_operating_expenses = monthly_operating_expenses * 12
        annual_mortgage_payment = mortgage_result.monthly_payment * 12
        annual_cash_flow = monthly_cash_flow * 12

        # NOI (Net Operating Income) = Annual Rent - Annual Operating Expenses (excluding mortgage)
        noi = annual_income - annual_operating_expenses

        # Cap Rate = NOI / Purchase Price
        cap_rate = (noi / property_price) * 100 if property_price > 0 else 0

        # Cash on Cash ROI = Annual Cash Flow / Total Cash Invested
        cash_on_cash_roi = (
            (annual_cash_flow / total_investment) * 100 if total_investment > 0 else 0
        )

        # Gross Yield = Annual Rent / Property Price
        gross_yield = (annual_income / property_price) * 100 if property_price > 0 else 0

        # Net Yield = Annual Cash Flow / Property Price
        net_yield = (annual_cash_flow / property_price) * 100 if property_price > 0 else 0

        # Investment Score (0-100)
        score_breakdown = InvestmentCalculatorTool._calculate_score_breakdown(
            cash_on_cash_roi=cash_on_cash_roi,
            cap_rate=cap_rate,
            net_yield=net_yield,
            monthly_cash_flow=monthly_cash_flow,
            property_price=property_price,
        )
        investment_score = sum(score_breakdown.values())

        return InvestmentAnalysisResult(
            # Key metrics
            monthly_cash_flow=round(monthly_cash_flow, 2),
            annual_cash_flow=round(annual_cash_flow, 2),
            cash_on_cash_roi=round(cash_on_cash_roi, 2),
            cap_rate=round(cap_rate, 2),
            gross_yield=round(gross_yield, 2),
            net_yield=round(net_yield, 2),
            total_investment=round(total_investment, 2),
            # Breakdowns
            monthly_income=round(monthly_income, 2),
            monthly_expenses=round(monthly_expenses, 2),
            annual_income=round(annual_income, 2),
            annual_expenses=round(annual_operating_expenses + annual_mortgage_payment, 2),
            monthly_mortgage=round(mortgage_result.monthly_payment, 2),
            # Investment scoring
            investment_score=round(investment_score, 1),
            score_breakdown={k: round(v, 1) for k, v in score_breakdown.items()},
        )

    @staticmethod
    def _calculate_score_breakdown(
        cash_on_cash_roi: float,
        cap_rate: float,
        net_yield: float,
        monthly_cash_flow: float,
        property_price: float,
    ) -> Dict[str, float]:
        """
        Calculate investment score breakdown (total = 100).

        Scoring components:
        - Yield score (0-30): Based on cash-on-cash ROI
        - Cap rate score (0-25): Based on capitalization rate
        - Cash flow margin (0-20): Positive cash flow ratio
        - Net yield score (0-15): Based on net yield percentage
        - Risk factor (0-10): Lower risk for positive cash flow
        """
        score: Dict[str, float] = {}

        # Yield score (0-30): Cash on Cash ROI
        # >15% = 30, 10-15% = 20-30, 5-10% = 10-20, 0-5% = 0-10, negative = 0
        if cash_on_cash_roi >= 15:
            score["yield_score"] = 30.0
        elif cash_on_cash_roi >= 10:
            score["yield_score"] = 20.0 + (cash_on_cash_roi - 10) * 2
        elif cash_on_cash_roi >= 5:
            score["yield_score"] = 10.0 + (cash_on_cash_roi - 5) * 2
        elif cash_on_cash_roi >= 0:
            score["yield_score"] = cash_on_cash_roi * 2
        else:
            score["yield_score"] = 0.0

        # Cap rate score (0-25)
        # >10% = 25, 7-10% = 15-25, 4-7% = 5-15, 0-4% = 0-5, negative = 0
        if cap_rate >= 10:
            score["cap_rate_score"] = 25.0
        elif cap_rate >= 7:
            score["cap_rate_score"] = 15.0 + (cap_rate - 7) * (10 / 3)
        elif cap_rate >= 4:
            score["cap_rate_score"] = 5.0 + (cap_rate - 4) * (10 / 3)
        elif cap_rate >= 0:
            score["cap_rate_score"] = cap_rate * 1.25
        else:
            score["cap_rate_score"] = 0.0

        # Cash flow margin (0-20)
        # Positive ratio > 20% = 20, 10-20% = 10-20, 0-10% = 0-10, negative = 0
        if monthly_cash_flow > 0:
            margin = (monthly_cash_flow / property_price) * 100 if property_price > 0 else 0
            if margin >= 0.2:  # 0.2% monthly margin
                score["cash_flow_score"] = 20.0
            elif margin >= 0.1:
                score["cash_flow_score"] = 10.0 + (margin - 0.1) * 100
            else:
                score["cash_flow_score"] = margin * 100
        else:
            score["cash_flow_score"] = 0.0

        # Net yield score (0-15)
        # >12% = 15, 8-12% = 10-15, 4-8% = 5-10, 0-4% = 0-5, negative = 0
        if net_yield >= 12:
            score["net_yield_score"] = 15.0
        elif net_yield >= 8:
            score["net_yield_score"] = 10.0 + (net_yield - 8) * 1.25
        elif net_yield >= 4:
            score["net_yield_score"] = 5.0 + (net_yield - 4) * 1.25
        elif net_yield >= 0:
            score["net_yield_score"] = net_yield * 1.25
        else:
            score["net_yield_score"] = 0.0

        # Risk factor (0-10): Positive cash flow reduces risk
        if monthly_cash_flow > 0 and cash_on_cash_roi > 5:
            score["risk_score"] = 10.0
        elif monthly_cash_flow > 0 and cash_on_cash_roi > 0:
            score["risk_score"] = 5.0 + cash_on_cash_roi
        elif monthly_cash_flow > 0:
            score["risk_score"] = 5.0
        else:
            score["risk_score"] = 0.0

        return score

    def _run(self, **kwargs: Any) -> str:
        """Execute investment analysis."""
        try:
            result = self.calculate(**kwargs)

            formatted = f"""
Investment Analysis for ${kwargs.get("property_price", 0):,.2f} Property:

=== KEY METRICS ===
Monthly Cash Flow:     ${result.monthly_cash_flow:,.2f}
Annual Cash Flow:      ${result.annual_cash_flow:,.2f}
Cash on Cash ROI:      {result.cash_on_cash_roi:.2f}%
Cap Rate:              {result.cap_rate:.2f}%
Gross Yield:           {result.gross_yield:.2f}%
Net Yield:             {result.net_yield:.2f}%
Total Investment:      ${result.total_investment:,.2f}

=== INVESTMENT SCORE: {result.investment_score:.1f}/100 ===
Breakdown:
"""
            for key, value in result.score_breakdown.items():
                formatted += f"- {key.replace('_', ' ').title()}: {value:.1f}\n"

            formatted += f"""
=== MONTHLY BREAKDOWN ===
Income:                ${result.monthly_income:,.2f}
- Mortgage Payment:    ${result.monthly_mortgage:,.2f}
- Operating Expenses:  ${result.monthly_expenses - result.monthly_mortgage:,.2f}
Total Expenses:        ${result.monthly_expenses:,.2f}
Monthly Cash Flow:     ${result.monthly_cash_flow:,.2f}

=== ANNUAL BREAKDOWN ===
Annual Income:         ${result.annual_income:,.2f}
Annual Expenses:       ${result.annual_expenses:,.2f}
Annual Cash Flow:      ${result.annual_cash_flow:,.2f}
"""
            return formatted.strip()

        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error calculating investment analysis: {str(e)}"

    async def _arun(self, **kwargs: Any) -> str:
        """Async version."""
        return self._run(**kwargs)


# Task #39: Advanced Investment Analytics
class AdvancedInvestmentInput(BaseModel):
    """Input for advanced investment analysis with projections."""

    # Base property info
    property_price: float = Field(description="Purchase price", gt=0)
    monthly_rent: float = Field(description="Expected monthly rent", gt=0)

    # Financing
    down_payment_percent: float = Field(default=20.0, ge=0, le=100)
    interest_rate: float = Field(default=4.5, ge=0)
    loan_years: int = Field(default=30, gt=0, le=50)

    # Operating expenses (monthly)
    property_tax_monthly: float = Field(default=0.0, ge=0)
    insurance_monthly: float = Field(default=0.0, ge=0)
    hoa_monthly: float = Field(default=0.0, ge=0)
    maintenance_percent: float = Field(default=1.0, ge=0)
    vacancy_rate: float = Field(default=5.0, ge=0, le=100)
    management_percent: float = Field(default=0.0, ge=0)

    # Advanced projection settings
    projection_years: int = Field(default=20, ge=1, le=30)
    appreciation_rate: float = Field(default=3.0, description="Annual appreciation %")
    rent_growth_rate: float = Field(default=2.0, description="Annual rent growth %")
    marginal_tax_rate: float = Field(default=0.0, ge=0, le=50)
    land_value_ratio: float = Field(default=0.2, ge=0, le=1)
    market_volatility: float = Field(default=0.5, ge=0, le=1)


class AdvancedInvestmentResult(BaseModel):
    """Result from advanced investment analysis."""

    # Base metrics (from standard analysis)
    monthly_cash_flow: float
    annual_cash_flow: float
    cap_rate: float
    cash_on_cash_roi: float
    total_investment: float

    # Projection results
    cash_flow_projection: List[Dict[str, Any]] = Field(default_factory=list)
    total_projected_cash_flow: float = 0.0
    final_equity: float = 0.0
    irr: Optional[float] = None

    # Tax implications
    annual_depreciation: float = 0.0
    total_tax_deductions: float = 0.0
    tax_benefit: float = 0.0

    # Appreciation scenarios
    appreciation_scenarios: List[Dict[str, Any]] = Field(default_factory=list)

    # Risk assessment
    risk_score: float = 0.0
    risk_factors: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class AdvancedInvestmentTool(BaseTool):
    """Tool for advanced investment analysis with projections."""

    name: str = "advanced_investment_analyzer"
    description: str = (
        "Advanced investment analysis with multi-year cash flow projections, "
        "tax implications, appreciation scenarios, and risk assessment."
    )
    args_schema: type[AdvancedInvestmentInput] = AdvancedInvestmentInput

    @staticmethod
    def calculate(
        property_price: float,
        monthly_rent: float,
        down_payment_percent: float = 20.0,
        interest_rate: float = 4.5,
        loan_years: int = 30,
        property_tax_monthly: float = 0.0,
        insurance_monthly: float = 0.0,
        hoa_monthly: float = 0.0,
        maintenance_percent: float = 1.0,
        vacancy_rate: float = 5.0,
        management_percent: float = 0.0,
        projection_years: int = 20,
        appreciation_rate: float = 3.0,
        rent_growth_rate: float = 2.0,
        marginal_tax_rate: float = 0.0,
        land_value_ratio: float = 0.2,
        market_volatility: float = 0.5,
    ) -> AdvancedInvestmentResult:
        """Calculate advanced investment metrics with projections."""
        from analytics.financial_metrics import ExpenseParams, MortgageParams
        from analytics.investment_analytics import InvestmentAnalyticsCalculator

        # Calculate base investment metrics
        base_result = InvestmentCalculatorTool.calculate(
            property_price=property_price,
            monthly_rent=monthly_rent,
            down_payment_percent=down_payment_percent,
            interest_rate=interest_rate,
            loan_years=loan_years,
            property_tax_monthly=property_tax_monthly,
            insurance_monthly=insurance_monthly,
            hoa_monthly=hoa_monthly,
            maintenance_percent=maintenance_percent,
            vacancy_rate=vacancy_rate,
            management_percent=management_percent,
        )

        # Setup params for advanced calculations
        mortgage = MortgageParams(
            interest_rate=interest_rate,
            loan_term_years=loan_years,
            down_payment_percent=down_payment_percent,
        )

        expenses = ExpenseParams(
            property_tax_rate=(property_tax_monthly * 12 / property_price) * 100
            if property_price > 0
            else 0,
            insurance_annual=insurance_monthly * 12,
            maintenance_rate=maintenance_percent,
            vacancy_rate=vacancy_rate,
            management_fee_rate=management_percent,
            hoa_monthly=hoa_monthly,
        )

        # Cash flow projection
        projection = InvestmentAnalyticsCalculator.project_cash_flows(
            property_price=property_price,
            monthly_rent=monthly_rent,
            mortgage=mortgage,
            expenses=expenses,
            appreciation_rate=appreciation_rate,
            rent_growth_rate=rent_growth_rate,
            projection_years=projection_years,
        )

        # Tax implications
        loan_amount = property_price * (1 - down_payment_percent / 100)
        first_year_interest = loan_amount * (interest_rate / 100)

        tax_implications = InvestmentAnalyticsCalculator.calculate_tax_implications(
            property_price=property_price,
            land_value_ratio=land_value_ratio,
            mortgage_interest_annual=first_year_interest,
            property_tax_annual=property_tax_monthly * 12,
            marginal_tax_rate=marginal_tax_rate,
        )

        # Appreciation scenarios
        scenarios = InvestmentAnalyticsCalculator.calculate_appreciation_scenarios(
            property_price=property_price,
            years=projection_years,
        )

        # Risk assessment
        debt_service_ratio = (
            (base_result.annual_cash_flow + base_result.monthly_expenses * 12)
            / (base_result.monthly_expenses * 12)
            if base_result.monthly_expenses > 0
            else 1.0
        )

        risk = InvestmentAnalyticsCalculator.assess_risk(
            property_price=property_price,
            monthly_cash_flow=base_result.monthly_cash_flow,
            cap_rate=base_result.cap_rate,
            debt_service_ratio=debt_service_ratio,
            vacancy_rate=vacancy_rate,
            market_volatility=market_volatility,
            loan_to_value=1 - down_payment_percent / 100,
        )

        # Convert projection to dict format
        projection_list = [
            {
                "year": y.year,
                "gross_income": y.gross_income,
                "operating_expenses": y.operating_expenses,
                "mortgage_payment": y.mortgage_payment,
                "noi": y.noi,
                "cash_flow": y.cash_flow,
                "cumulative_cash_flow": y.cumulative_cash_flow,
                "property_value": y.property_value,
                "equity": y.equity,
                "loan_balance": y.loan_balance,
            }
            for y in projection.yearly_breakdown
        ]

        # Convert scenarios to dict format
        scenarios_list = [
            {
                "name": s.name,
                "annual_rate": s.annual_rate,
                "projected_values": s.projected_values,
                "total_appreciation_percent": s.total_appreciation_percent,
                "total_appreciation_amount": s.total_appreciation_amount,
            }
            for s in scenarios
        ]

        return AdvancedInvestmentResult(
            monthly_cash_flow=base_result.monthly_cash_flow,
            annual_cash_flow=base_result.annual_cash_flow,
            cap_rate=base_result.cap_rate,
            cash_on_cash_roi=base_result.cash_on_cash_roi,
            total_investment=base_result.total_investment,
            cash_flow_projection=projection_list,
            total_projected_cash_flow=projection.total_cash_flow,
            final_equity=projection.final_equity,
            irr=projection.irr,
            annual_depreciation=tax_implications.annual_depreciation,
            total_tax_deductions=tax_implications.total_annual_deductions,
            tax_benefit=tax_implications.effective_tax_benefit,
            appreciation_scenarios=scenarios_list,
            risk_score=risk.overall_score,
            risk_factors=risk.risk_factors,
            recommendations=risk.recommendations,
        )

    def _run(self, **kwargs: Any) -> str:
        """Execute advanced investment analysis."""
        try:
            result = self.calculate(**kwargs)

            output = [
                "Advanced Investment Analysis",
                "=" * 40,
                "",
                "BASE METRICS",
                f"  Monthly Cash Flow: ${result.monthly_cash_flow:,.2f}",
                f"  Annual Cash Flow: ${result.annual_cash_flow:,.2f}",
                f"  Cap Rate: {result.cap_rate:.2f}%",
                f"  Cash on Cash ROI: {result.cash_on_cash_roi:.2f}%",
                "",
                "PROJECTION SUMMARY",
                f"  Projection Period: {len(result.cash_flow_projection)} years",
                f"  Total Projected Cash Flow: ${result.total_projected_cash_flow:,.2f}",
                f"  Final Equity: ${result.final_equity:,.2f}",
                f"  IRR: {result.irr:.2f}%" if result.irr else "  IRR: N/A",
                "",
                "TAX IMPLICATIONS",
                f"  Annual Depreciation: ${result.annual_depreciation:,.2f}",
                f"  Total Tax Deductions: ${result.total_tax_deductions:,.2f}",
                f"  Tax Benefit: ${result.tax_benefit:,.2f}/year",
                "",
                "RISK ASSESSMENT",
                f"  Risk Score: {result.risk_score:.1f}/100",
            ]

            if result.risk_factors:
                output.append("  Risk Factors:")
                for factor in result.risk_factors:
                    output.append(f"    - {factor}")

            if result.recommendations:
                output.append("  Recommendations:")
                for rec in result.recommendations:
                    output.append(f"    - {rec}")

            return "\n".join(output)

        except Exception as e:
            return f"Advanced Investment Analysis Error: {str(e)}"

    async def _arun(self, **kwargs: Any) -> str:
        """Async version."""
        return self._run(**kwargs)
