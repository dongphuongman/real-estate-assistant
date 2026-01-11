"""
Professional HTML email templates for notifications.

Provides responsive, mobile-friendly email templates for:
- Price drop alerts
- New property matches
- Saved search matches
- Daily digests
- Weekly summaries
- Market updates
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from data.schemas import Property


class EmailTemplate:
    """Base class for email templates with common styles."""

    # Common color scheme
    COLORS = {
        "primary": "#1f77b4",
        "success": "#2ca02c",
        "warning": "#ff7f0e",
        "danger": "#d62728",
        "text": "#333333",
        "text_light": "#666666",
        "background": "#f8f9fa",
        "white": "#ffffff",
        "border": "#e0e0e0",
    }

    @staticmethod
    def _base_wrapper(title: str, content: str) -> str:
        """Wrap content in base HTML template."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
            line-height: 1.6;
            color: {EmailTemplate.COLORS['text']};
            margin: 0;
            padding: 0;
            background-color: {EmailTemplate.COLORS['background']};
        }}
        .container {{
            max-width: 600px;
            margin: 20px auto;
            background-color: {EmailTemplate.COLORS['white']};
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, {EmailTemplate.COLORS['primary']}, #1565c0);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .footer {{
            background-color: {EmailTemplate.COLORS['background']};
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: {EmailTemplate.COLORS['text_light']};
            border-top: 1px solid {EmailTemplate.COLORS['border']};
        }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            background-color: {EmailTemplate.COLORS['primary']};
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: 600;
            margin: 10px 0;
        }}
        .button:hover {{
            background-color: #1565c0;
        }}
        @media only screen and (max-width: 600px) {{
            .container {{
                margin: 10px;
                border-radius: 5px;
            }}
            .content {{
                padding: 20px 15px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 Real Estate Assistant</h1>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p>You're receiving this email because you have notifications enabled.</p>
            <p><a href="#" style="color: {EmailTemplate.COLORS['text_light']};">Manage Preferences</a> |
               <a href="#" style="color: {EmailTemplate.COLORS['text_light']};">Unsubscribe</a></p>
            <p style="margin-top: 15px;">© 2025 Real Estate Assistant. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

    @staticmethod
    def _format_amenities(prop: Property) -> str:
        """Format property amenities as HTML list."""
        amenities = []
        if prop.has_parking:
            amenities.append("🚗 Parking")
        if prop.has_garden:
            amenities.append("🌳 Garden")
        if prop.has_pool:
            amenities.append("🏊 Pool")
        if prop.is_furnished:
            amenities.append("🛋️ Furnished")
        if prop.has_balcony:
            amenities.append("🌅 Balcony")
        if prop.has_elevator:
            amenities.append("🛗 Elevator")

        if not amenities:
            return "<em>No special amenities</em>"

        return ", ".join(amenities)

    @staticmethod
    def _property_card(prop: Property, highlight_color: Optional[str] = None) -> str:
        """Generate HTML card for a property."""
        border_color = highlight_color or EmailTemplate.COLORS["border"]

        area_text = f"{prop.area_sqm} sqm" if prop.area_sqm else "Area not specified"

        return f"""
<div style="background-color: white; padding: 20px; border-radius: 8px; margin: 15px 0;
     border-left: 4px solid {border_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
    <h3 style="margin-top: 0; color: {EmailTemplate.COLORS['text']};">
        {prop.property_type} in {prop.city}
    </h3>
    <div style="font-size: 24px; font-weight: bold; color: {EmailTemplate.COLORS['primary']}; margin: 10px 0;">
        ${prop.price:,.0f}/month
    </div>
    <div style="margin: 15px 0;">
        <span style="margin-right: 15px;">🛏️ {prop.rooms} bed</span>
        <span style="margin-right: 15px;">🚿 {prop.bathrooms} bath</span>
        <span>📏 {area_text}</span>
    </div>
    <div style="margin-top: 15px;">
        <strong>Amenities:</strong><br>
        {EmailTemplate._format_amenities(prop)}
    </div>
</div>
"""


class PriceDropTemplate(EmailTemplate):
    """Template for price drop alerts."""

    @staticmethod
    def render(property_info: Dict[str, Any], user_name: Optional[str] = None) -> tuple[str, str]:
        """
        Render price drop alert email.

        Args:
            property_info: Dictionary with property, old_price, new_price, percent_drop, savings
            user_name: User's name (optional)

        Returns:
            Tuple of (subject, html_body)
        """
        prop = property_info["property"]
        old_price = property_info["old_price"]
        new_price = property_info["new_price"]
        percent_drop = property_info["percent_drop"]
        savings = property_info["savings"]

        greeting = f"Hi {user_name}," if user_name else "Hello,"

        subject = f"🔔 Price Drop Alert - {prop.city} Property"

        content = f"""
<h2 style="color: {EmailTemplate.COLORS['success']};">💰 Great News - Price Drop!</h2>
<p>{greeting}</p>
<p>A property you're watching has dropped in price. This could be a great opportunity!</p>

<div style="background-color: {EmailTemplate.COLORS['background']}; padding: 25px; border-radius: 8px; margin: 20px 0;">
    <h3 style="margin-top: 0;">{prop.property_type} in {prop.city}</h3>

    <div style="margin: 20px 0;">
        <div style="margin-bottom: 10px;">
            <strong>Previous Price:</strong>
            <span style="text-decoration: line-through; color: {EmailTemplate.COLORS['text_light']};">
                ${old_price:,.0f}/month
            </span>
        </div>
        <div style="margin-bottom: 10px;">
            <strong>New Price:</strong>
            <span style="color: {EmailTemplate.COLORS['success']}; font-size: 28px; font-weight: bold;">
                ${new_price:,.0f}/month
            </span>
        </div>
        <div style="background-color: {EmailTemplate.COLORS['success']}; color: white;
             padding: 10px 15px; border-radius: 5px; display: inline-block; margin-top: 10px;">
            <strong>You Save: ${savings:,.0f} ({percent_drop:.1f}% off)</strong>
        </div>
    </div>

    <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid {EmailTemplate.COLORS['border']};">
        <h4 style="margin-top: 0;">Property Details:</h4>
        <ul style="list-style: none; padding: 0;">
            <li>🛏️ {prop.rooms} bedrooms, 🚿 {prop.bathrooms} bathrooms</li>
            <li>📏 {prop.area_sqm if prop.area_sqm else 'N/A'} sqm</li>
            <li>🏷️ {prop.property_type}</li>
        </ul>
        <p><strong>Amenities:</strong> {EmailTemplate._format_amenities(prop)}</p>
    </div>
</div>

<div style="text-align: center; margin: 30px 0;">
    <a href="#" class="button">View Property Details</a>
</div>

<p style="color: {EmailTemplate.COLORS['text_light']}; font-size: 14px;">
    Act fast! Price drops often attract multiple interested renters.
</p>
"""

        return subject, EmailTemplate._base_wrapper(subject, content)


class NewPropertyTemplate(EmailTemplate):
    """Template for new property match alerts."""

    @staticmethod
    def render(
        search_name: str,
        properties: List[Property],
        max_display: int = 5,
        user_name: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Render new property matches email.

        Args:
            search_name: Name of the saved search
            properties: List of matching properties
            max_display: Maximum properties to display in email
            user_name: User's name (optional)

        Returns:
            Tuple of (subject, html_body)
        """
        greeting = f"Hi {user_name}," if user_name else "Hello,"
        count = len(properties)

        subject = f"🏠 {count} New {'Property' if count == 1 else 'Properties'} Match Your Search - {search_name}"

        # Build property cards HTML
        properties_html = ""
        for prop in properties[:max_display]:
            properties_html += EmailTemplate._property_card(prop, EmailTemplate.COLORS["primary"])

        if len(properties) > max_display:
            remaining = len(properties) - max_display
            properties_html += f"""
<p style="text-align: center; color: {EmailTemplate.COLORS['text_light']}; font-style: italic;">
    ...and {remaining} more {'property' if remaining == 1 else 'properties'}
</p>
"""

        content = f"""
<h2 style="color: {EmailTemplate.COLORS['primary']};">🏠 New Properties Match Your Search!</h2>
<p>{greeting}</p>
<p>We found <strong>{count}</strong> new {'property' if count == 1 else 'properties'} matching your saved search:
   <strong style="color: {EmailTemplate.COLORS['primary']};">{search_name}</strong></p>

{properties_html}

<div style="text-align: center; margin: 30px 0;">
    <a href="#" class="button">View All Matches</a>
    <a href="#" style="display: inline-block; padding: 12px 24px; color: {EmailTemplate.COLORS['text']};
       text-decoration: none; border: 1px solid {EmailTemplate.COLORS['border']}; border-radius: 5px;
       margin: 10px 5px;">Manage Searches</a>
</div>

<p style="color: {EmailTemplate.COLORS['text_light']}; font-size: 14px;">
    These properties were recently added and match your search criteria.
    Contact landlords quickly to schedule viewings.
</p>
"""

        return subject, EmailTemplate._base_wrapper(subject, content)


class DigestTemplate(EmailTemplate):
    """Template for daily/weekly digest emails."""

    @staticmethod
    def render(
        digest_type: str,  # 'daily' or 'weekly'
        data: Dict[str, Any],
        user_name: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Render digest email.

        Args:
            digest_type: 'daily' or 'weekly'
            data: Digest data (new_properties, price_drops, avg_price, etc.)
            user_name: User's name (optional)

        Returns:
            Tuple of (subject, html_body)
        """
        greeting = f"Hi {user_name}," if user_name else "Hello,"
        date_str = datetime.now().strftime("%B %d, %Y")
        period = digest_type.title()

        subject = f"📊 Your {period} Real Estate Digest - {date_str}"

        # Extract data with defaults
        new_properties = data.get("new_properties", 0)
        price_drops = data.get("price_drops", 0)
        avg_price = data.get("avg_price", 0)
        total_properties = data.get("total_properties", 0)
        average_price = data.get("average_price", 0)
        trending_cities = data.get("trending_cities", [])
        saved_searches = data.get("saved_searches", [])
        top_picks = data.get("top_picks", []) or []
        price_drop_properties = data.get("price_drop_properties", []) or []
        expert = data.get("expert")

        def _fmt_money(amount: Any, currency: Any) -> str:
            if amount is None:
                return "—"
            try:
                if currency:
                    return f"{float(amount):,.0f} {currency}"
            except Exception:
                pass
            try:
                return f"${float(amount):,.0f}"
            except Exception:
                return str(amount)

        def _fmt_number(v: Any) -> str:
            if v is None:
                return "—"
            try:
                if float(v).is_integer():
                    return str(int(float(v)))
                return f"{float(v):.1f}"
            except Exception:
                return str(v)

        def _render_property_cards(items: List[Dict[str, Any]]) -> str:
            cards = ""
            for p in items[:5]:
                city = p.get("city") or "Unknown"
                district = p.get("district")
                title = p.get("title")
                price = _fmt_money(p.get("price"), p.get("currency"))
                rooms = _fmt_number(p.get("rooms"))
                baths = _fmt_number(p.get("bathrooms"))
                area = _fmt_number(p.get("area_sqm"))
                price_per_sqm = p.get("price_per_sqm")
                pps = f"{_fmt_money(price_per_sqm, p.get('currency'))}/m²" if price_per_sqm is not None else None
                prop_type = p.get("property_type")
                listing_type = p.get("listing_type")

                amenity_bits = []
                if p.get("has_parking"):
                    amenity_bits.append("Parking")
                if p.get("has_elevator"):
                    amenity_bits.append("Elevator")
                if p.get("has_balcony"):
                    amenity_bits.append("Balcony")
                if p.get("is_furnished"):
                    amenity_bits.append("Furnished")
                amenities = ", ".join(amenity_bits) if amenity_bits else None

                meta_bits = []
                if prop_type:
                    meta_bits.append(str(prop_type).title())
                if listing_type:
                    meta_bits.append(str(listing_type).title())
                meta = " • ".join(meta_bits) if meta_bits else ""

                location = f"{city}{f' — {district}' if district else ''}"
                headline = title if title else location
                subline_bits = [location]
                if meta:
                    subline_bits.append(meta)
                subline_bits.append(f"{rooms} rooms • {baths} baths")
                if area != "—":
                    subline_bits.append(f"{area} m²")
                if pps:
                    subline_bits.append(pps)
                subline = " | ".join([b for b in subline_bits if b])

                url = p.get("source_url")
                link_style = f"color: {EmailTemplate.COLORS['primary']}; text-decoration: none;"
                cta = f'<a href="{url}" style="{link_style}">View listing</a>' if url else ""

                amenity_style = f"margin: 6px 0 0 0; color: {EmailTemplate.COLORS['text_light']}; " "font-size: 13px;"
                amenities_html = f'<p style="{amenity_style}">{amenities}</p>' if amenities else ""

                cards += f"""
    <div style="background-color: {EmailTemplate.COLORS['white']}; padding: 15px; border-radius: 8px; margin: 12px 0;
         border: 1px solid {EmailTemplate.COLORS['border']};">
        <div style="display: flex; justify-content: space-between; gap: 10px; align-items: baseline;">
            <div style="font-weight: 600;">{headline}</div>
            <div style="font-weight: 700; color: {EmailTemplate.COLORS['primary']}; white-space: nowrap;">{price}</div>
        </div>
        <div style="margin-top: 6px; color: {EmailTemplate.COLORS['text_light']}; font-size: 14px;">
            {subline}
        </div>
        {amenities_html}
        <div style="margin-top: 10px;">{cta}</div>
    </div>
"""
            return cards

        def _render_expert_table(title: str, rows: List[Dict[str, Any]]) -> str:
            if not rows:
                return ""
            cols = list(rows[0].keys())
            th_style = "text-align: left; padding: 8px; border-bottom: 1px solid " f"{EmailTemplate.COLORS['border']};"
            header = "".join([f'<th style="{th_style}">{c}</th>' for c in cols])
            body_rows = ""
            td_style = f"padding: 8px; border-bottom: 1px solid {EmailTemplate.COLORS['border']};"
            for r in rows[:10]:
                tds = []
                for c in cols:
                    v = r.get(c)
                    if isinstance(v, float):
                        tds.append(f"{v:.2f}")
                    else:
                        tds.append(str(v) if v is not None else "—")
                body_rows += "<tr>" + "".join([f'<td style="{td_style}">{cell}</td>' for cell in tds]) + "</tr>"
            return f"""
<div style="margin: 25px 0;">
    <h3>📌 {title}</h3>
    <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
            <thead><tr>{header}</tr></thead>
            <tbody>{body_rows}</tbody>
        </table>
    </div>
</div>
"""

        content = f"""
<h2 style="color: {EmailTemplate.COLORS['primary']};">📊 {period} Real Estate Digest</h2>
<p>{greeting}</p>
<p style="color: {EmailTemplate.COLORS['text_light']};">{date_str}</p>

<div style="background-color: {EmailTemplate.COLORS['background']}; padding: 25px; border-radius: 8px; margin: 25px 0;">
    <h3 style="margin-top: 0; text-align: center;">Market Summary</h3>

    <div style="display: flex; justify-content: space-around; flex-wrap: wrap; margin: 20px 0;">
        <div style="text-align: center; margin: 15px; min-width: 120px;">
            <div style="font-size: 36px; font-weight: bold; color: {EmailTemplate.COLORS['primary']};
                 margin-bottom: 5px;">
                {new_properties}
            </div>
            <div style="color: {EmailTemplate.COLORS['text_light']};">New Properties</div>
        </div>

        <div style="text-align: center; margin: 15px; min-width: 120px;">
            <div style="font-size: 36px; font-weight: bold; color: {EmailTemplate.COLORS['success']};
                 margin-bottom: 5px;">
                {price_drops}
            </div>
            <div style="color: {EmailTemplate.COLORS['text_light']};">Price Drops</div>
        </div>

        <div style="text-align: center; margin: 15px; min-width: 120px;">
            <div style="font-size: 36px; font-weight: bold; color: {EmailTemplate.COLORS['warning']};
                 margin-bottom: 5px;">
                ${avg_price:,.0f}
            </div>
            <div style="color: {EmailTemplate.COLORS['text_light']};">Avg Price</div>
        </div>
    </div>
</div>

<div style="margin: 25px 0;">
    <h3>📈 Market Statistics</h3>
    <ul style="line-height: 2;">
        <li><strong>Total Active Listings:</strong> {total_properties:,}</li>
        <li><strong>Average Price:</strong> ${average_price:,.0f}/month</li>
    </ul>
</div>
"""

        # Add trending cities if available
        if trending_cities:
            content += """
<div style="margin: 25px 0;">
    <h3>🔥 Trending Cities</h3>
    <ul style="line-height: 2;">
"""
            for city in trending_cities[:5]:
                content += f"        <li>{city}</li>\n"
            content += "    </ul>\n</div>\n"

        # Add saved searches status if available
        if saved_searches:
            content += """
<div style="margin: 25px 0;">
    <h3>🔔 Your Saved Searches</h3>
"""
            for search in saved_searches:
                search_name = search.get("name", "Unnamed Search")
                new_matches = search.get("new_matches", 0)
                match_color = EmailTemplate.COLORS["success"] if new_matches > 0 else EmailTemplate.COLORS["text_light"]

                content += f"""
    <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;
         border-left: 3px solid {match_color};">
        <strong>{search_name}</strong>
        <span style="float: right; color: {match_color}; font-weight: bold;">
            {new_matches} new {'match' if new_matches == 1 else 'matches'}
        </span>
    </div>
"""
            content += "</div>\n"

        if top_picks:
            content += """
<div style="margin: 25px 0;">
    <h3>🏆 Top Picks</h3>
"""
            content += _render_property_cards(top_picks)
            content += "</div>\n"

        if price_drop_properties:
            content += """
<div style="margin: 25px 0;">
    <h3>💸 Biggest Price Drops</h3>
"""
            drops_cards = ""
            for item in price_drop_properties[:5]:
                p = item.get("property") or {}
                city = p.get("city") or "Unknown"
                price_old = _fmt_money(item.get("old_price"), p.get("currency"))
                price_new = _fmt_money(item.get("new_price"), p.get("currency"))
                pct = item.get("percent_drop")
                pct_str = f"{float(pct):.1f}%" if pct is not None else "—"
                p_cards = _render_property_cards([p])
                drops_cards += f"""
    <div style="margin: 0 0 10px 0;">
        <div style="margin-bottom: 6px; color: {EmailTemplate.COLORS['text_light']};
             font-size: 13px;">
            {city}: {price_old} →
            <span style="color: {EmailTemplate.COLORS['success']}; font-weight: 700;">
                {price_new}
            </span>
            (<span style="color: {EmailTemplate.COLORS['success']}; font-weight: 700;">-{pct_str}</span>)
        </div>
        {p_cards}
    </div>
"""
            content += drops_cards
            content += "</div>\n"

        if expert:
            # Check for different expert data structures
            city_indices = expert.get("city_indices")
            yoy_up = expert.get("yoy_top_up")
            yoy_down = expert.get("yoy_top_down")
            market_table = expert.get("market_table")
            analysis = expert.get("analysis")

            if city_indices or yoy_up or yoy_down or market_table:
                content += """
<div style="margin: 30px 0; padding-top: 10px; border-top: 1px solid {border};">
    <h2 style="color: {primary}; margin-top: 0;">🧠 Expert Digest — Expert Market Insights</h2>
</div>
""".format(
                    border=EmailTemplate.COLORS["border"],
                    primary=EmailTemplate.COLORS["primary"],
                )

            if analysis:
                content += f"""
<div style="margin-bottom: 20px; font-style: italic; color: {EmailTemplate.COLORS['text']};">
    "{analysis}"
</div>
"""

            if market_table:
                content += _render_expert_table("Market Trends", market_table)
            
            if city_indices:
                content += _render_expert_table("City Price Indices (Top 10)", city_indices)
            
            if yoy_up:
                content += _render_expert_table("YoY — Top Gainers", yoy_up)
                
            if yoy_down:
                content += _render_expert_table("YoY — Top Decliners", yoy_down)

        content += f"""
<div style="text-align: center; margin: 30px 0;">
    <a href="#" class="button">View Dashboard</a>
</div>

<p style="color: {EmailTemplate.COLORS['text_light']}; font-size: 14px;">
    Stay informed about the latest market trends and never miss a great opportunity.
</p>
"""

        return subject, EmailTemplate._base_wrapper(subject, content)


class TestEmailTemplate(EmailTemplate):
    """Template for test emails."""

    @staticmethod
    def render(user_name: Optional[str] = None) -> tuple[str, str]:
        """
        Render test email.

        Args:
            user_name: User's name (optional)

        Returns:
            Tuple of (subject, html_body)
        """
        greeting = f"Hi {user_name}," if user_name else "Hello,"

        subject = "✅ Test Email - Real Estate Assistant"

        content = f"""
<h2 style="color: {EmailTemplate.COLORS['success']};">✅ Email Configuration Test</h2>
<p>{greeting}</p>
<p>This is a test email to verify your notification settings are working correctly.</p>

<div style="background-color: {EmailTemplate.COLORS['background']}; padding: 20px; border-radius: 8px; margin: 20px 0;">
    <h3 style="margin-top: 0;">✓ Success!</h3>
    <p>If you're reading this, your email configuration is working properly. You can now receive:</p>
    <ul>
        <li>🔔 Price drop alerts</li>
        <li>🏠 New property matches</li>
        <li>📊 Market updates and digests</li>
        <li>💾 Saved search notifications</li>
    </ul>
</div>

<div style="text-align: center; margin: 30px 0;">
    <a href="#" class="button">Manage Notification Preferences</a>
</div>

<p style="color: {EmailTemplate.COLORS['text_light']}; font-size: 14px;">
    You can customize your notification preferences at any time to control what alerts you receive and how often.
</p>
"""

        return subject, EmailTemplate._base_wrapper(subject, content)


class MarketUpdateTemplate(EmailTemplate):
    """Template for market update notifications."""

    @staticmethod
    def render(update_data: Dict[str, Any], user_name: Optional[str] = None) -> tuple[str, str]:
        """
        Render market update email.

        Args:
            update_data: Market update data (trends, insights, recommendations)
            user_name: User's name (optional)

        Returns:
            Tuple of (subject, html_body)
        """
        greeting = f"Hi {user_name}," if user_name else "Hello,"

        subject = "📈 Market Update - Real Estate Insights"

        update_title = update_data.get("title", "Market Update")
        summary = update_data.get("summary", "Latest market insights and trends.")
        insights = update_data.get("insights", [])

        content = f"""
<h2 style="color: {EmailTemplate.COLORS['primary']};">📈 {update_title}</h2>
<p>{greeting}</p>
<p>{summary}</p>

<div style="background-color: {EmailTemplate.COLORS['background']}; padding: 20px; border-radius: 8px; margin: 20px 0;">
    <h3 style="margin-top: 0;">Key Insights</h3>
"""

        for insight in insights:
            icon = insight.get("icon", "•")
            text = insight.get("text", "")
            content += f"    <p>{icon} {text}</p>\n"

        content += """
</div>

<div style="text-align: center; margin: 30px 0;">
    <a href="#" class="button">View Full Report</a>
</div>

<p style="color: {EmailTemplate.COLORS['text_light']}; font-size: 14px;">
    Stay ahead of market trends and make informed decisions with our real-time insights.
</p>
"""

        return subject, EmailTemplate._base_wrapper(subject, content)
