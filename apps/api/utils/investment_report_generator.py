"""Investment analysis report generator.

Generates professional PDF and markdown reports for real estate investment analysis.
Includes key metrics, cash flow breakdowns, and investment scoring.
"""

import logging
from datetime import datetime
from io import BytesIO
from typing import Optional

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

from analytics.investment_analytics import CashFlowProjection

logger = logging.getLogger(__name__)


# Color palette for professional reports
COLOR_HEADER = colors.HexColor("#1a365d")  # Deep blue
COLOR_SUBHEADER = colors.HexColor("#2c5282")  # Medium blue
COLOR_POSITIVE = colors.HexColor("#22543d")  # Green
COLOR_NEGATIVE = colors.HexColor("#742a2a")  # Red
COLOR_NEUTRAL = colors.HexColor("#4a5568")  # Gray
COLOR_LIGHT_BG = colors.HexColor("#ebf8ff")  # Light blue


class InvestmentReportGenerator:
    """Generate investment analysis reports in PDF and markdown formats."""

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

    def generate_pdf(
        self,
        result: dict,
        projection: Optional[CashFlowProjection] = None
    ) -> bytes:
        """
        Generate PDF report with investment metrics and projections.

        Args:
            result: InvestmentAnalysisResult as dict
            projection: Optional CashFlowProjection for multi-year analysis

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

        # Title page header
        story.extend(self._build_header(result))
        story.append(Spacer(1, 0.2 * inch))

        # Key metrics summary
        story.extend(self._build_key_metrics_section(result))
        story.append(Spacer(1, 0.2 * inch))

        # Cash flow breakdown
        story.extend(self._build_cash_flow_section(result))
        story.append(Spacer(1, 0.2 * inch))

        # Investment score
        story.extend(self._build_investment_score_section(result))
        story.append(Spacer(1, 0.2 * inch))

        # Monthly breakdown table
        story.extend(self._build_monthly_breakdown_table(result))

        # Add projection if available
        if projection:
            story.append(PageBreak())
            story.extend(self._build_projection_section(projection))

        # Footer with timestamp
        story.append(Spacer(1, 0.3 * inch))
        story.extend(self._build_footer())

        doc.build(story)
        output.seek(0)
        return output.read()

    def generate_markdown(self, result: dict) -> str:
        """
        Generate markdown summary report.

        Args:
            result: InvestmentAnalysisResult as dict

        Returns:
            Markdown formatted string
        """
        lines = []

        # Header
        lines.append("# Real Estate Investment Analysis Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Key metrics
        lines.append("## Key Investment Metrics")
        lines.append("")

        # Create metrics table
        metrics_data = self._get_key_metrics_data(result)
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for label, value, _is_positive in metrics_data:
            lines.append(f"| {label} | {value} |")
        lines.append("")

        # Cash flow breakdown
        lines.append("## Cash Flow Breakdown")
        lines.append("")
        lines.append("### Monthly Income & Expenses")
        lines.append("")

        monthly_income = result.get("monthly_income", 0)
        monthly_expenses = result.get("monthly_expenses", 0)
        monthly_mortgage = result.get("monthly_mortgage", 0)
        monthly_cash_flow = result.get("monthly_cash_flow", 0)

        lines.append(f"- **Gross Monthly Income:** ${monthly_income:,.2f}")
        lines.append(f"- **Total Monthly Expenses:** ${monthly_expenses:,.2f}")
        lines.append(f"  - Mortgage Payment: ${monthly_mortgage:,.2f}")
        lines.append(f"  - Other Expenses: ${monthly_expenses - monthly_mortgage:,.2f}")
        lines.append(f"- **Net Monthly Cash Flow:** ${monthly_cash_flow:,.2f}")
        lines.append("")

        # Annual figures
        annual_income = result.get("annual_income", 0)
        annual_expenses = result.get("annual_expenses", 0)
        annual_cash_flow = result.get("annual_cash_flow", 0)

        lines.append("### Annual Summary")
        lines.append("")
        lines.append(f"- **Gross Annual Income:** ${annual_income:,.2f}")
        lines.append(f"- **Total Annual Expenses:** ${annual_expenses:,.2f}")
        lines.append(f"- **Net Annual Cash Flow:** ${annual_cash_flow:,.2f}")
        lines.append("")

        # Investment score
        lines.append("## Investment Score")
        lines.append("")

        investment_score = result.get("investment_score", 0)
        score_breakdown = result.get("score_breakdown", {})

        # Score visualization
        score_bar = self._get_score_bar(investment_score)
        lines.append(f"**Overall Score:** {investment_score:.1f}/100")
        lines.append("")
        lines.append(score_bar)
        lines.append("")

        if score_breakdown:
            lines.append("### Score Breakdown")
            lines.append("")
            for category, score in score_breakdown.items():
                bar = self._get_score_bar(score, short=True)
                label = category.replace("_", " ").title()
                lines.append(f"- **{label}:** {score:.1f}/100")
                lines.append(f"  {bar}")
            lines.append("")

        # Total investment
        lines.append("## Investment Summary")
        lines.append("")
        total_investment = result.get("total_investment", 0)
        lines.append(f"**Total Initial Investment:** ${total_investment:,.2f}")
        lines.append("")

        # Disclaimer
        lines.append("---")
        lines.append("")
        lines.append("*This report is for informational purposes only and does not constitute financial advice.*")
        lines.append("")

        return "\n".join(lines)

    def _get_key_metrics_data(self, result: dict) -> list[tuple[str, str, bool]]:
        """Extract key metrics for display. Returns list of (label, value, is_positive)."""
        metrics = [
            ("Cash on Cash ROI", result.get("cash_on_cash_roi", 0), True),
            ("Cap Rate", result.get("cap_rate", 0), True),
            ("Gross Rental Yield", result.get("gross_yield", 0), True),
            ("Net Rental Yield", result.get("net_yield", 0), True),
            ("Monthly Cash Flow", result.get("monthly_cash_flow", 0), True),
            ("Annual Cash Flow", result.get("annual_cash_flow", 0), True),
        ]

        formatted = []
        for label, value, _is_positive in metrics:
            formatted_value = self._format_metric(value, label)
            is_positive_value = value >= 0 if isinstance(value, (int, float)) else True
            formatted.append((label, formatted_value, is_positive_value))

        return formatted

    def _format_metric(self, value: float, label: str) -> str:
        """Format a metric value for display."""
        if "ROI" in label or "Rate" in label or "Yield" in label:
            return f"{value:.2f}%"
        elif "Cash Flow" in label:
            return f"${value:,.2f}"
        else:
            return f"{value:,.2f}"

    def _get_score_bar(self, score: float, short: bool = False) -> str:
        """Generate a text-based score bar visualization."""
        filled = int(score / 10) if short else int(score / 5)
        empty = (10 - filled) if short else (20 - filled)
        bar = "█" * filled + "░" * empty
        return f"[{bar}]"

    def _build_header(self, result: dict) -> list:
        """Build report header section."""
        story = []

        # Main title
        story.append(Paragraph("Investment Analysis Report", self.styles["ReportTitle"]))
        story.append(Spacer(1, 0.1 * inch))

        # Timestamp
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        story.append(
            Paragraph(f"<i>Generated on {timestamp}</i>", self.styles["Normal"])
        )

        return story

    def _build_key_metrics_section(self, result: dict) -> list:
        """Build key metrics summary section."""
        story = []

        story.append(Paragraph("Key Investment Metrics", self.styles["SectionHeader"]))

        metrics = self._get_key_metrics_data(result)

        # Create table data
        table_data = [["Metric", "Value"]]
        for label, value, is_positive in metrics:
            color = COLOR_POSITIVE if is_positive else COLOR_NEGATIVE
            colored_value = f'<font color="{color}">{value}</font>'
            table_data.append([label, colored_value])

        # Build table
        table = Table(table_data, colWidths=[2.5 * inch, 2 * inch])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_LIGHT_BG),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ])
        )

        story.append(table)
        return story

    def _build_cash_flow_section(self, result: dict) -> list:
        """Build cash flow breakdown section."""
        story = []

        story.append(Paragraph("Cash Flow Breakdown", self.styles["SectionHeader"]))

        # Monthly breakdown
        monthly_income = result.get("monthly_income", 0)
        monthly_expenses = result.get("monthly_expenses", 0)
        monthly_mortgage = result.get("monthly_mortgage", 0)
        monthly_cash_flow = result.get("monthly_cash_flow", 0)

        monthly_data = [
            ["", "Monthly", "Annually"],
            ["Gross Income", f"${monthly_income:,.2f}", f"${monthly_income * 12:,.2f}"],
            ["Operating Expenses", f"${monthly_expenses:,.2f}", f"${monthly_expenses * 12:,.2f}"],
            ["  - Mortgage", f"${monthly_mortgage:,.2f}", f"${monthly_mortgage * 12:,.2f}"],
            ["  - Other", f"${monthly_expenses - monthly_mortgage:,.2f}",
             f"${(monthly_expenses - monthly_mortgage) * 12:,.2f}"],
        ]

        # Net cash flow with color
        cash_flow_color = COLOR_POSITIVE if monthly_cash_flow >= 0 else COLOR_NEGATIVE
        monthly_cf = f'<font color="{cash_flow_color}">${monthly_cash_flow:,.2f}</font>'
        annual_cf = f'<font color="{cash_flow_color}">${monthly_cash_flow * 12:,.2f}</font>'
        monthly_data.append(["<b>Net Cash Flow</b>", monthly_cf, annual_cf])

        table = Table(monthly_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )

        story.append(table)
        return story

    def _build_investment_score_section(self, result: dict) -> list:
        """Build investment score visualization section."""
        story = []

        story.append(Paragraph("Investment Score", self.styles["SectionHeader"]))

        investment_score = result.get("investment_score", 0)
        score_breakdown = result.get("score_breakdown", {})

        # Overall score with color
        score_color = COLOR_POSITIVE if investment_score >= 70 else COLOR_NEGATIVE if investment_score < 50 else colors.orange
        score_text = f'<font name="Helvetica-Bold" size="24" color="{score_color}">{investment_score:.1f}/100</font>'

        score_table_data = [
            ["Overall Investment Score:", score_text],
        ]

        # Add score description
        if investment_score >= 80:
            description = "Excellent investment opportunity"
        elif investment_score >= 70:
            description = "Good investment potential"
        elif investment_score >= 50:
            description = "Moderate investment - review carefully"
        else:
            description = "High risk - not recommended"

        score_table_data.append(["", f'<i>{description}</i>'])

        score_table = Table(score_table_data, colWidths=[2.5 * inch, 2 * inch])
        score_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
                ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (0, 0), 12),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ])
        )

        story.append(score_table)
        story.append(Spacer(1, 0.1 * inch))

        # Score breakdown if available
        if score_breakdown:
            story.append(Paragraph("Score Breakdown", self.styles["SubsectionHeader"]))

            breakdown_data = [["Category", "Score", "Rating"]]
            for category, score in score_breakdown.items():
                label = category.replace("_", " ").title()
                score_value = f"{score:.1f}"
                if score >= 80:
                    rating = "Excellent"
                elif score >= 70:
                    rating = "Good"
                elif score >= 50:
                    rating = "Fair"
                else:
                    rating = "Poor"
                breakdown_data.append([label, score_value, rating])

            breakdown_table = Table(breakdown_data, colWidths=[2 * inch, 1 * inch, 1.5 * inch])
            breakdown_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_SUBHEADER),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
                    ("ALIGN", (1, 0), (2, -1), "CENTER"),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ])
            )

            story.append(breakdown_table)

        return story

    def _build_monthly_breakdown_table(self, result: dict) -> list:
        """Build detailed monthly breakdown table."""
        story = []

        story.append(Paragraph("Monthly Breakdown", self.styles["SectionHeader"]))

        monthly_income = result.get("monthly_income", 0)
        monthly_mortgage = result.get("monthly_mortgage", 0)
        property_tax = result.get("property_tax_monthly", 0)
        insurance = result.get("insurance_monthly", 0)
        hoa = result.get("hoa_monthly", 0)
        maintenance = result.get("maintenance_monthly", 0)
        vacancy = result.get("vacancy_monthly", 0)
        management = result.get("management_monthly", 0)
        monthly_cash_flow = result.get("monthly_cash_flow", 0)

        breakdown_data = [
            ["Category", "Amount", "% of Income"],
            ["Income", "", ""],
            ["  Gross Rent", f"${monthly_income:,.2f}", "100.00%"],
            ["", "", ""],
            ["Expenses", "", ""],
            ["  Mortgage Payment", f"${monthly_mortgage:,.2f}",
             f"{(monthly_mortgage / monthly_income * 100):.1f}%" if monthly_income > 0 else "N/A"],
            ["  Property Tax", f"${property_tax:,.2f}",
             f"{(property_tax / monthly_income * 100):.1f}%" if monthly_income > 0 else "N/A"],
            ["  Insurance", f"${insurance:,.2f}",
             f"{(insurance / monthly_income * 100):.1f}%" if monthly_income > 0 else "N/A"],
            ["  HOA Fees", f"${hoa:,.2f}",
             f"{(hoa / monthly_income * 100):.1f}%" if monthly_income > 0 else "N/A"],
            ["  Maintenance", f"${maintenance:,.2f}",
             f"{(maintenance / monthly_income * 100):.1f}%" if monthly_income > 0 else "N/A"],
            ["  Vacancy Allowance", f"${vacancy:,.2f}",
             f"{(vacancy / monthly_income * 100):.1f}%" if monthly_income > 0 else "N/A"],
            ["  Management Fee", f"${management:,.2f}",
             f"{(management / monthly_income * 100):.1f}%" if monthly_income > 0 else "N/A"],
            ["", "", ""],
            ["Net Cash Flow", f"${monthly_cash_flow:,.2f}",
             f"{(monthly_cash_flow / monthly_income * 100):.1f}%" if monthly_income > 0 else "N/A"],
        ]

        table = Table(breakdown_data, colWidths=[2 * inch, 1.5 * inch, 1 * inch])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("FONTNAME", (0, 1), (0, 1), "Helvetica-Bold"),
                ("FONTNAME", (0, 4), (0, 4), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ])
        )

        story.append(table)
        return story

    def _build_projection_section(self, projection: CashFlowProjection) -> list:
        """Build multi-year projection section."""
        story = []

        story.append(Paragraph("Multi-Year Projection", self.styles["SectionHeader"]))
        story.append(Spacer(1, 0.1 * inch))

        # Summary metrics
        summary_data = [
            ["Projection Summary", ""],
            ["Property Price", f"${projection.property_price:,.2f}"],
            ["Projection Period", f"{projection.projection_years} years"],
            ["Total Cash Flow", f"${projection.total_cash_flow:,.2f}"],
            ["Total Principal Paid", f"${projection.total_principal_paid:,.2f}"],
            ["Final Equity", f"${projection.final_equity:,.2f}"],
        ]

        if projection.irr is not None:
            summary_data.append(["Internal Rate of Return (IRR)", f"{projection.irr:.2f}%"])

        summary_table = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
        summary_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )

        story.append(summary_table)
        story.append(Spacer(1, 0.15 * inch))

        # Yearly breakdown table
        story.append(Paragraph("Yearly Breakdown", self.styles["SubsectionHeader"]))

        yearly_data = [["Year", "Income", "Expenses", "Cash Flow", "Property Value", "Equity"]]

        for year_data in projection.yearly_breakdown[:10]:  # Limit to 10 years for readability
            yearly_data.append([
                str(year_data.year),
                f"${year_data.gross_income:,.0f}",
                f"${year_data.operating_expenses + year_data.mortgage_payment:,.0f}",
                f"${year_data.cash_flow:,.0f}",
                f"${year_data.property_value:,.0f}",
                f"${year_data.equity:,.0f}",
            ])

        yearly_table = Table(yearly_data, colWidths=[0.5 * inch, 1 * inch, 1 * inch, 0.8 * inch, 1.2 * inch, 1 * inch])
        yearly_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )

        story.append(yearly_table)

        return story

    def _build_footer(self) -> list:
        """Build report footer with disclaimer."""
        story = []

        disclaimer = (
            '<i>This report is for informational purposes only and does not '
            'constitute financial, tax, or legal advice. Please consult with '
            'qualified professionals before making investment decisions.</i>'
        )

        story.append(Paragraph(disclaimer, self.styles["Normal"]))

        return story
