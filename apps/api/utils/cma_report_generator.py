"""Comparative Market Analysis (CMA) report generator.

Generates professional PDF reports for property valuation including
comparable properties, adjustments, and final valuation estimate.
"""

import logging
from datetime import datetime
from io import BytesIO
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


# Color palette for professional reports (matching InvestmentReportGenerator)
COLOR_HEADER = colors.HexColor("#1a365d")  # Deep blue
COLOR_SUBHEADER = colors.HexColor("#2c5282")  # Medium blue
COLOR_POSITIVE = colors.HexColor("#22543d")  # Green
COLOR_NEGATIVE = colors.HexColor("#742a2a")  # Red
COLOR_NEUTRAL = colors.HexColor("#4a5568")  # Gray
COLOR_LIGHT_BG = colors.HexColor("#ebf8ff")  # Light blue
COLOR_HIGHLIGHT = colors.HexColor("#faf089")  # Light yellow


class CMAReportGenerator:
    """Generate CMA reports in PDF format."""

    def __init__(self):
        """Initialize the report generator."""
        self.styles = getSampleStyleSheet()
        self._add_custom_styles()

    def _add_custom_styles(self):
        """Add custom paragraph styles for the report."""
        self.styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=self.styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=24,
                textColor=COLOR_HEADER,
                spaceAfter=12,
                alignment=1,  # Center
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=16,
                textColor=COLOR_SUBHEADER,
                spaceBefore=12,
                spaceAfter=8,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SubsectionHeader",
                parent=self.styles["Heading3"],
                fontName="Helvetica-Bold",
                fontSize=12,
                textColor=COLOR_NEUTRAL,
                spaceBefore=8,
                spaceAfter=4,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="MetricLabel",
                parent=self.styles["Normal"],
                fontName="Helvetica",
                fontSize=10,
                textColor=COLOR_NEUTRAL,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="MetricValue",
                parent=self.styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="AddressText",
                parent=self.styles["Normal"],
                fontName="Helvetica",
                fontSize=14,
                textColor=COLOR_HEADER,
                alignment=1,  # Center
            )
        )

    def generate(
        self,
        subject_data: dict[str, Any],
        comparables: list[dict[str, Any]],
        valuation: dict[str, Any],
        market_context: Optional[dict[str, Any]] = None,
    ) -> bytes:
        """
        Generate PDF report for CMA.

        Args:
            subject_data: Subject property details
            comparables: List of comparable properties with adjustments
            valuation: Final valuation with range and confidence
            market_context: Optional market context data

        Returns:
            PDF file as bytes
        """
        output = BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )
        story = []

        # Cover page / Header
        story.extend(self._build_header(subject_data))
        story.append(Spacer(1, 0.3 * inch))

        # Executive summary
        story.extend(self._build_executive_summary(valuation, subject_data))
        story.append(Spacer(1, 0.2 * inch))

        # Subject property details
        story.extend(self._build_subject_section(subject_data))
        story.append(Spacer(1, 0.2 * inch))

        # Comparables grid
        story.extend(self._build_comparables_section(comparables))

        # Adjustments table (new page if many comparables)
        if len(comparables) > 3:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 0.2 * inch))
        story.extend(self._build_adjustments_section(comparables))

        # Market context
        if market_context:
            story.append(Spacer(1, 0.2 * inch))
            story.extend(self._build_market_context_section(market_context))

        # Methodology notes
        story.append(Spacer(1, 0.2 * inch))
        story.extend(self._build_methodology_section())

        # Footer with disclaimer
        story.append(Spacer(1, 0.3 * inch))
        story.extend(self._build_footer())

        doc.build(story)
        output.seek(0)
        return output.read()

    def _build_header(self, subject_data: dict[str, Any]) -> list:
        """Build report header section."""
        story = []

        # Main title
        story.append(Paragraph("Comparative Market Analysis", self.styles["ReportTitle"]))
        story.append(Spacer(1, 0.1 * inch))

        # Property address
        address = self._format_address(subject_data)
        if address:
            story.append(Paragraph(address, self.styles["AddressText"]))
            story.append(Spacer(1, 0.1 * inch))

        # Timestamp
        timestamp = datetime.now().strftime("%B %d, %Y")
        story.append(Paragraph(f"<i>Prepared on {timestamp}</i>", self.styles["Normal"]))

        return story

    def _build_executive_summary(
        self,
        valuation: dict[str, Any],
        subject_data: dict[str, Any],
    ) -> list:
        """Build executive summary section with valuation."""
        story = []

        story.append(Paragraph("Executive Summary", self.styles["SectionHeader"]))

        estimated_value = valuation.get("estimated_value", 0)
        value_low = valuation.get("value_range_low", 0)
        value_high = valuation.get("value_range_high", 0)
        confidence = valuation.get("confidence_score", 0) * 100

        # Main valuation box
        summary_data = [
            ["Estimated Market Value", f"€{estimated_value:,.0f}"],
            ["Value Range", f"€{value_low:,.0f} - €{value_high:,.0f}"],
            ["Confidence Score", f"{confidence:.0f}%"],
        ]

        # Add price per sqm if available
        price_per_sqm = valuation.get("price_per_sqm", 0)
        if price_per_sqm > 0:
            summary_data.append(["Price per m²", f"€{price_per_sqm:,.0f}"])

        summary_table = Table(summary_data, colWidths=[2.5 * inch, 2.5 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 15),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 15),
                    ("BOX", (0, 0), (-1, -1), 1, COLOR_HEADER),
                ]
            )
        )

        story.append(summary_table)

        # Confidence interpretation
        if confidence >= 80:
            interpretation = "High confidence - Multiple strong comparables available"
        elif confidence >= 60:
            interpretation = "Moderate confidence - Consider additional verification"
        else:
            interpretation = "Low confidence - Limited comparable data available"

        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(f"<i>{interpretation}</i>", self.styles["Normal"]))

        return story

    def _build_subject_section(self, subject_data: dict[str, Any]) -> list:
        """Build subject property details section."""
        story = []

        story.append(Paragraph("Subject Property", self.styles["SectionHeader"]))

        # Property details table
        details_data = [
            ["Property Details", ""],
            ["Property Type", self._format_property_type(subject_data.get("property_type", "N/A"))],
            ["Listing Type", subject_data.get("listing_type", "N/A").title()],
            [
                "Area",
                f"{subject_data.get('area_sqm', 'N/A')} m²"
                if subject_data.get("area_sqm")
                else "N/A",
            ],
            [
                "Rooms",
                str(subject_data.get("rooms", "N/A")) if subject_data.get("rooms") else "N/A",
            ],
            [
                "Bedrooms",
                str(subject_data.get("bedrooms", "N/A")) if subject_data.get("bedrooms") else "N/A",
            ],
            [
                "Bathrooms",
                str(subject_data.get("bathrooms", "N/A"))
                if subject_data.get("bathrooms")
                else "N/A",
            ],
            [
                "Year Built",
                str(subject_data.get("year_built", "N/A"))
                if subject_data.get("year_built")
                else "N/A",
            ],
            [
                "Floor",
                f"{subject_data.get('floor', 'N/A')}/{subject_data.get('total_floors', '')}"
                if subject_data.get("floor")
                else "N/A",
            ],
            ["Energy Rating", subject_data.get("energy_rating", "N/A") or "N/A"],
        ]

        details_table = Table(details_data, colWidths=[2 * inch, 3 * inch])
        details_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        story.append(details_table)

        # Amenities section
        amenities = self._get_amenities_list(subject_data)
        if amenities:
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph("Amenities", self.styles["SubsectionHeader"]))
            story.append(Paragraph(", ".join(amenities), self.styles["Normal"]))

        return story

    def _build_comparables_section(self, comparables: list[dict[str, Any]]) -> list:
        """Build comparables grid section."""
        story = []

        story.append(Paragraph("Comparable Properties", self.styles["SectionHeader"]))
        story.append(
            Paragraph(
                f"<i>{len(comparables)} comparable properties identified</i>",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        # Comparables summary table
        comp_data = [["#", "Address", "Area", "Original Price", "Adjusted Price", "Score"]]

        for i, comp in enumerate(comparables, 1):
            address = self._format_address(comp, short=True)
            area = f"{comp.get('area_sqm', 'N/A')} m²" if comp.get("area_sqm") else "N/A"

            # Get original price from adjustments or directly
            original_price = comp.get("original_price", comp.get("price", 0))
            adjusted_price = comp.get("adjusted_price", 0)
            score = comp.get("similarity_score", 0)

            comp_data.append(
                [
                    str(i),
                    address[:30] + "..." if len(address) > 30 else address,
                    area,
                    f"€{original_price:,.0f}" if original_price else "N/A",
                    f"€{adjusted_price:,.0f}" if adjusted_price else "N/A",
                    f"{score:.0f}",
                ]
            )

        comp_table = Table(
            comp_data,
            colWidths=[0.3 * inch, 1.8 * inch, 0.8 * inch, 1 * inch, 1 * inch, 0.5 * inch],
        )
        comp_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        story.append(comp_table)

        return story

    def _build_adjustments_section(self, comparables: list[dict[str, Any]]) -> list:
        """Build adjustments breakdown section."""
        story = []

        story.append(Paragraph("Adjustments Breakdown", self.styles["SectionHeader"]))
        story.append(
            Paragraph(
                "<i>Detailed adjustments applied to each comparable property</i>",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        for i, comp in enumerate(comparables, 1):
            address = self._format_address(comp, short=True)
            story.append(Paragraph(f"Comparable #{i}: {address}", self.styles["SubsectionHeader"]))

            adjustments = comp.get("adjustments", [])
            if not adjustments:
                story.append(Paragraph("No adjustments applied", self.styles["Normal"]))
                continue

            # Adjustments table
            adj_data = [["Category", "Description", "Adjustment", "Confidence"]]

            total_percent = 0
            for adj in adjustments:
                category = adj.get("category", "N/A").title()
                description = adj.get("description", "")
                percent = adj.get("adjustment_percent", 0)
                confidence = adj.get("confidence", 1.0) * 100

                total_percent += percent

                # Format adjustment string
                if percent > 0:
                    adj_str = f"+{percent:.1f}%"
                elif percent < 0:
                    adj_str = f"{percent:.1f}%"
                else:
                    adj_str = "0.0%"

                adj_data.append(
                    [
                        category,
                        description[:40] + "..." if len(description) > 40 else description,
                        adj_str,
                        f"{confidence:.0f}%",
                    ]
                )

            # Total row
            adj_data.append(["", "TOTAL ADJUSTMENT", f"{total_percent:+.1f}%", ""])

            adj_table = Table(adj_data, colWidths=[1 * inch, 2.5 * inch, 0.8 * inch, 0.7 * inch])
            adj_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), COLOR_SUBHEADER),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, COLOR_LIGHT_BG]),
                        ("BACKGROUND", (0, -1), (-1, -1), COLOR_HIGHLIGHT),
                        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )

            story.append(adj_table)
            story.append(Spacer(1, 0.1 * inch))

        return story

    def _build_market_context_section(self, market_context: dict[str, Any]) -> list:
        """Build market context section."""
        story = []

        story.append(Paragraph("Market Context", self.styles["SectionHeader"]))

        context_data = [["Metric", "Value"]]

        if "avg_price_per_sqm" in market_context:
            context_data.append(
                ["Average Price/m²", f"€{market_context['avg_price_per_sqm']:,.0f}"]
            )

        if "median_price" in market_context:
            context_data.append(["Median Price", f"€{market_context['median_price']:,.0f}"])

        if "trend" in market_context:
            trend = market_context["trend"]
            trend_str = f"+{trend:.1f}%" if trend > 0 else f"{trend:.1f}%"
            context_data.append(["Market Trend", trend_str])

        if "inventory_count" in market_context:
            context_data.append(["Active Listings", str(market_context["inventory_count"])])

        if len(context_data) > 1:
            context_table = Table(context_data, colWidths=[2 * inch, 2 * inch])
            context_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
                        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(context_table)

        return story

    def _build_methodology_section(self) -> list:
        """Build methodology notes section."""
        story = []

        story.append(Paragraph("Methodology", self.styles["SectionHeader"]))

        methodology_text = """
        <b>Comparable Selection:</b> Properties are selected based on a multi-factor scoring
        system considering location (25%), property type (20%), size (15%), room count (15%),
        listing recency (15%), and amenity overlap (10%).
        <br/><br/>
        <b>Adjustment Calculations:</b> Adjustments are based on hedonic pricing coefficients
        derived from market data. Categories include location price indices, size scaling,
        age depreciation (0.5% per year from 2000 baseline), energy rating premiums/discounts,
        individual amenity values, floor level adjustments, and market timing corrections.
        <br/><br/>
        <b>Valuation Method:</b> The final estimated value is a weighted average of adjusted
        comparable prices, with weights based on similarity scores. The value range represents
        ±10% from the estimate. Confidence scores reflect the number and quality of comparables
        and price consistency.
        """

        story.append(Paragraph(methodology_text, self.styles["Normal"]))

        return story

    def _build_footer(self) -> list:
        """Build report footer with disclaimer."""
        story = []

        disclaimer = (
            "<i>This Comparative Market Analysis is for informational purposes only and does not "
            "constitute an appraisal or formal property valuation. The estimates provided are based "
            "on available market data and may not reflect actual market conditions. Please consult "
            "with a licensed appraiser or real estate professional for official valuations.</i>"
        )

        story.append(Paragraph(disclaimer, self.styles["Normal"]))

        return story

    def _format_address(self, data: dict[str, Any], short: bool = False) -> str:
        """Format property address for display."""
        parts = []

        if data.get("street"):
            parts.append(data["street"])

        if data.get("neighborhood") and not short:
            parts.append(data["neighborhood"])

        if data.get("district"):
            parts.append(data["district"])

        if data.get("city"):
            parts.append(data["city"])

        return ", ".join(parts) if parts else "Address not available"

    def _format_property_type(self, prop_type: str) -> str:
        """Format property type for display."""
        type_map = {
            "apartment": "Apartment",
            "house": "House",
            "studio": "Studio",
            "loft": "Loft",
            "townhouse": "Townhouse",
            "villa": "Villa",
            "penthouse": "Penthouse",
            "other": "Other",
        }
        return type_map.get(prop_type.lower(), prop_type.title())

    def _get_amenities_list(self, data: dict[str, Any]) -> list[str]:
        """Get list of amenities from property data."""
        amenities = []

        amenity_map = {
            "has_parking": "Parking",
            "has_garden": "Garden",
            "has_elevator": "Elevator",
            "has_balcony": "Balcony",
            "is_furnished": "Furnished",
            "has_pool": "Pool",
            "has_garage": "Garage",
            "pets_allowed": "Pets Allowed",
            "has_bike_room": "Bike Room",
        }

        for key, label in amenity_map.items():
            if data.get(key):
                amenities.append(label)

        return amenities
