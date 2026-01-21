from unittest.mock import patch

from langchain_core.documents import Document

from tools.property_tools import MortgageCalculatorTool, PriceAnalysisTool, PropertyComparisonTool


def test_mortgage_calculator_tool_handles_value_error():
    tool = MortgageCalculatorTool()
    out = tool._run(property_price=0)
    assert out.startswith("Error:")


def test_mortgage_calculator_tool_handles_unexpected_error():
    tool = MortgageCalculatorTool()
    with patch.object(MortgageCalculatorTool, "calculate", side_effect=RuntimeError("boom")):
        out = tool._run(property_price=100000)
    assert out.startswith("Error calculating mortgage:")


def test_property_comparison_tool_handles_missing_store_and_empty_ids():
    tool = PropertyComparisonTool(vector_store=None)
    out = tool._run("p1")
    assert "Provide a comma-separated list of property IDs" in out

    tool2 = PropertyComparisonTool(vector_store=object())
    out2 = tool2._run(" , ")
    assert "Please provide at least one property ID" in out2


def test_property_comparison_tool_handles_store_without_id_retrieval():
    tool = PropertyComparisonTool(vector_store=object())
    out = tool._run("p1")
    assert "does not support retrieving by IDs" in out


def test_property_comparison_tool_handles_no_docs_and_formats_values():
    class StoreEmpty:
        def get_properties_by_ids(self, ids):
            return []

    tool = PropertyComparisonTool(vector_store=StoreEmpty())
    out = tool._run("p1")
    assert "No properties found" in out

    class Store:
        def get_properties_by_ids(self, ids):
            return [
                Document(page_content="", metadata={"id": "p1", "price": 1000, "price_per_sqm": 20, "area_sqm": 50}),
                Document(page_content="", metadata={"id": "p2", "price": 2000, "price_per_sqm": 40, "area_sqm": 60}),
            ]

    tool2 = PropertyComparisonTool(vector_store=Store())
    out2 = tool2._run("p1, p2")
    assert "$1,000" in out2
    assert "/m²" in out2
    assert "Price difference" in out2


def test_price_analysis_tool_handles_empty_results_and_missing_prices():
    tool = PriceAnalysisTool(vector_store=None)
    out = tool._run("warsaw")
    assert "Provide a data source" in out

    class StoreEmpty:
        def search(self, query, k=20):
            return []

    tool2 = PriceAnalysisTool(vector_store=StoreEmpty())
    out2 = tool2._run("warsaw")
    assert "No properties found" in out2

    class StoreNoPrices:
        def search(self, query, k=20):
            return [(Document(page_content="", metadata={"price": "bad"}), 0.5)]

    tool3 = PriceAnalysisTool(vector_store=StoreNoPrices())
    out3 = tool3._run("warsaw")
    assert "no price data available" in out3.lower()
