"""Tests for notifications.email_templates module."""

from data.schemas import Property
from notifications.email_templates import (
    AnomalyAlertTemplate,
    DigestTemplate,
    EmailTemplate,
    MarketUpdateTemplate,
    NewPropertyTemplate,
    PriceDropTemplate,
    TestEmailTemplate,
)


def _make_property(
    city="Warsaw",
    price=3500.0,
    property_type="apartment",
    rooms=3,
    bathrooms=1,
    area_sqm=65.0,
    has_parking=False,
    has_garden=False,
    has_pool=False,
    is_furnished=False,
    has_balcony=False,
    has_elevator=False,
) -> Property:
    return Property(
        id="prop-1",
        city=city,
        price=price,
        property_type=property_type,
        rooms=rooms,
        bathrooms=bathrooms,
        area_sqm=area_sqm,
        has_parking=has_parking,
        has_garden=has_garden,
        has_pool=has_pool,
        is_furnished=is_furnished,
        has_balcony=has_balcony,
        has_elevator=has_elevator,
    )


class TestBaseWrapper:
    def test_base_wrapper_contains_title(self):
        html = EmailTemplate._base_wrapper("Test Title", "<p>Content</p>")
        assert "<title>Test Title</title>" in html
        assert "<p>Content</p>" in html

    def test_base_wrapper_has_html_structure(self):
        html = EmailTemplate._base_wrapper("Title", "content")
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html


class TestFormatAmenities:
    def test_no_amenities(self):
        prop = _make_property()
        result = EmailTemplate._format_amenities(prop)
        assert "No special amenities" in result

    def test_parking(self):
        prop = _make_property(has_parking=True)
        result = EmailTemplate._format_amenities(prop)
        assert "Parking" in result

    def test_multiple_amenities(self):
        prop = _make_property(has_parking=True, has_garden=True, has_pool=True)
        result = EmailTemplate._format_amenities(prop)
        assert "Parking" in result
        assert "Garden" in result
        assert "Pool" in result

    def test_all_amenities(self):
        prop = _make_property(
            has_parking=True,
            has_garden=True,
            has_pool=True,
            is_furnished=True,
            has_balcony=True,
            has_elevator=True,
        )
        result = EmailTemplate._format_amenities(prop)
        assert "Parking" in result
        assert "Garden" in result
        assert "Pool" in result
        assert "Furnished" in result
        assert "Balcony" in result
        assert "Elevator" in result


class TestPropertyCard:
    def test_basic_card(self):
        prop = _make_property()
        html = EmailTemplate._property_card(prop)
        assert "apartment" in html
        assert "Warsaw" in html

    def test_card_with_highlight_color(self):
        prop = _make_property()
        html = EmailTemplate._property_card(prop, highlight_color="#ff0000")
        assert "#ff0000" in html

    def test_card_no_area(self):
        prop = _make_property(area_sqm=None)
        html = EmailTemplate._property_card(prop)
        assert "Area not specified" in html

    def test_card_with_area(self):
        prop = _make_property(area_sqm=75.0)
        html = EmailTemplate._property_card(prop)
        assert "75" in html


class TestPriceDropTemplate:
    def test_render_with_user(self):
        prop = _make_property()
        info = {
            "property": prop,
            "old_price": 4000.0,
            "new_price": 3500.0,
            "percent_drop": 12.5,
            "savings": 500.0,
        }
        subject, html = PriceDropTemplate.render(info, user_name="Alice")
        assert "Price Drop" in subject
        assert "Alice" in html

    def test_render_without_user(self):
        prop = _make_property()
        info = {
            "property": prop,
            "old_price": 4000.0,
            "new_price": 3500.0,
            "percent_drop": 12.5,
            "savings": 500.0,
        }
        subject, html = PriceDropTemplate.render(info)
        assert "Hello," in html
        assert isinstance(subject, str)

    def test_render_returns_tuple(self):
        prop = _make_property()
        info = {
            "property": prop,
            "old_price": 4000.0,
            "new_price": 3500.0,
            "percent_drop": 12.5,
            "savings": 500.0,
        }
        result = PriceDropTemplate.render(info)
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestNewPropertyTemplate:
    def test_single_property(self):
        prop = _make_property()
        subject, html = NewPropertyTemplate.render("My Search", [prop])
        assert "1" in subject
        assert "My Search" in html

    def test_multiple_properties(self):
        props = [_make_property(city=f"City{i}") for i in range(3)]
        subject, html = NewPropertyTemplate.render("Test", props)
        assert "3" in subject

    def test_max_display_overflow(self):
        props = [_make_property(city=f"City{i}") for i in range(7)]
        subject, html = NewPropertyTemplate.render("Test", props, max_display=5)
        assert "2 more" in html

    def test_with_user_name(self):
        prop = _make_property()
        subject, html = NewPropertyTemplate.render("Search", [prop], user_name="Bob")
        assert "Bob" in html

    def test_empty_properties(self):
        subject, html = NewPropertyTemplate.render("Search", [])
        assert "0" in subject


