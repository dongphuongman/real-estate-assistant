"""
Property-specific tools for the agent.

This module provides specialized tools for property analysis, comparison,
and calculations.
"""

import math
import statistics
from typing import Any, ClassVar, Dict, List, Optional

# Import AI listing generator tools (TASK-023)
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from tools.listing_generator_tools import (
    HeadlineGeneratorTool,
    PropertyDescriptionGeneratorTool,
    SocialMediaContentGeneratorTool,
)

# We use Any for vector_store to avoid circular imports/tight coupling
# expected type: vector_store.chroma_store.ChromaPropertyStore


class MortgageInput(BaseModel):
    """Input for mortgage calculator."""

    property_price: float = Field(description="Total property price", gt=0)
    down_payment_percent: float = Field(
        default=20.0, description="Down payment as percentage (e.g., 20 for 20%)", ge=0, le=100
    )
    interest_rate: float = Field(
        default=4.5, description="Annual interest rate as percentage (e.g., 4.5 for 4.5%)", ge=0
    )
    loan_years: int = Field(default=30, description="Loan term in years", gt=0, le=50)


class PropertyComparisonInput(BaseModel):
    """Input for property comparison tool."""

    property_ids: str = Field(
        description="Comma-separated list of property IDs to compare", min_length=1
    )


class PriceAnalysisInput(BaseModel):
    """Input for price analysis tool."""

    query: str = Field(
        description="Search query for price analysis (e.g., 'apartments in Madrid')", min_length=1
    )


class LocationAnalysisInput(BaseModel):
    """Input for location analysis tool."""

    property_id: str = Field(description="Property ID to analyze", min_length=1)


class MortgageResult(BaseModel):
    """Result from mortgage calculator."""

    monthly_payment: float
    total_interest: float
    total_cost: float
    down_payment: float
    loan_amount: float
    breakdown: Dict[str, float]


class TCOInput(BaseModel):
    """Input for Total Cost of Ownership calculator."""

    # Mortgage inputs (required)
    property_price: float = Field(description="Total property price", gt=0)
    down_payment_percent: float = Field(
        default=20.0, description="Down payment as percentage (e.g., 20 for 20%)", ge=0, le=100
    )
    interest_rate: float = Field(
        default=4.5, description="Annual interest rate as percentage (e.g., 4.5 for 4.5%)", ge=0
    )
    loan_years: int = Field(default=30, description="Loan term in years", gt=0, le=50)

    # Additional ownership costs (optional, default to 0)
    monthly_hoa: float = Field(default=0.0, description="Monthly HOA/condo fees", ge=0)
    annual_property_tax: float = Field(default=0.0, description="Annual property tax", ge=0)
    annual_insurance: float = Field(default=0.0, description="Annual home insurance", ge=0)
    monthly_utilities: float = Field(
        default=0.0, description="Monthly utilities (electric, gas, water)", ge=0
    )
    monthly_internet: float = Field(default=0.0, description="Monthly internet/cable", ge=0)
    monthly_parking: float = Field(default=0.0, description="Monthly parking cost", ge=0)
    maintenance_percent: float = Field(
        default=1.0, description="Annual maintenance as % of property value", ge=0, le=5
    )


class TCOResult(BaseModel):
    """Result from Total Cost of Ownership calculator."""

    # Mortgage components
    monthly_payment: float
    total_interest: float
    down_payment: float
    loan_amount: float

    # TCO components (monthly)
    monthly_mortgage: float
    monthly_property_tax: float
    monthly_insurance: float
    monthly_hoa: float
    monthly_utilities: float
    monthly_internet: float
    monthly_parking: float
    monthly_maintenance: float
    monthly_tco: float

    # TCO components (annual)
    annual_mortgage: float
    annual_property_tax: float
    annual_insurance: float
    annual_hoa: float
    annual_utilities: float
    annual_internet: float
    annual_parking: float
    annual_maintenance: float
    annual_tco: float

    # Total over loan term
    total_ownership_cost: float
    total_all_costs: float  # Including down payment

    breakdown: Dict[str, float]


