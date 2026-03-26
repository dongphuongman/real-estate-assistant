"""
SPRAV Risk Assessment Module

Manages risk identification, assessment, and mitigation planning.

Usage:
    from scripts.sprav.risk_assessment import RiskAssessment, Risk, RiskLevel

    assessment = RiskAssessment()
    assessment.add_risk(
        description="Third-party API rate limiting",
        probability=RiskLevel.MEDIUM,
        impact=RiskLevel.HIGH,
        mitigation="Implement request caching and retry logic",
        owner="Backend Team",
    )
    assessment.save("risks.json")
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class RiskLevel(str, Enum):
    """Risk level for probability and impact."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class RiskCategory(str, Enum):
    """Risk category."""

    TECHNICAL = "Technical"
    SECURITY = "Security"
    PERFORMANCE = "Performance"
    BUSINESS = "Business"
    OPERATIONAL = "Operational"
    COMPLIANCE = "Compliance"
    THIRD_PARTY = "Third-Party"
    RESOURCE = "Resource"


class RiskStatus(str, Enum):
    """Risk status."""

    IDENTIFIED = "Identified"
    ANALYZING = "Analyzing"
    MITIGATING = "Mitigating"
    MONITORING = "Monitoring"
    RESOLVED = "Resolved"
    ACCEPTED = "Accepted"


@dataclass
class Risk:
    """Represents a single risk."""

    id: str
    description: str
    probability: RiskLevel
    impact: RiskLevel
    mitigation: str
    owner: str
    category: RiskCategory = RiskCategory.TECHNICAL
    status: RiskStatus = RiskStatus.IDENTIFIED
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    trigger: str = ""  # What triggers this risk
    contingency: str = ""  # Plan B if risk materializes
    residual_risk: RiskLevel | None = None  # Risk after mitigation
    notes: list[str] = field(default_factory=list)

    @property
    def risk_score(self) -> int:
        """Calculate risk score (probability × impact)."""
        score_matrix = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }
        return score_matrix[self.probability] * score_matrix[self.impact]

    @property
    def risk_level(self) -> RiskLevel:
        """Determine overall risk level from score."""
        score = self.risk_score
        if score >= 12:
            return RiskLevel.CRITICAL
        elif score >= 6:
            return RiskLevel.HIGH
        elif score >= 2:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "probability": self.probability.value,
            "impact": self.impact.value,
            "category": self.category.value,
            "status": self.status.value,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "residual_risk": self.residual_risk.value if self.residual_risk else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Risk":
        """Create from dictionary."""
        # Remove computed fields
        data = {k: v for k, v in data.items() if k not in ("risk_score", "risk_level")}
        data["probability"] = RiskLevel(data["probability"])
        data["impact"] = RiskLevel(data["impact"])
        data["category"] = RiskCategory(data["category"])
        data["status"] = RiskStatus(data["status"])
        if data.get("residual_risk"):
            data["residual_risk"] = RiskLevel(data["residual_risk"])
        return cls(**data)