class TestDigestTemplate:
    def test_daily_digest(self):
        data = {
            "new_properties": 10,
            "price_drops": 5,
            "avg_price": 3500.0,
            "total_properties": 500,
            "average_price": 3200.0,
        }
        subject, html = DigestTemplate.render("daily", data, user_name="Alice")
        assert "Daily" in subject
        assert "Alice" in html
        assert "10" in html

    def test_weekly_digest(self):
        data = {
            "new_properties": 50,
            "price_drops": 20,
            "avg_price": 3400.0,
            "total_properties": 600,
            "average_price": 3100.0,
        }
        subject, html = DigestTemplate.render("weekly", data)
        assert "Weekly" in subject

    def test_with_trending_cities(self):
        data = {"trending_cities": ["Warsaw", "Krakow", "Gdansk"]}
        subject, html = DigestTemplate.render("daily", data)
        assert "Warsaw" in html
        assert "Krakow" in html

    def test_with_saved_searches(self):
        data = {
            "saved_searches": [
                {"name": "My Search", "new_matches": 3},
            ],
        }
        subject, html = DigestTemplate.render("daily", data)
        assert "My Search" in html
        assert "3 new" in html

    def test_saved_searches_zero_matches(self):
        data = {
            "saved_searches": [
                {"name": "Empty Search", "new_matches": 0},
            ],
        }
        subject, html = DigestTemplate.render("daily", data)
        assert "Empty Search" in html

    def test_with_top_picks(self):
        data = {
            "top_picks": [
                {"city": "Warsaw", "price": 3500.0, "rooms": 3, "bathrooms": 1},
            ],
        }
        subject, html = DigestTemplate.render("daily", data)
        assert "Top Picks" in html

    def test_with_price_drop_properties(self):
        data = {
            "price_drop_properties": [
                {
                    "property": {"city": "Krakow", "price": 2800.0},
                    "old_price": 3200.0,
                    "new_price": 2800.0,
                    "percent_drop": 12.5,
                },
            ],
        }
        subject, html = DigestTemplate.render("daily", data)
        assert "Biggest Price Drops" in html

    def test_with_expert_data(self):
        data = {
            "expert": {
                "analysis": "Market is trending up",
                "market_table": [{"city": "Warsaw", "price": 3500}],
                "city_indices": [{"city": "Warsaw", "index": 105.2}],
            },
        }
        subject, html = DigestTemplate.render("daily", data)
        assert "Expert" in html
        assert "Market is trending up" in html

    def test_with_expert_yoy(self):
        data = {
            "expert": {
                "yoy_top_up": [{"city": "Warsaw", "change": 12.5}],
                "yoy_top_down": [{"city": "Gdansk", "change": -5.3}],
            },
        }
        subject, html = DigestTemplate.render("daily", data)
        assert "Top Gainers" in html
        assert "Top Decliners" in html

    def test_expert_no_data(self):
        data = {"expert": None}
        subject, html = DigestTemplate.render("daily", data)
        assert "Expert Market Insights" not in html

    def test_empty_digest(self):
        data = {}
        subject, html = DigestTemplate.render("daily", data)
        assert "Daily" in subject
        assert "<!DOCTYPE html>" in html

    def test_top_picks_with_amenities(self):
        data = {
            "top_picks": [
                {
                    "city": "Warsaw",
                    "price": 3500.0,
                    "rooms": 3,
                    "bathrooms": 1,
                    "area_sqm": 65,
                    "has_parking": True,
                    "has_elevator": True,
                    "source_url": "https://example.com",
                },
            ],
        }
        subject, html = DigestTemplate.render("daily", data)
        assert "Parking" in html
        assert "View listing" in html

    def test_top_picks_with_title_and_pps(self):
        data = {
            "top_picks": [
                {
                    "city": "Warsaw",
                    "price": 3500.0,
                    "rooms": 3,
                    "bathrooms": 1,
                    "area_sqm": 65,
                    "price_per_sqm": 53.85,
                    "currency": "PLN",
                    "title": "Nice Apartment",
                    "property_type": "apartment",
                    "listing_type": "rent",
                },
            ],
        }
        subject, html = DigestTemplate.render("daily", data)
        assert "Nice Apartment" in html
        assert "Apartment" in html

    def test_expert_market_table_only(self):
        data = {
            "expert": {
                "market_table": [{"City": "Warsaw", "Price": 3500}],
            },
        }
        subject, html = DigestTemplate.render("daily", data)
        assert "Market Trends" in html

    def test_expert_city_indices_only(self):
        data = {
            "expert": {
                "city_indices": [{"city": "Warsaw", "index": 105}],
            },
        }
        subject, html = DigestTemplate.render("daily", data)
        assert "City Price Indices" in html


