from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from tools.property_tools import (
    LocationAnalysisTool,
    MortgageCalculatorTool,
    PriceAnalysisTool,
    PropertyComparisonTool,
    create_property_tools,
)


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    
    # Mock get_properties_by_ids
    def get_by_ids(ids):
        docs = []
        for pid in ids:
            if pid == "prop1":
                docs.append(Document(
                    page_content="Prop 1 Desc",
                    metadata={
                        "id": "prop1", 
                        "price": 500000, 
                        "city": "Madrid",
                        "lat": 40.4168,
                        "lon": -3.7038
                    }
                ))
            elif pid == "prop2":
                docs.append(Document(
                    page_content="Prop 2 Desc",
                    metadata={
                        "id": "prop2", 
                        "price": 600000, 
                        "city": "Madrid",
                        "lat": 40.4200,
                        "lon": -3.7000
                    }
                ))
        return docs
    store.get_properties_by_ids.side_effect = get_by_ids
    
    # Mock search
    def search(query, k=5):
        return [
            (Document(page_content="D1", metadata={"price": 100000, "property_type": "Apartment"}), 0.9),
            (Document(page_content="D2", metadata={"price": 200000, "property_type": "House"}), 0.8),
            (Document(page_content="D3", metadata={"price": 150000, "property_type": "Apartment"}), 0.7),
        ]
    store.search.side_effect = search
    
    return store

def test_create_property_tools(mock_vector_store):
    tools = create_property_tools(mock_vector_store)
    assert len(tools) == 4
    assert isinstance(tools[0], MortgageCalculatorTool)
    assert isinstance(tools[1], PropertyComparisonTool)
    assert isinstance(tools[2], PriceAnalysisTool)
    assert isinstance(tools[3], LocationAnalysisTool)

def test_mortgage_tool():
    tool = MortgageCalculatorTool()
    # Test valid calculation
    result = tool._run(property_price=100000, down_payment_percent=20, interest_rate=5, loan_years=30)
    assert "Mortgage Calculation for $100,000.00" in result
    assert "Monthly Payment: $" in result
    
    # Test invalid input
    result_err = tool._run(property_price=-100)
    assert "Error:" in result_err

def test_comparison_tool(mock_vector_store):
    tool = PropertyComparisonTool(vector_store=mock_vector_store)
    result = tool._run("prop1, prop2")
    
    assert "Property Comparison:" in result
    assert "prop1" in result
    assert "prop2" in result
    assert "$500,000" in result
    assert "$600,000" in result
    assert "Price difference: $100,000" in result

def test_price_analysis_tool(mock_vector_store):
    tool = PriceAnalysisTool(vector_store=mock_vector_store)
    result = tool._run("apartments in madrid")
    
    assert "Price Analysis for 'apartments in madrid'" in result
    assert "Average: $150,000.00" in result  # (100+200+150)/3
    assert "Median: $150,000.00" in result
    assert "Min: $100,000.00" in result
    assert "Max: $200,000.00" in result
    assert "Apartment: 2" in result
    assert "House: 1" in result

def test_location_analysis_tool(mock_vector_store):
    tool = LocationAnalysisTool(vector_store=mock_vector_store)
    result = tool._run("prop1")
    
    assert "Location Analysis for Property prop1" in result
    assert "City: Madrid" in result
    assert "Coordinates: 40.4168, -3.7038" in result