class RiskAssessment:
    """
    Manages risk assessment for SPRAV validation.

    Supports adding, updating, querying, and exporting risks.
    """

    # Risk matrix for visualization
    RISK_MATRIX = {
        (RiskLevel.LOW, RiskLevel.LOW): "LOW",
        (RiskLevel.LOW, RiskLevel.MEDIUM): "LOW",
        (RiskLevel.LOW, RiskLevel.HIGH): "MEDIUM",
        (RiskLevel.LOW, RiskLevel.CRITICAL): "MEDIUM",
        (RiskLevel.MEDIUM, RiskLevel.LOW): "LOW",
        (RiskLevel.MEDIUM, RiskLevel.MEDIUM): "MEDIUM",
        (RiskLevel.MEDIUM, RiskLevel.HIGH): "HIGH",
        (RiskLevel.MEDIUM, RiskLevel.CRITICAL): "HIGH",
        (RiskLevel.HIGH, RiskLevel.LOW): "MEDIUM",
        (RiskLevel.HIGH, RiskLevel.MEDIUM): "HIGH",
        (RiskLevel.HIGH, RiskLevel.HIGH): "CRITICAL",
        (RiskLevel.HIGH, RiskLevel.CRITICAL): "CRITICAL",
        (RiskLevel.CRITICAL, RiskLevel.LOW): "MEDIUM",
        (RiskLevel.CRITICAL, RiskLevel.MEDIUM): "HIGH",
        (RiskLevel.CRITICAL, RiskLevel.HIGH): "CRITICAL",
        (RiskLevel.CRITICAL, RiskLevel.CRITICAL): "CRITICAL",
    }

    def __init__(self, project_root: Path | None = None):
        """
        Initialize the risk assessment.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.risks: list[Risk] = []
        self._counter = 0

    def _generate_id(self) -> str:
        """Generate a unique risk ID."""
        self._counter += 1
        return f"R{self._counter:03d}"

    def add_risk(
        self,
        description: str,
        probability: RiskLevel,
        impact: RiskLevel,
        mitigation: str,
        owner: str,
        category: RiskCategory = RiskCategory.TECHNICAL,
        trigger: str = "",
        contingency: str = "",
        notes: list[str] | None = None,
    ) -> Risk:
        """
        Add a new risk.

        Args:
            description: Risk description
            probability: Probability level
            impact: Impact level
            mitigation: Mitigation strategy
            owner: Risk owner
            category: Risk category
            trigger: What triggers this risk
            contingency: Plan B if risk materializes
            notes: Additional notes

        Returns:
            The created risk
        """
        risk = Risk(
            id=self._generate_id(),
            description=description,
            probability=probability,
            impact=impact,
            mitigation=mitigation,
            owner=owner,
            category=category,
            trigger=trigger,
            contingency=contingency,
            notes=notes or [],
        )
        self.risks.append(risk)
        return risk

    def get_risk(self, risk_id: str) -> Risk | None:
        """Get a risk by ID."""
        for risk in self.risks:
            if risk.id == risk_id:
                return risk
        return None

    def update_risk(
        self,
        risk_id: str,
        status: RiskStatus | None = None,
        residual_risk: RiskLevel | None = None,
        **kwargs,
    ) -> Risk | None:
        """
        Update a risk.

        Args:
            risk_id: ID of the risk to update
            status: New status
            residual_risk: Residual risk level after mitigation
            **kwargs: Other fields to update

        Returns:
            The updated risk or None if not found
        """
        risk = self.get_risk(risk_id)
        if risk is None:
            return None

        if status is not None:
            risk.status = status
        if residual_risk is not None:
            risk.residual_risk = residual_risk

        for key, value in kwargs.items():
            if hasattr(risk, key):
                setattr(risk, key, value)

        risk.updated_at = datetime.now().isoformat()
        return risk

    def query(
        self,
        probability: RiskLevel | None = None,
        impact: RiskLevel | None = None,
        category: RiskCategory | None = None,
        status: RiskStatus | None = None,
        owner: str | None = None,
        min_score: int | None = None,
    ) -> list[Risk]:
        """
        Query risks by various criteria.

        Args:
            probability: Filter by probability
            impact: Filter by impact
            category: Filter by category
            status: Filter by status
            owner: Filter by owner
            min_score: Minimum risk score

        Returns:
            List of matching risks
        """
        results = self.risks

        if probability is not None:
            results = [r for r in results if r.probability == probability]
        if impact is not None:
            results = [r for r in results if r.impact == impact]
        if category is not None:
            results = [r for r in results if r.category == category]
        if status is not None:
            results = [r for r in results if r.status == status]
        if owner is not None:
            results = [r for r in results if r.owner == owner]
        if min_score is not None:
            results = [r for r in results if r.risk_score >= min_score]

        return results

    @property
    def critical_count(self) -> int:
        """Count of critical risks."""
        return len([r for r in self.risks if r.risk_level == RiskLevel.CRITICAL])

    @property
    def high_count(self) -> int:
        """Count of high risks."""
        return len([r for r in self.risks if r.risk_level == RiskLevel.HIGH])

    @property
    def unresolved_count(self) -> int:
        """Count of unresolved risks."""
        return len(
            [
                r
                for r in self.risks
                if r.status not in (RiskStatus.RESOLVED, RiskStatus.ACCEPTED)
            ]
        )

    def save(self, path: Path | str) -> None:
        """
        Save risks to a file.

        Args:
            path: Output file path (.json or .csv)
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.suffix == ".json":
            with open(path, "w") as f:
                json.dump([r.to_dict() for r in self.risks], f, indent=2)
        elif path.suffix == ".csv":
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "ID",
                        "Description",
                        "Category",
                        "Probability",
                        "Impact",
                        "Risk Score",
                        "Risk Level",
                        "Mitigation",
                        "Owner",
                        "Status",
                        "Created",
                    ]
                )
                for r in self.risks:
                    writer.writerow(
                        [
                            r.id,
                            r.description,
                            r.category.value,
                            r.probability.value,
                            r.impact.value,
                            r.risk_score,
                            r.risk_level.value,
                            r.mitigation,
                            r.owner,
                            r.status.value,
                            r.created_at,
                        ]
                    )
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def load(self, path: Path | str) -> None:
        """
        Load risks from a file.

        Args:
            path: Input file path (.json)
        """
        path = Path(path)
        if path.suffix == ".json":
            with open(path) as f:
                data = json.load(f)
            self.risks = [Risk.from_dict(r) for r in data]
            # Update counter to avoid ID collisions
            if self.risks:
                max_id = max(int(r.id[1:]) for r in self.risks)
                self._counter = max_id
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def summary(self) -> dict:
        """
        Generate a summary of risks.

        Returns:
            Dictionary with risk statistics
        """
        return {
            "total": len(self.risks),
            "by_level": {
                level.value: len([r for r in self.risks if r.risk_level == level])
                for level in RiskLevel
            },
            "by_category": {
                cat.value: len(self.query(category=cat)) for cat in RiskCategory
            },
            "by_status": {
                status.value: len(self.query(status=status)) for status in RiskStatus
            },
            "critical_high": self.critical_count + self.high_count,
            "unresolved": self.unresolved_count,
            "average_score": sum(r.risk_score for r in self.risks) / len(self.risks)
            if self.risks
            else 0,
        }

    def to_markdown(self) -> str:
        """
        Generate markdown table of risks.

        Returns:
            Markdown formatted string
        """
        if not self.risks:
            return "No risks identified."

        lines = [
            "# Risk Assessment Matrix",
            "",
            f"**Total Risks:** {len(self.risks)}",
            f"**Critical/High:** {self.critical_count + self.high_count}",
            f"**Unresolved:** {self.unresolved_count}",
            "",
            "## Risk Matrix",
            "",
            "```\n           │ LOW    │ MEDIUM │ HIGH   │ CRITICAL",
            "───────────┼────────┼────────┼────────┼─────────",
            "CRITICAL   │ MED    │ HIGH   │ CRIT   │ CRIT",
            "HIGH       │ MED    │ HIGH   │ CRIT   │ CRIT",
            "MEDIUM     │ LOW    │ MED    │ HIGH   │ HIGH",
            "LOW        │ LOW    │ LOW    │ MED    │ MED",
            "```",
            "",
            "## Identified Risks",
            "",
            "| ID | Description | Category | Prob | Impact | Score | Level | Owner | Status |",
            "|----|-------------|----------|------|--------|-------|-------|-------|--------|",
        ]

        # Sort by risk score descending
        sorted_risks = sorted(self.risks, key=lambda r: r.risk_score, reverse=True)

        for r in sorted_risks:
            level_icon = {
                RiskLevel.CRITICAL: "🚨",
                RiskLevel.HIGH: "⚠️",
                RiskLevel.MEDIUM: "⚡",
                RiskLevel.LOW: "✓",
            }.get(r.risk_level, "")
            lines.append(
                f"| {r.id} | {r.description[:50]}... | {r.category.value} | {r.probability.value} | {r.impact.value} | {r.risk_score} | {level_icon} {r.risk_level.value} | {r.owner} | {r.status.value} |"
            )

        # Add mitigation details
        lines.extend(
            [
                "",
                "## Mitigation Plans",
                "",
            ]
        )

        for r in sorted_risks:
            if r.mitigation:
                lines.append(f"### {r.id}: {r.description[:60]}...")
                lines.append("")
                lines.append(f"**Mitigation:** {r.mitigation}")
                if r.contingency:
                    lines.append(f"**Contingency:** {r.contingency}")
                lines.append("")

        return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for risk assessment."""
    import argparse

    parser = argparse.ArgumentParser(description="SPRAV Risk Assessment")
    parser.add_argument("--load", type=Path, help="Load risks from file")
    parser.add_argument("--save", type=Path, help="Save risks to file")
    parser.add_argument("--summary", action="store_true", help="Print summary")
    parser.add_argument("--markdown", action="store_true", help="Output as markdown")

    args = parser.parse_args(argv)

    assessment = RiskAssessment()

    if args.load:
        assessment.load(args.load)
        print(f"Loaded {len(assessment.risks)} risks from {args.load}")

    if args.summary:
        print(json.dumps(assessment.summary(), indent=2))

    if args.markdown:
        print(assessment.to_markdown())

    if args.save:
        assessment.save(args.save)
        print(f"Saved {len(assessment.risks)} risks to {args.save}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