class TestTestEmailTemplate:
    def test_render_with_user(self):
        subject, html = TestEmailTemplate.render(user_name="Alice")
        assert "Test Email" in subject
        assert "Alice" in html

    def test_render_without_user(self):
        subject, html = TestEmailTemplate.render()
        assert "Hello," in html
        assert "<!DOCTYPE html>" in html


class TestAnomalyAlertTemplate:
    def test_basic_anomaly(self):
        data = {
            "anomaly_type": "price_spike",
            "severity": "high",
            "scope_type": "property",
            "scope_id": "prop-1",
            "metric_name": "price",
            "expected_value": 3000.0,
            "actual_value": 5000.0,
            "deviation_percent": 66.7,
        }
        subject, html = AnomalyAlertTemplate.render(data, user_name="Admin")
        assert "Anomaly" in subject
        assert "Admin" in html
        assert "HIGH" in html

    def test_critical_severity(self):
        data = {
            "severity": "critical",
            "expected_value": 1000.0,
            "actual_value": 5000.0,
            "deviation_percent": 400.0,
        }
        subject, html = AnomalyAlertTemplate.render(data)
        assert "CRITICAL" in html

    def test_with_z_score(self):
        data = {
            "z_score": 3.5,
            "expected_value": 3000.0,
            "actual_value": 5000.0,
            "deviation_percent": 66.7,
        }
        subject, html = AnomalyAlertTemplate.render(data)
        assert "3.50" in html

    def test_all_severity_levels(self):
        for severity in ["low", "medium", "high", "critical"]:
            data = {
                "severity": severity,
                "expected_value": 1000.0,
                "actual_value": 2000.0,
                "deviation_percent": 100.0,
            }
            subject, html = AnomalyAlertTemplate.render(data)
            assert severity.upper() in html

    def test_all_anomaly_types(self):
        for atype in [
            "price_spike",
            "price_drop",
            "volume_spike",
            "volume_drop",
            "unusual_pattern",
        ]:
            data = {
                "anomaly_type": atype,
                "expected_value": 1000.0,
                "actual_value": 2000.0,
                "deviation_percent": 100.0,
            }
            subject, html = AnomalyAlertTemplate.render(data)
            assert "<!DOCTYPE html>" in html

    def test_large_values_formatting(self):
        data = {
            "expected_value": 1500000.0,
            "actual_value": 2500000.0,
            "deviation_percent": 66.7,
        }
        subject, html = AnomalyAlertTemplate.render(data)
        assert "1.5M" in html or "2.5M" in html

    def test_negative_deviation(self):
        data = {
            "expected_value": 3000.0,
            "actual_value": 1500.0,
            "deviation_percent": -50.0,
        }
        subject, html = AnomalyAlertTemplate.render(data)
        assert "↓" in html

    def test_detected_at(self):
        data = {
            "expected_value": 1000.0,
            "actual_value": 2000.0,
            "deviation_percent": 100.0,
            "detected_at": "2025-01-01",
            "algorithm": "zscore",
        }
        subject, html = AnomalyAlertTemplate.render(data)
        assert "2025-01-01" in html
        assert "zscore" in html


class TestMarketUpdateTemplate:
    def test_basic_update(self):
        data = {
            "title": "Q1 Market Report",
            "summary": "Market is growing",
            "insights": [
                {"icon": "📈", "text": "Prices up 5%"},
            ],
        }
        subject, html = MarketUpdateTemplate.render(data, user_name="Alice")
        assert "Market Update" in subject
        assert "Alice" in html
        assert "Q1 Market Report" in html

    def test_without_user(self):
        data = {"title": "Update", "summary": "Summary text"}
        subject, html = MarketUpdateTemplate.render(data)
        assert "Hello," in html

    def test_empty_insights(self):
        data = {"insights": []}
        subject, html = MarketUpdateTemplate.render(data)
        assert "<!DOCTYPE html>" in html

    def test_default_title(self):
        data = {}
        subject, html = MarketUpdateTemplate.render(data)
        assert "Market Update" in html


class TestColors:
    def test_colors_defined(self):
        assert "primary" in EmailTemplate.COLORS
        assert "success" in EmailTemplate.COLORS
        assert "danger" in EmailTemplate.COLORS
        assert "text" in EmailTemplate.COLORS
        assert "background" in EmailTemplate.COLORS
