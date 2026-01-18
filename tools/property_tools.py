"""
Property-specific tools for the agent.

This module provides specialized tools for property analysis, comparison,
and calculations.
"""

import math
import statistics
from typing import Any, Dict, List

from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

# We use Any for vector_store to avoid circular imports/tight coupling
# expected type: vector_store.chroma_store.ChromaPropertyStore


class MortgageInput(BaseModel):
    """Input for mortgage calculator."""
    property_price: float = Field(description="Total property price")
    down_payment_percent: float = Field(
        default=20.0,
        description="Down payment as percentage (e.g., 20 for 20%)"
    )
    interest_rate: float = Field(
        default=4.5,
        description="Annual interest rate as percentage (e.g., 4.5 for 4.5%)"
    )
    loan_years: int = Field(default=30, description="Loan term in years")


class MortgageResult(BaseModel):
    """Result from mortgage calculator."""
    monthly_payment: float
    total_interest: float
    total_cost: float
    down_payment: float
    loan_amount: float
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
        loan_years: int = 30
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
                loan_amount
                * monthly_rate
                * math.pow(1 + monthly_rate, num_payments)
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
                "down_payment": down_payment
            }
        )

    def _run(
        self,
        property_price: float,
        down_payment_percent: float = 20.0,
        interest_rate: float = 4.5,
        loan_years: int = 30
    ) -> str:
        """Execute mortgage calculation."""
        try:
            result = self.calculate(
                property_price, 
                down_payment_percent, 
                interest_rate, 
                loan_years
            )

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


class PropertyComparisonTool(BaseTool):
    """Tool for comparing properties side-by-side."""

    name: str = "property_comparator"
    description: str = (
        "Compare multiple properties based on various criteria. "
        "Input should be a comma-separated list of property IDs (e.g., 'prop1, prop2'). "
        "Returns a detailed comparison table."
    )
    
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
                "price", "price_per_sqm", "city", "rooms", "bathrooms", 
                "area_sqm", "year_built", "property_type"
            ]
            
            # Header
            header = f"{'Feature':<20} | " + " | ".join([f"{d.metadata.get('id', 'Unknown')[:10]:<15}" for d in docs])
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
            prices = [d.metadata.get("price", 0) for d in docs if isinstance(d.metadata.get("price"), (int, float))]
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
        PropertyComparisonTool(vector_store=vector_store),
        PriceAnalysisTool(vector_store=vector_store),
        LocationAnalysisTool(vector_store=vector_store),
    ]
