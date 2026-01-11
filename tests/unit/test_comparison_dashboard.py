"""
Tests for property comparison dashboard module.
"""

import pytest
from unittest.mock import MagicMock, patch
from ui.comparison_dashboard import display_comparison_dashboard, display_compact_comparison, _display_property_card, _get_property_pros, _get_property_cons, _export_comparison_markdown
from data.schemas import Property, PropertyType
from ui.comparison_viz import PropertyComparison

@pytest.fixture
def comparison_properties():
    """Create sample properties for comparison testing."""
    return [
        Property(
            id="comp1",
            city="Krakow",
            rooms=2,
            bathrooms=1,
            price=850,
            area_sqm=50,
            has_parking=True,
            has_garden=False,
            has_pool=False,
            is_furnished=False,
            has_balcony=True,
            has_elevator=False,
            property_type=PropertyType.APARTMENT
        ),
        Property(
            id="comp2",
            city="Warsaw",
            rooms=3,
            bathrooms=2,
            price=1400,
            area_sqm=75,
            has_parking=True,
            has_garden=True,
            has_pool=False,
            is_furnished=True,
            has_balcony=True,
            has_elevator=True,
            property_type=PropertyType.APARTMENT
        ),
        Property(
            id="comp3",
            city="Gdansk",
            rooms=1,
            bathrooms=1,
            price=600,
            area_sqm=35,
            has_parking=False,
            has_garden=False,
            has_pool=False,
            is_furnished=False,
            has_balcony=False,
            has_elevator=False,
            property_type=PropertyType.STUDIO
        ),
    ]

@patch('ui.comparison_dashboard.st')
@patch('ui.comparison_dashboard.create_property_radar_chart')
@patch('ui.comparison_dashboard.create_amenity_radar_chart')
@patch('ui.comparison_dashboard.create_price_comparison_chart')
def test_display_comparison_dashboard_basic(mock_price_chart, mock_amenity_chart, mock_radar_chart, mock_st, comparison_properties):
    """Test basic dashboard display with valid properties."""
    # Setup mocks
    mock_radar_chart.return_value = MagicMock()
    mock_amenity_chart.return_value = MagicMock()
    mock_price_chart.return_value = MagicMock()
    
    # Configure st.columns to return list of mocks based on input
    def columns_side_effect(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [MagicMock() for _ in range(count)]
    mock_st.columns.side_effect = columns_side_effect
    
    # Configure st.tabs
    def tabs_side_effect(spec):
        return [MagicMock() for _ in spec]
    mock_st.tabs.side_effect = tabs_side_effect
    
    # Run function
    display_comparison_dashboard(comparison_properties)
    
    # Verify calls
    assert mock_st.markdown.called
    assert mock_st.columns.called
    assert mock_st.metric.called
    assert mock_st.plotly_chart.called
    assert mock_st.dataframe.called
    
    # Verify charts created
    mock_radar_chart.assert_called_once()
    mock_amenity_chart.assert_called_once()
    mock_price_chart.assert_called_once()

@patch('ui.comparison_dashboard.st')
def test_display_comparison_dashboard_validation(mock_st, comparison_properties):
    """Test validation logic in dashboard."""
    # Too few properties
    display_comparison_dashboard([comparison_properties[0]])
    mock_st.warning.assert_called_with("Please select at least 2 properties to compare")
    
    # No properties
    display_comparison_dashboard([])
    mock_st.warning.assert_called_with("No properties selected for comparison")
    
    # Too many properties (should trim but not fail)
    # comparison_viz now allows 6, dashboard trims to 6.
    # So if we pass 9, dashboard trims to 6, comparison_viz accepts 6.
    # We need to mock columns for the successful run after trim
    def columns_side_effect(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [MagicMock() for _ in range(count)]
    mock_st.columns.side_effect = columns_side_effect
    
    # Configure st.tabs
    def tabs_side_effect(spec):
        return [MagicMock() for _ in spec]
    mock_st.tabs.side_effect = tabs_side_effect

    many_props = comparison_properties * 3  # 9 properties
    display_comparison_dashboard(many_props)
    # It should warn about max 6
    mock_st.warning.assert_called_with("Maximum 6 properties can be compared at once")

@patch('ui.comparison_dashboard.st')
def test_display_compact_comparison(mock_st, comparison_properties):
    """Test compact comparison view."""
    # Configure st.columns
    def columns_side_effect(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [MagicMock() for _ in range(count)]
    mock_st.columns.side_effect = columns_side_effect

    display_compact_comparison(comparison_properties)
    
    assert mock_st.columns.called
    assert mock_st.metric.called
    assert mock_st.success.called

def test_get_property_pros_cons(comparison_properties):
    """Test pros and cons generation."""
    prop2 = comparison_properties[1]  # Warsaw, 1400, 3 rooms (most expensive, most rooms)
    
    pros = _get_property_pros(prop2, comparison_properties)
    cons = _get_property_cons(prop2, comparison_properties)
    
    # Prop2 is most expensive, has most rooms, most amenities
    # Note: rooms might be float in output if property schema defines it as float or if python auto-converts
    # The error showed 'Most rooms (3.0)'
    assert any("Most rooms" in p for p in pros)
    assert any("Most amenities" in p for p in pros)
    assert any("Above average price" in c for c in cons)

def test_export_comparison_markdown(comparison_properties):
    """Test markdown export generation."""
    comparison = PropertyComparison(comparison_properties)
    md = _export_comparison_markdown(comparison_properties, comparison)
    
    assert "# Property Comparison Report" in md
    assert "## Price Overview" in md
    assert "## Best Value" in md
    assert "Krakow" in md
    assert "Warsaw" in md

@patch('ui.comparison_dashboard.st')
def test_display_property_card(mock_st, comparison_properties):
    """Test property card display."""
    _display_property_card(comparison_properties[0], 1)
    
    assert mock_st.markdown.called
    # Check if amenities are rendered
    assert "🚗" in mock_st.markdown.call_args_list[-1][0][0]  # Parking icon