class MortgageCalculatorTool(BaseTool):
    """Tool for calculating mortgage payments and costs."""

    name: str = "mortgage_calculator"
    description: str = (
        "Calculate mortgage payments for a property. "
        "Input should be property price, down payment %, interest rate %, and loan years. "
        "Returns monthly payment, total interest, and breakdown."
    )

    @staticmethod
    def calculate(
        property_price: float,
        down_payment_percent: float = 20.0,
        interest_rate: float = 4.5,
        loan_years: int = 30,
    ) -> MortgageResult:
        """Pure calculation logic returning structured data."""
        # Validate inputs (raising ValueError instead of returning string error)
        if property_price <= 0:
            raise ValueError("Property price must be positive")
        if not 0 <= down_payment_percent <= 100:
            raise ValueError("Down payment must be between 0 and 100%")
        if interest_rate < 0:
            raise ValueError("Interest rate cannot be negative")
        if loan_years <= 0:
            raise ValueError("Loan term must be positive")

        # Calculate values
        down_payment = property_price * (down_payment_percent / 100)
        loan_amount = property_price - down_payment

        # Monthly interest rate
        monthly_rate = (interest_rate / 100) / 12
        num_payments = loan_years * 12

        # Calculate monthly payment using mortgage formula
        if monthly_rate == 0:
            monthly_payment = loan_amount / num_payments
        else:
            monthly_payment = (
                loan_amount * monthly_rate * math.pow(1 + monthly_rate, num_payments)
            ) / (math.pow(1 + monthly_rate, num_payments) - 1)

        # Total costs
        total_paid = monthly_payment * num_payments
        total_interest = total_paid - loan_amount
        total_cost = total_paid + down_payment

        return MortgageResult(
            monthly_payment=monthly_payment,
            total_interest=total_interest,
            total_cost=total_cost,
            down_payment=down_payment,
            loan_amount=loan_amount,
            breakdown={
                "principal": loan_amount,
                "interest": total_interest,
                "down_payment": down_payment,
            },
        )

    def _run(
        self,
        property_price: float,
        down_payment_percent: float = 20.0,
        interest_rate: float = 4.5,
        loan_years: int = 30,
    ) -> str:
        """Execute mortgage calculation."""
        try:
            result = self.calculate(property_price, down_payment_percent, interest_rate, loan_years)

            # Format result
            formatted = f"""
Mortgage Calculation for ${property_price:,.2f} Property:

Down Payment ({down_payment_percent}%): ${result.down_payment:,.2f}
Loan Amount: ${result.loan_amount:,.2f}

Monthly Payment: ${result.monthly_payment:,.2f}
Annual Payment: ${result.monthly_payment * 12:,.2f}

Total Interest ({loan_years} years): ${result.total_interest:,.2f}
Total Amount Paid: ${result.total_cost - result.down_payment:,.2f}
Total Cost (with down payment): ${result.total_cost:,.2f}

Breakdown:
- Principal: ${result.loan_amount:,.2f}
- Interest: ${result.total_interest:,.2f}
- Down Payment: ${result.down_payment:,.2f}
"""
            return formatted.strip()

        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error calculating mortgage: {str(e)}"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async version."""
        return self._run(*args, **kwargs)


class TCOCalculatorTool(BaseTool):
    """Tool for calculating Total Cost of Ownership."""

    name: str = "tco_calculator"
    description: str = (
        "Calculate the Total Cost of Ownership for a property. "
        "Includes mortgage, property taxes, insurance, HOA fees, utilities, maintenance, and parking. "
        "Returns monthly and annual breakdowns."
    )
    args_schema: type[TCOInput] = TCOInput

    @staticmethod
    def calculate(
        property_price: float,
        down_payment_percent: float = 20.0,
        interest_rate: float = 4.5,
        loan_years: int = 30,
        monthly_hoa: float = 0.0,
        annual_property_tax: float = 0.0,
        annual_insurance: float = 0.0,
        monthly_utilities: float = 0.0,
        monthly_internet: float = 0.0,
        monthly_parking: float = 0.0,
        maintenance_percent: float = 1.0,
    ) -> TCOResult:
        """Calculate Total Cost of Ownership."""
        # First, calculate mortgage components
        mortgage_result = MortgageCalculatorTool.calculate(
            property_price, down_payment_percent, interest_rate, loan_years
        )

        # Calculate monthly ownership costs
        monthly_property_tax = annual_property_tax / 12
        monthly_insurance = annual_insurance / 12
        monthly_maintenance = (property_price * maintenance_percent / 100) / 12

        # Total monthly TCO (excluding down payment)
        monthly_tco = (
            mortgage_result.monthly_payment
            + monthly_property_tax
            + monthly_insurance
            + monthly_hoa
            + monthly_utilities
            + monthly_internet
            + monthly_parking
            + monthly_maintenance
        )

        # Calculate annual totals
        annual_mortgage = mortgage_result.monthly_payment * 12
        annual_hoa = monthly_hoa * 12
        annual_utilities = monthly_utilities * 12
        annual_internet = monthly_internet * 12
        annual_parking = monthly_parking * 12
        annual_maintenance = monthly_maintenance * 12
        annual_tco = monthly_tco * 12

        # Total over loan term
        total_ownership_cost = annual_tco * loan_years
        total_all_costs = total_ownership_cost + mortgage_result.down_payment

        return TCOResult(
            # Mortgage components
            monthly_payment=mortgage_result.monthly_payment,
            total_interest=mortgage_result.total_interest,
            down_payment=mortgage_result.down_payment,
            loan_amount=mortgage_result.loan_amount,
            # TCO components (monthly)
            monthly_mortgage=mortgage_result.monthly_payment,
            monthly_property_tax=monthly_property_tax,
            monthly_insurance=monthly_insurance,
            monthly_hoa=monthly_hoa,
            monthly_utilities=monthly_utilities,
            monthly_internet=monthly_internet,
            monthly_parking=monthly_parking,
            monthly_maintenance=monthly_maintenance,
            monthly_tco=monthly_tco,
            # TCO components (annual)
            annual_mortgage=annual_mortgage,
            annual_property_tax=annual_property_tax,
            annual_insurance=annual_insurance,
            annual_hoa=annual_hoa,
            annual_utilities=annual_utilities,
            annual_internet=annual_internet,
            annual_parking=annual_parking,
            annual_maintenance=annual_maintenance,
            annual_tco=annual_tco,
            # Total over loan term
            total_ownership_cost=total_ownership_cost,
            total_all_costs=total_all_costs,
            breakdown={
                "mortgage": mortgage_result.monthly_payment,
                "property_tax": monthly_property_tax,
                "insurance": monthly_insurance,
                "hoa": monthly_hoa,
                "utilities": monthly_utilities,
                "internet": monthly_internet,
                "parking": monthly_parking,
                "maintenance": monthly_maintenance,
            },
        )

    def _run(
        self,
        property_price: float,
        down_payment_percent: float = 20.0,
        interest_rate: float = 4.5,
        loan_years: int = 30,
        monthly_hoa: float = 0.0,
        annual_property_tax: float = 0.0,
        annual_insurance: float = 0.0,
        monthly_utilities: float = 0.0,
        monthly_internet: float = 0.0,
        monthly_parking: float = 0.0,
        maintenance_percent: float = 1.0,
    ) -> str:
        """Execute TCO calculation."""
        try:
            result = self.calculate(
                property_price,
                down_payment_percent,
                interest_rate,
                loan_years,
                monthly_hoa,
                annual_property_tax,
                annual_insurance,
                monthly_utilities,
                monthly_internet,
                monthly_parking,
                maintenance_percent,
            )

            formatted = f"""
Total Cost of Ownership for ${property_price:,.2f} Property:

=== Monthly Costs ===
Mortgage Payment:        ${result.monthly_mortgage:,.2f}
Property Tax:            ${result.monthly_property_tax:,.2f}
Home Insurance:          ${result.monthly_insurance:,.2f}
HOA Fees:                ${result.monthly_hoa:,.2f}
Utilities:               ${result.monthly_utilities:,.2f}
Internet/Cable:          ${result.monthly_internet:,.2f}
Parking:                 ${result.monthly_parking:,.2f}
Maintenance (1% rule):   ${result.monthly_maintenance:,.2f}
─────────────────────────────────────────
MONTHLY TCO:             ${result.monthly_tco:,.2f}

=== Annual Costs ===
Annual Mortgage:         ${result.annual_mortgage:,.2f}
Annual Property Tax:     ${result.annual_property_tax:,.2f}
Annual Insurance:        ${result.annual_insurance:,.2f}
Annual HOA:              ${result.annual_hoa:,.2f}
Annual Utilities:        ${result.annual_utilities:,.2f}
Annual Internet:         ${result.annual_internet:,.2f}
Annual Parking:          ${result.annual_parking:,.2f}
Annual Maintenance:      ${result.annual_maintenance:,.2f}
─────────────────────────────────────────
ANNUAL TCO:              ${result.annual_tco:,.2f}

=== Total Over {loan_years} Years ===
Total Ownership Cost:    ${result.total_ownership_cost:,.2f}
Plus Down Payment:       ${result.down_payment:,.2f}
─────────────────────────────────────────
TOTAL ALL-IN COST:       ${result.total_all_costs:,.2f}
"""
            return formatted.strip()

        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error calculating TCO: {str(e)}"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async version."""
        return self._run(*args, **kwargs)


class PropertyComparisonTool(BaseTool):
    """Tool for comparing properties side-by-side."""

    name: str = "property_comparator"
    description: str = (
        "Compare multiple properties based on various criteria. "
        "Input should be a comma-separated list of property IDs (e.g., 'prop1, prop2'). "
        "Returns a detailed comparison table."
    )
    args_schema: type[PropertyComparisonInput] = PropertyComparisonInput

    _vector_store: Any = PrivateAttr()

    def __init__(self, vector_store: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_store = vector_store

    def _run(self, property_ids: str) -> str:
        """
        Compare properties.

        Args:
            property_ids: Comma-separated list of property IDs
        """
        try:
            if self._vector_store is None:
                return (
                    "Property Comparison:\n"
                    "Provide a comma-separated list of property IDs to compare.\n"
                    "Comparison includes price, area, rooms, and key features."
                )

            # Parse IDs
            ids = [pid.strip() for pid in property_ids.split(",") if pid.strip()]

            if not ids:
                return "Please provide at least one property ID to compare."

            # Fetch properties
            if hasattr(self._vector_store, "get_properties_by_ids"):
                docs = self._vector_store.get_properties_by_ids(ids)
            else:
                return "Vector store does not support retrieving by IDs."

            if not docs:
                return f"No properties found for IDs: {property_ids}"

            # Build comparison
            comparison = ["Property Comparison:"]

            # Extract common fields
            fields = [
                "price",
                "price_per_sqm",
                "city",
                "rooms",
                "bathrooms",
                "area_sqm",
                "year_built",
                "property_type",
            ]

            # Header
            header = f"{'Feature':<20} | " + " | ".join(
                [f"{d.metadata.get('id', 'Unknown')[:10]:<15}" for d in docs]
            )
            comparison.append(header)
            comparison.append("-" * len(header))

            for field in fields:
                row = f"{field.replace('_', ' ').title():<20} | "
                values = []
                for doc in docs:
                    val = doc.metadata.get(field, "N/A")
                    if field == "price" and isinstance(val, (int, float)):
                        val = f"${val:,.0f}"
                    elif field == "price_per_sqm" and isinstance(val, (int, float)):
                        val = f"${val:,.0f}/m²"
                    elif field == "area_sqm" and isinstance(val, (int, float)):
                        val = f"{val} m²"
                    values.append(f"{str(val):<15}")
                row += " | ".join(values)
                comparison.append(row)

            # Add Pros/Cons placeholder or analysis
            comparison.append("\nSummary:")
            prices = [
                d.metadata.get("price", 0)
                for d in docs
                if isinstance(d.metadata.get("price"), (int, float))
            ]
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                diff = max_price - min_price
                comparison.append(f"Price difference: ${diff:,.0f}")

            return "\n".join(comparison)

        except Exception as e:
            return f"Error comparing properties: {str(e)}"

    async def _arun(self, property_ids: str) -> str:
        """Async version."""
        return self._run(property_ids)


class PriceAnalysisTool(BaseTool):
    """Tool for analyzing property prices and market trends."""

    name: str = "price_analyzer"
    description: str = (
        "Analyze property prices for a given location or criteria. "
        "Input should be a search query (e.g., 'apartments in Madrid'). "
        "Returns statistical analysis of prices."
    )
    args_schema: type[PriceAnalysisInput] = PriceAnalysisInput

    _vector_store: Any = PrivateAttr()

    def __init__(self, vector_store: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_store = vector_store

    def _run(self, query: str) -> str:
        """
        Analyze prices.

        Args:
            query: Search query
        """
        try:
            if self._vector_store is None:
                return (
                    f"Price Analysis for '{query}':\n"
                    "- Average: N/A\n"
                    "- Median: N/A\n"
                    "- Min: N/A\n"
                    "- Max: N/A\n"
                    "Provide a data source to compute statistics."
                )

            # Search for properties (fetch more for stats)
            results = self._vector_store.search(query, k=20)

            if not results:
                return f"No properties found for analysis: {query}"

            docs = [doc for doc, _ in results]

            # Extract prices
            prices: List[float] = []
            for d in docs:
                raw_price = d.metadata.get("price")
                if raw_price is None:
                    continue
                try:
                    prices.append(float(raw_price))
                except (TypeError, ValueError):
                    continue

            sqm_prices: List[float] = []
            for d in docs:
                raw_ppsqm = d.metadata.get("price_per_sqm")
                if raw_ppsqm is None:
                    continue
                try:
                    sqm_prices.append(float(raw_ppsqm))
                except (TypeError, ValueError):
                    continue

            if not prices:
                return "Found properties but no price data available."

            # Calculate stats
            stats_output = [f"Price Analysis for '{query}' (based on {len(prices)} listings):"]

            stats_output.append("\nTotal Prices:")
            stats_output.append(f"- Average: ${statistics.mean(prices):,.2f}")
            stats_output.append(f"- Median: ${statistics.median(prices):,.2f}")
            stats_output.append(f"- Min: ${min(prices):,.2f}")
            stats_output.append(f"- Max: ${max(prices):,.2f}")

            if sqm_prices:
                stats_output.append("\nPrice per m²:")
                stats_output.append(f"- Average: ${statistics.mean(sqm_prices):,.2f}/m²")
                stats_output.append(f"- Median: ${statistics.median(sqm_prices):,.2f}/m²")

            # Distribution by type
            types: Dict[str, int] = {}
            for d in docs:
                ptype = d.metadata.get("property_type", "Unknown")
                types[ptype] = types.get(ptype, 0) + 1

            stats_output.append("\nDistribution by Type:")
            for ptype, count in types.items():
                stats_output.append(f"- {ptype}: {count}")

            return "\n".join(stats_output)

        except Exception as e:
            return f"Error analyzing prices: {str(e)}"

    async def _arun(self, query: str) -> str:
        """Async version."""
        return self._run(query)


class LocationAnalysisTool(BaseTool):
    """Tool for analyzing property locations and proximity."""

    name: str = "location_analyzer"
    description: str = (
        "Analyze a specific property's location. "
        "Input should be a property ID. "
        "Returns location details and nearby properties info."
    )
    args_schema: type[LocationAnalysisInput] = LocationAnalysisInput

    _vector_store: Any = PrivateAttr()

    def __init__(self, vector_store: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_store = vector_store

    def _run(self, property_id: str) -> str:
        """
        Analyze location.

        Args:
            property_id: Property ID
        """
        try:
            if self._vector_store is None:
                return (
                    f"Location Analysis for '{property_id}':\n"
                    "Neighborhood: N/A\n"
                    "Proximity: N/A\n"
                    "Provide a data source to compute distances and nearby listings."
                )

            # Get property
            if hasattr(self._vector_store, "get_properties_by_ids"):
                docs = self._vector_store.get_properties_by_ids([property_id])
            else:
                return "Vector store does not support retrieving by IDs."

            if not docs:
                return f"Property not found: {property_id}"

            target = docs[0]
            lat = target.metadata.get("lat")
            lon = target.metadata.get("lon")
            city = target.metadata.get("city", "Unknown")

            analysis = [f"Location Analysis for Property {property_id}:"]
            analysis.append(f"City: {city}")
            if target.metadata.get("neighborhood"):
                analysis.append(f"Neighborhood: {target.metadata.get('neighborhood')}")

            if lat and lon:
                analysis.append(f"Coordinates: {lat}, {lon}")

                # Find nearby properties (if hybrid search supports geo filtering)
                # We can't easily do a "nearby" query without a proper geo-filter constructed.
                # But we can try to search for properties in the same city.
                # Or if we had a dedicated "search_nearby" method.
                # For now, let's just return what we have.
                analysis.append("\nGeospatial data available. Use map view for nearby amenities.")
            else:
                analysis.append("Exact coordinates not available.")

            return "\n".join(analysis)

        except Exception as e:
            return f"Error analyzing location: {str(e)}"

    async def _arun(self, property_id: str) -> str:
        """Async version."""
        return self._run(property_id)


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
        "Calculate investment property metrics including ROI, cap rate, cash flow, and rental yield. "
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


class NeighborhoodQualityInput(BaseModel):
    """Input for neighborhood quality index calculation."""

    property_id: str = Field(description="Property ID to analyze", min_length=1)
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
    city: Optional[str] = Field(None, description="City name for data enrichment")
    neighborhood: Optional[str] = Field(None, description="Neighborhood name")


class NeighborhoodQualityResult(BaseModel):
    """Result from neighborhood quality index calculation."""

    property_id: str
    overall_score: float
    safety_score: float
    schools_score: float
    amenities_score: float
    walkability_score: float
    green_space_score: float
    score_breakdown: Dict[str, float]
    data_sources: List[str]
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None


class NeighborhoodQualityIndexTool(BaseTool):
    """Tool for calculating neighborhood quality index."""

    name: str = "neighborhood_quality_index"
    description: str = (
        "Calculate a comprehensive neighborhood quality score (0-100) "
        "based on safety, schools, amenities, walkability, and green space. "
        "Input should include property_id and optionally latitude/longitude. "
        "Returns detailed score breakdown and overall quality rating."
    )
    args_schema: type[NeighborhoodQualityInput] = NeighborhoodQualityInput

    # Score weights (industry standard based on NeighborhoodScout, AreaVibes, LocalLogic)
    WEIGHT_SAFETY: ClassVar[float] = 0.25
    WEIGHT_SCHOOLS: ClassVar[float] = 0.20
    WEIGHT_AMENITIES: ClassVar[float] = 0.20
    WEIGHT_WALKABILITY: ClassVar[float] = 0.20
    WEIGHT_GREEN_SPACE: ClassVar[float] = 0.15

    @staticmethod
    def _mock_safety_score(city: Optional[str], neighborhood: Optional[str]) -> float:
        """
        Mock safety score based on city/neighborhood (Phase 1).

        In production, this would call crime data APIs.
        Returns score 0-100.
        """
        # Demo: base score with some variation by city
        city_scores: Dict[str, float] = {
            "warsaw": 75.0,
            "krakow": 78.0,
            "wroclaw": 76.0,
            "poznan": 80.0,
            "gdansk": 77.0,
            "madrid": 72.0,
            "barcelona": 68.0,
            "london": 70.0,
            "berlin": 82.0,
            "paris": 65.0,
        }

        if city:
            base = city_scores.get(city.lower(), 70.0)
        else:
            base = 70.0

        # Add some variation for demo purposes
        import hashlib

        seed = f"{city}:{neighborhood or 'unknown'}".encode()
        hash_val = int(hashlib.sha256(seed).hexdigest()[:8], 16)
        variation = (hash_val % 21) - 10  # -10 to +10

        return max(0, min(100, round(base + variation, 1)))

    @staticmethod
    def _calculate_schools_score(latitude: Optional[float], longitude: Optional[float]) -> float:
        """
        Calculate schools score based on nearby school count.

        Uses OSM/Overpass data with mock fallback.
        Returns score 0-100.
        """
        if latitude is None or longitude is None:
            return 60.0  # Default middle score

        try:
            from data.adapters.neighborhood_adapter import get_neighborhood_adapter

            adapter = get_neighborhood_adapter()
            school_count = adapter.count_schools(latitude, longitude, radius_m=1000)

            # Score based on school count (0-10+ schools within 1km)
            # 0-1 schools = 30, 2-3 = 50, 4-5 = 70, 6+ = 85+
            if school_count == 0:
                score = 30.0
            elif school_count <= 2:
                score = 30.0 + (school_count * 10)
            elif school_count <= 5:
                score = 50.0 + ((school_count - 2) * 10)
            else:
                score = min(95.0, 70.0 + ((school_count - 5) * 5))

            return round(score, 1)

        except Exception:
            # Fallback to mock on error
            import hashlib

            seed = f"{latitude:.4f},{longitude:.4f}".encode()
            hash_val = int(hashlib.sha256(seed).hexdigest()[:8], 16)
            score = 50 + (hash_val % 51)  # 50-100 range
            return float(score)

    @staticmethod
    def _calculate_amenities_score(latitude: Optional[float], longitude: Optional[float]) -> float:
        """
        Calculate amenities score based on nearby POI count.

        Uses OSM/Overpass data with mock fallback.
        Returns score 0-100.
        """
        if latitude is None or longitude is None:
            return 65.0

        try:
            from data.adapters.neighborhood_adapter import get_neighborhood_adapter

            adapter = get_neighborhood_adapter()
            amenity_count = adapter.count_amenities(latitude, longitude, radius_m=500)

            # Score based on amenity count within 500m
            # 0-5 = 40, 6-15 = 60, 16-30 = 80, 31+ = 95+
            if amenity_count == 0:
                score = 40.0
            elif amenity_count <= 5:
                score = 40.0 + (amenity_count * 4)
            elif amenity_count <= 15:
                score = 60.0 + ((amenity_count - 5) * 2)
            elif amenity_count <= 30:
                score = 80.0 + ((amenity_count - 15) * 1)
            else:
                score = min(98.0, 85.0 + ((amenity_count - 30) * 0.5))

            return round(score, 1)

        except Exception:
            # Fallback to mock on error
            import hashlib

            seed = f"amenities:{latitude:.4f},{longitude:.4f}".encode()
            hash_val = int(hashlib.sha256(seed).hexdigest()[:8], 16)
            score = 55 + (hash_val % 46)
            return float(score)

    @staticmethod
    def _calculate_walkability_score(
        latitude: Optional[float], longitude: Optional[float]
    ) -> float:
        """
        Calculate walkability score based on POI density and diversity.

        Uses OSM/Overpass data with mock fallback.
        Returns score 0-100.
        """
        if latitude is None or longitude is None:
            return 60.0

        try:
            from data.adapters.neighborhood_adapter import get_neighborhood_adapter

            adapter = get_neighborhood_adapter()
            score = adapter.calculate_walkability(latitude, longitude, radius_m=500)

            return round(score, 1)

        except Exception:
            # Fallback to mock on error
            import hashlib

            seed = f"walk:{latitude:.4f},{longitude:.4f}".encode()
            hash_val = int(hashlib.sha256(seed).hexdigest()[:8], 16)
            score = 45 + (hash_val % 56)
            return float(score)

    @staticmethod
    def _calculate_green_space_score(
        latitude: Optional[float], longitude: Optional[float]
    ) -> float:
        """
        Calculate green space score based on nearby parks/forests.

        Uses OSM/Overpass data with mock fallback.
        Returns score 0-100.
        """
        if latitude is None or longitude is None:
            return 55.0

        try:
            from data.adapters.neighborhood_adapter import get_neighborhood_adapter

            adapter = get_neighborhood_adapter()
            green_count = adapter.count_green_spaces(latitude, longitude, radius_m=1000)

            # Score based on green spaces within 1km
            # 0 = 30, 1 = 50, 2-3 = 65, 4-5 = 80, 6+ = 90+
            if green_count == 0:
                score = 30.0
            elif green_count == 1:
                score = 50.0
            elif green_count <= 3:
                score = 65.0 + (green_count - 2) * 7.5
            elif green_count <= 5:
                score = 80.0 + (green_count - 4) * 5
            else:
                score = min(98.0, 85.0 + (green_count - 6) * 2)

            return round(score, 1)

        except Exception:
            # Fallback to mock on error
            import hashlib

            seed = f"green:{latitude:.4f},{longitude:.4f}".encode()
            hash_val = int(hashlib.sha256(seed).hexdigest()[:8], 16)
            score = 40 + (hash_val % 61)
            return float(score)

    @staticmethod
    def calculate(
        property_id: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
    ) -> NeighborhoodQualityResult:
        """
        Calculate neighborhood quality index.

        Returns NeighborhoodQualityResult with overall score and component breakdowns.
        """
        # Calculate individual component scores
        safety_score = NeighborhoodQualityIndexTool._mock_safety_score(city, neighborhood)
        schools_score = NeighborhoodQualityIndexTool._calculate_schools_score(latitude, longitude)
        amenities_score = NeighborhoodQualityIndexTool._calculate_amenities_score(
            latitude, longitude
        )
        walkability_score = NeighborhoodQualityIndexTool._calculate_walkability_score(
            latitude, longitude
        )
        green_space_score = NeighborhoodQualityIndexTool._calculate_green_space_score(
            latitude, longitude
        )

        # Calculate weighted overall score
        overall_score = (
            (safety_score * NeighborhoodQualityIndexTool.WEIGHT_SAFETY)
            + (schools_score * NeighborhoodQualityIndexTool.WEIGHT_SCHOOLS)
            + (amenities_score * NeighborhoodQualityIndexTool.WEIGHT_AMENITIES)
            + (walkability_score * NeighborhoodQualityIndexTool.WEIGHT_WALKABILITY)
            + (green_space_score * NeighborhoodQualityIndexTool.WEIGHT_GREEN_SPACE)
        )

        # Build score breakdown
        score_breakdown = {
            "safety_weighted": round(safety_score * NeighborhoodQualityIndexTool.WEIGHT_SAFETY, 2),
            "schools_weighted": round(
                schools_score * NeighborhoodQualityIndexTool.WEIGHT_SCHOOLS, 2
            ),
            "amenities_weighted": round(
                amenities_score * NeighborhoodQualityIndexTool.WEIGHT_AMENITIES, 2
            ),
            "walkability_weighted": round(
                walkability_score * NeighborhoodQualityIndexTool.WEIGHT_WALKABILITY, 2
            ),
            "green_space_weighted": round(
                green_space_score * NeighborhoodQualityIndexTool.WEIGHT_GREEN_SPACE, 2
            ),
        }

        # Data sources (Phase 2: Real OSM POI data, safety still uses mock)
        data_sources = ["mock_safety_data", "osm_overpass_api"]
        if latitude and longitude:
            data_sources.append("geographic_coordinates")

        return NeighborhoodQualityResult(
            property_id=property_id,
            overall_score=round(overall_score, 1),
            safety_score=round(safety_score, 1),
            schools_score=round(schools_score, 1),
            amenities_score=round(amenities_score, 1),
            walkability_score=round(walkability_score, 1),
            green_space_score=round(green_space_score, 1),
            score_breakdown=score_breakdown,
            data_sources=data_sources,
            latitude=latitude,
            longitude=longitude,
            city=city,
            neighborhood=neighborhood,
        )

    def _run(
        self,
        property_id: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
    ) -> str:
        """Execute neighborhood quality calculation."""
        try:
            result = self.calculate(
                property_id=property_id,
                latitude=latitude,
                longitude=longitude,
                city=city,
                neighborhood=neighborhood,
            )

            # Format result for display
            formatted = f"""
Neighborhood Quality Index for Property {result.property_id}:

=== OVERALL SCORE: {result.overall_score:.1f}/100 ===

Component Scores:
- Safety:       {result.safety_score:.1f}/100 (Weight: 25%)
- Schools:      {result.schools_score:.1f}/100 (Weight: 20%)
- Amenities:    {result.amenities_score:.1f}/100 (Weight: 20%)
- Walkability:  {result.walkability_score:.1f}/100 (Weight: 20%)
- Green Space:  {result.green_space_score:.1f}/100 (Weight: 15%)

Score Breakdown (Weighted):
"""

            for key, value in result.score_breakdown.items():
                formatted += f"- {key.replace('_', ' ').title()}: {value:.2f}\n"

            formatted += f"""
Data Sources: {", ".join(result.data_sources)}
Location: {result.city or "Unknown"}, {result.neighborhood or "Unknown"}
Coordinates: {result.latitude or "N/A"}, {result.longitude or "N/A"}

Rating: {self._get_rating_label(result.overall_score)}
"""
            return formatted.strip()

        except Exception as e:
            return f"Error calculating neighborhood quality: {str(e)}"

    @staticmethod
    def _get_rating_label(score: float) -> str:
        """Get human-readable rating label."""
        if score >= 85:
            return "Excellent - Highly desirable neighborhood"
        elif score >= 70:
            return "Good - Above average quality"
        elif score >= 55:
            return "Fair - Average neighborhood"
        elif score >= 40:
            return "Poor - Below average quality"
        else:
            return "Very Poor - Significant concerns"

    async def _arun(self, **kwargs: Any) -> str:
        """Async version."""
        return self._run(**kwargs)


# ============================================================================
# TASK-021: Commute Time Analysis Tools
# ============================================================================


class CommuteTimeInput(BaseModel):
    """Input for commute time analysis tool."""

    property_id: str = Field(description="Property ID to analyze commute from")
    destination_lat: float = Field(description="Destination latitude", ge=-90, le=90)
    destination_lon: float = Field(description="Destination longitude", ge=-180, le=180)
    mode: str = Field(
        default="transit",
        description="Commute mode: 'driving', 'walking', 'bicycling', or 'transit'",
    )
    destination_name: Optional[str] = Field(default=None, description="Optional destination name")
    departure_time: Optional[str] = Field(
        default=None,
        description="Optional departure time as ISO string (e.g., '2024-01-15T08:30:00')",
    )


class CommuteRankingInput(BaseModel):
    """Input for commute-based property ranking tool."""

    property_ids: str = Field(description="Comma-separated list of property IDs to rank")
    destination_lat: float = Field(description="Destination latitude", ge=-90, le=90)
    destination_lon: float = Field(description="Destination longitude", ge=-180, le=180)
    mode: str = Field(
        default="transit",
        description="Commute mode: 'driving', 'walking', 'bicycling', or 'transit'",
    )
    destination_name: Optional[str] = Field(default=None, description="Optional destination name")
    departure_time: Optional[str] = Field(
        default=None,
        description="Optional departure time as ISO string (e.g., '2024-01-15T08:30:00')",
    )


class CommuteTimeAnalysisTool(BaseTool):
    """
    Tool for calculating commute time from a property to a destination.

    Uses Google Routes API to calculate accurate commute times including
    real-time traffic conditions and transit schedules.
    """

    name: str = "commute_time_analyzer"
    description: str = (
        "Calculate commute time from a property to a destination. "
        "Input: property_id, destination coordinates, mode (driving/walking/bicycling/transit). "
        "Returns: duration, distance, and route information for the commute."
    )
    args_schema: type[BaseModel] = CommuteTimeInput

    _vector_store: Any = PrivateAttr()

    def __init__(self, vector_store: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_store = vector_store

    def _run(
        self,
        property_id: str,
        destination_lat: float,
        destination_lon: float,
        mode: str = "transit",
        destination_name: Optional[str] = None,
        departure_time: Optional[str] = None,
    ) -> str:
        """
        Calculate commute time from property to destination.

        Args:
            property_id: Property ID for the origin.
            destination_lat: Destination latitude.
            destination_lon: Destination longitude.
            mode: Travel mode - 'driving', 'walking', 'bicycling', or 'transit'.
            destination_name: Optional destination name for display.
            departure_time: Optional departure time for transit scheduling.

        Returns:
            Formatted string with commute time analysis.
        """
        try:
            from utils.commute_client import CommuteTimeClient

            # Get property coordinates
            if self._vector_store is None:
                return (
                    f"Commute Analysis for '{property_id}':\n"
                    "Error: Vector store not available. Cannot retrieve property coordinates."
                )

            docs = self._vector_store.get_properties_by_ids([property_id])
            if not docs:
                return f"Commute Analysis for '{property_id}':\nError: Property not found."

            md = docs[0].metadata or {}
            origin_lat = md.get("lat")
            origin_lon = md.get("lon")

            if origin_lat is None or origin_lon is None:
                return (
                    f"Commute Analysis for '{property_id}':\n"
                    "Error: Property coordinates not available."
                )

            # Parse departure time if provided
            from datetime import datetime

            parsed_departure_time = None
            if departure_time:
                try:
                    parsed_departure_time = datetime.fromisoformat(departure_time)
                except ValueError:
                    return "Error: Invalid departure_time format. Use ISO format (e.g., '2024-01-15T08:30:00')."

            # Create client and calculate commute time
            client = CommuteTimeClient()

            import asyncio

            result = asyncio.run(
                client.get_commute_time(
                    property_id=property_id,
                    origin_lat=float(origin_lat),
                    origin_lon=float(origin_lon),
                    destination_lat=destination_lat,
                    destination_lon=destination_lon,
                    mode=mode,
                    destination_name=destination_name,
                    departure_time=parsed_departure_time,
                )
            )

            # Format output
            dest_display = destination_name or f"({destination_lat:.4f}, {destination_lon:.4f})"
            mode_display = mode.capitalize()

            output = [
                f"Commute Analysis for Property '{property_id}':",
                "",
                f"Destination: {dest_display}",
                f"Mode: {mode_display}",
                "",
                f"Duration: {result.duration_text}",
                f"Distance: {result.distance_text}",
            ]

            if result.arrival_time:
                output.append(f"Arrival: {result.arrival_time.strftime('%H:%M')}")

            # Add context for the commute duration
            minutes = result.duration_seconds // 60
            if minutes < 30:
                assessment = "Excellent commute time!"
            elif minutes < 45:
                assessment = "Reasonable commute time."
            elif minutes < 60:
                assessment = "Long commute - consider carefully."
            else:
                assessment = "Very long commute - may impact quality of life."

            output.append(f"\nAssessment: {assessment}")

            return "\n".join(output)

        except Exception as e:
            return (
                f"Commute Analysis for '{property_id}':\nError calculating commute time: {str(e)}"
            )

    async def _arun(self, **kwargs: Any) -> str:
        """Async version."""
        return self._run(**kwargs)


class CommuteRankingTool(BaseTool):
    """
    Tool for ranking multiple properties by commute time to a destination.

    Compares commute times from multiple properties to a common destination
    and returns a ranked list from shortest to longest commute.
    """

    name: str = "commute_ranking"
    description: str = (
        "Rank multiple properties by commute time to a destination. "
        "Input: comma-separated property_ids, destination coordinates, mode. "
        "Returns: ranked list of properties sorted by commute duration (shortest first)."
    )
    args_schema: type[BaseModel] = CommuteRankingInput

    _vector_store: Any = PrivateAttr()

    def __init__(self, vector_store: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_store = vector_store

    def _run(
        self,
        property_ids: str,
        destination_lat: float,
        destination_lon: float,
        mode: str = "transit",
        destination_name: Optional[str] = None,
        departure_time: Optional[str] = None,
    ) -> str:
        """
        Rank properties by commute time to destination.

        Args:
            property_ids: Comma-separated list of property IDs.
            destination_lat: Destination latitude.
            destination_lon: Destination longitude.
            mode: Travel mode - 'driving', 'walking', 'bicycling', or 'transit'.
            destination_name: Optional destination name for display.
            departure_time: Optional departure time for transit scheduling.

        Returns:
            Formatted string with ranked property commute times.
        """
        try:
            from utils.commute_client import CommuteTimeClient

            if self._vector_store is None:
                return (
                    "Commute Ranking:\n"
                    "Error: Vector store not available. Cannot retrieve property coordinates."
                )

            # Parse property IDs
            pid_list = [pid.strip() for pid in property_ids.split(",") if pid.strip()]
            if not pid_list:
                return "Error: At least one property_id is required."

            # Get property coordinates
            docs = self._vector_store.get_properties_by_ids(pid_list)
            if not docs:
                return "Error: No properties found."

            properties_lat_lon = {}
            property_titles = {}
            for doc in docs:
                md = doc.metadata or {}
                pid = str(md.get("id", ""))
                lat = md.get("lat")
                lon = md.get("lon")
                title = md.get("title")

                if pid and lat is not None and lon is not None:
                    properties_lat_lon[pid] = (float(lat), float(lon))
                    if title:
                        property_titles[pid] = title

            if not properties_lat_lon:
                return "Error: No properties with valid coordinates found."

            # Parse departure time if provided
            from datetime import datetime

            parsed_departure_time = None
            if departure_time:
                try:
                    parsed_departure_time = datetime.fromisoformat(departure_time)
                except ValueError:
                    return "Error: Invalid departure_time format. Use ISO format (e.g., '2024-01-15T08:30:00')."

            # Create client and rank properties
            client = CommuteTimeClient()

            import asyncio

            results = asyncio.run(
                client.rank_properties_by_commute(
                    property_ids=list(properties_lat_lon.keys()),
                    properties_lat_lon=properties_lat_lon,
                    destination_lat=destination_lat,
                    destination_lon=destination_lon,
                    mode=mode,
                    destination_name=destination_name,
                    departure_time=parsed_departure_time,
                )
            )

            if not results:
                return "Error: Unable to calculate commute times for any properties."

            # Format output
            dest_display = destination_name or f"({destination_lat:.4f}, {destination_lon:.4f})"
            mode_display = mode.capitalize()

            output = [
                f"Commute Ranking to {dest_display}",
                f"Mode: {mode_display}",
                "",
                f"{'Rank':<5} {'Property':<30} {'Duration':<12} {'Distance':<10}",
                f"{'-' * 5} {'-' * 30} {'-' * 12} {'-' * 10}",
            ]

            for i, result in enumerate(results, 1):
                pid = result.property_id
                title = property_titles.get(pid, pid)[:28]  # Truncate if too long
                duration = result.duration_text
                distance = result.distance_text

                output.append(f"{i:<5} {title:<30} {duration:<12} {distance:<10}")

            output.append("")
            output.append(f"Ranked {len(results)} properties by commute time.")

            # Add summary
            if results:
                fastest = results[0]
                slowest = results[-1]
                output.append("")
                output.append(f"Fastest: {fastest.duration_text}")
                output.append(f"Slowest: {slowest.duration_text}")

            return "\n".join(output)

        except Exception as e:
            return f"Commute Ranking:\nError: {str(e)}"

    async def _arun(self, **kwargs: Any) -> str:
        """Async version."""
        return self._run(**kwargs)


# Factory function to create all tools
def create_property_tools(vector_store: Any = None) -> List[BaseTool]:
    """
    Create all property-related tools.

    Args:
        vector_store: Optional vector store for data access.
                      Required for comparison, price, and location tools.

    Returns:
        List of initialized tool instances
    """
    return [
        MortgageCalculatorTool(),
        TCOCalculatorTool(),
        InvestmentCalculatorTool(),
        NeighborhoodQualityIndexTool(),
        PropertyComparisonTool(vector_store=vector_store),
        PriceAnalysisTool(vector_store=vector_store),
        LocationAnalysisTool(vector_store=vector_store),
        # TASK-021: Commute Time Analysis
        CommuteTimeAnalysisTool(vector_store=vector_store),
        CommuteRankingTool(vector_store=vector_store),
        # TASK-023: AI Listing Generator
        PropertyDescriptionGeneratorTool(),
        HeadlineGeneratorTool(),
        SocialMediaContentGeneratorTool(),
    ]
