"""
CMA adjustment calculations for property valuation.

This module implements adjustment calculations for Comparative Market Analysis,
accounting for differences between subject and comparable properties.

Adjustment categories:
1. Location - District price indices and neighborhood premiums
2. Size - Price per sqm scaling for area differences
3. Age - Depreciation/appreciation based on year built
4. Condition - Energy rating and overall condition
5. Amenities - Individual amenity premiums/discounts
6. Floor - Ground floor penalty, top floor premium
7. Market conditions - Time-based price adjustments

Based on HedonicValuationModel coefficients from analytics/valuation_model.py
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from data.schemas import Property

logger = logging.getLogger(__name__)


@dataclass
class CMAAdjustment:
    """Single adjustment factor for a comparable property."""

    category: str  # location, size, age, condition, amenities, floor, market
    description: str
    subject_value: Any
    comp_value: Any
    adjustment_percent: float  # Can be negative
    adjustment_amount: float  # Applied to comp price
    confidence: float = 1.0  # 0.0-1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category,
            "description": self.description,
            "subject_value": str(self.subject_value) if self.subject_value is not None else None,
            "comp_value": str(self.comp_value) if self.comp_value is not None else None,
            "adjustment_percent": round(self.adjustment_percent, 2),
            "adjustment_amount": round(self.adjustment_amount, 2),
            "confidence": round(self.confidence, 2),
        }


@dataclass
class AdjustedComparable:
    """Comparable property with all adjustments applied."""

    property_id: str
    original_price: float
    adjustments: List[CMAAdjustment] = field(default_factory=list)
    total_adjustment_percent: float = 0.0
    total_adjustment_amount: float = 0.0
    adjusted_price: float = 0.0
    net_adjustment: float = 0.0  # Positive = upward adjustment

    def __post_init__(self):
        if not self.adjustments:
            self.adjusted_price = self.original_price


class CMAAdjustmentCalculator:
    """
    Calculate fair market adjustments for comparable properties.

    Uses hedonic pricing coefficients to adjust comparable prices
    for differences from the subject property.

    Adjustment Logic:
    - If subject has BETTER feature → negative adjustment to comparable (it's overpriced relative to subject)
    - If subject has WORSE feature → positive adjustment to comparable (it's worth more than subject)
    """

    # Reference: HedonicValuationModel coefficients
    AMENITY_PREMIUM = {
        "has_parking": 0.05,  # +5%
        "has_garden": 0.08,  # +8%
        "has_elevator": 0.03,  # +3%
        "has_balcony": 0.04,  # +4%
        "is_furnished": 0.10,  # +10%
        "has_pool": 0.12,  # +12%
        "has_garage": 0.06,  # +6%
        "pets_allowed": 0.02,  # +2%
    }

    ENERGY_PREMIUM = {
        "A": 0.10,
        "B": 0.07,
        "C": 0.04,
        "D": 0.00,
        "E": -0.03,
        "F": -0.06,
        "G": -0.10,
    }

    # Age depreciation: 0.5% per year from baseline (2000)
    YEAR_PREMIUM_PER_YEAR = 0.005
    YEAR_BASELINE = 2000
    MAX_AGE_ADJUSTMENT = 0.20  # Cap at ±20%

    # Size adjustment: 0.3% per 1% size difference
    SIZE_ADJUSTMENT_PER_PERCENT = 0.003

    # Floor adjustments (for apartments)
    FLOOR_ADJUSTMENTS = {
        "ground": -0.03,  # Ground floor penalty
        "top": 0.02,  # Top floor premium
        "middle": 0.00,
    }

    # Market time adjustment (monthly rate)
    MARKET_TIME_ADJUSTMENT_MONTHLY = 0.005  # 0.5% per month

    def __init__(
        self,
        market_price_trend: Optional[float] = None,
        location_price_indices: Optional[Dict[str, float]] = None,
        custom_adjustments: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize the adjustment calculator.

        Args:
            market_price_trend: Overall market price trend (e.g., 0.02 for +2%)
            location_price_indices: Price indices by district/neighborhood
            custom_adjustments: Override default adjustment factors
        """
        self.market_price_trend = market_price_trend or 0.0
        self.location_price_indices = location_price_indices or {}
        self.custom_adjustments = custom_adjustments or {}

        # Apply custom adjustments if provided
        if custom_adjustments:
            self.AMENITY_PREMIUM.update(
                {k: v for k, v in custom_adjustments.items() if k in self.AMENITY_PREMIUM}
            )

    def calculate_adjustments(
        self,
        subject: Property,
        comparable: Property,
        comp_price: float,
    ) -> List[CMAAdjustment]:
        """
        Calculate all adjustments for a comparable property.

        Args:
            subject: Subject property
            comparable: Comparable property
            comp_price: Comparable's listing/sale price

        Returns:
            List of CMAAdjustment objects
        """
        adjustments = []

        # 1. Location adjustment
        loc_adj = self._adjust_location(subject, comparable, comp_price)
        if loc_adj:
            adjustments.append(loc_adj)

        # 2. Size adjustment
        size_adj = self._adjust_size(subject, comparable, comp_price)
        if size_adj:
            adjustments.append(size_adj)

        # 3. Age adjustment
        age_adj = self._adjust_age(subject, comparable, comp_price)
        if age_adj:
            adjustments.append(age_adj)

        # 4. Condition (energy rating) adjustment
        condition_adj = self._adjust_condition(subject, comparable, comp_price)
        if condition_adj:
            adjustments.append(condition_adj)

        # 5. Amenities adjustments (multiple)
        amenity_adjs = self._adjust_amenities(subject, comparable, comp_price)
        adjustments.extend(amenity_adjs)

        # 6. Floor adjustment (for apartments)
        floor_adj = self._adjust_floor(subject, comparable, comp_price)
        if floor_adj:
            adjustments.append(floor_adj)

        # 7. Market conditions adjustment
        market_adj = self._adjust_market_conditions(comparable, comp_price)
        if market_adj:
            adjustments.append(market_adj)

        return adjustments

    def apply_adjustments(
        self,
        comp_price: float,
        adjustments: List[CMAAdjustment],
    ) -> AdjustedComparable:
        """
        Apply all adjustments to get the final adjusted price.

        Args:
            comp_price: Original comparable price
            adjustments: List of adjustments to apply

        Returns:
            AdjustedComparable with all adjustments applied
        """
        total_percent = 0.0
        total_amount = 0.0

        for adj in adjustments:
            total_percent += adj.adjustment_percent
            total_amount += adj.adjustment_amount

        # Cap total adjustment at ±30%
        total_percent = max(min(total_percent, 0.30), -0.30)

        adjusted_price = comp_price * (1 + total_percent)
        net_adjustment = adjusted_price - comp_price

        return AdjustedComparable(
            property_id="",  # Set by caller
            original_price=comp_price,
            adjustments=adjustments,
            total_adjustment_percent=round(total_percent * 100, 2),
            total_adjustment_amount=round(total_amount, 2),
            adjusted_price=round(adjusted_price, 2),
            net_adjustment=round(net_adjustment, 2),
        )

    def _adjust_location(
        self,
        subject: Property,
        comp: Property,
        comp_price: float,
    ) -> Optional[CMAAdjustment]:
        """
        Location adjustment based on district price indices.

        If comparable is in a more expensive area → positive adjustment
        If comparable is in a cheaper area → negative adjustment
        """
        # Default: no adjustment if no indices available
        if not self.location_price_indices:
            return None

        subject_key = self._get_location_key(subject)
        comp_key = self._get_location_key(comp)

        subject_index = self.location_price_indices.get(subject_key, 1.0)
        comp_index = self.location_price_indices.get(comp_key, 1.0)

        if subject_index == comp_index:
            return None

        # Adjustment = how much to adjust comp to match subject's location
        # If comp is in pricier area (comp_index > subject_index),
        # we need negative adjustment (it's worth more than subject)
        adjustment_percent = (comp_index - subject_index) / subject_index

        # Cap at ±15%
        adjustment_percent = max(min(adjustment_percent, 0.15), -0.15)

        return CMAAdjustment(
            category="location",
            description=f"Location price index difference ({comp_key or 'N/A'} vs {subject_key or 'N/A'})",
            subject_value=subject_key,
            comp_value=comp_key,
            adjustment_percent=-adjustment_percent,  # Negative because we adjust comp towards subject
            adjustment_amount=round(-comp_price * adjustment_percent, 2),
            confidence=0.7 if self.location_price_indices else 0.3,
        )

    def _adjust_size(
        self,
        subject: Property,
        comp: Property,
        comp_price: float,
    ) -> Optional[CMAAdjustment]:
        """
        Size adjustment based on area difference.

        If comparable is larger → negative adjustment (divide price)
        If comparable is smaller → positive adjustment (multiply price)
        """
        if not subject.area_sqm or not comp.area_sqm:
            return None

        if subject.area_sqm <= 0 or comp.area_sqm <= 0:
            return None

        size_diff_percent = (comp.area_sqm - subject.area_sqm) / subject.area_sqm

        # No adjustment needed if within 5%
        if abs(size_diff_percent) < 0.05:
            return None

        # Adjustment: scale by price per sqm logic
        # If comp is 20% larger, we reduce price proportionally
        adjustment_percent = -size_diff_percent * self.SIZE_ADJUSTMENT_PER_PERCENT / 0.01

        # Cap at ±10%
        adjustment_percent = max(min(adjustment_percent, 0.10), -0.10)

        return CMAAdjustment(
            category="size",
            description=f"Area difference ({comp.area_sqm} vs {subject.area_sqm} sqm)",
            subject_value=f"{subject.area_sqm} sqm",
            comp_value=f"{comp.area_sqm} sqm",
            adjustment_percent=round(adjustment_percent, 4),
            adjustment_amount=round(comp_price * adjustment_percent, 2),
            confidence=0.8,
        )

    def _adjust_age(
        self,
        subject: Property,
        comp: Property,
        comp_price: float,
    ) -> Optional[CMAAdjustment]:
        """
        Age adjustment based on year built.

        Newer properties get premium, older get discount.
        Adjustment is based on age difference between subject and comp.
        """
        if not subject.year_built or not comp.year_built:
            return None

        age_diff = comp.year_built - subject.year_built

        # No adjustment if same age (within 2 years)
        if abs(age_diff) <= 2:
            return None

        # Calculate adjustment: comp newer = positive, older = negative
        adjustment_percent = -age_diff * self.YEAR_PREMIUM_PER_YEAR

        # Cap at max
        adjustment_percent = max(
            min(adjustment_percent, self.MAX_AGE_ADJUSTMENT), -self.MAX_AGE_ADJUSTMENT
        )

        return CMAAdjustment(
            category="age",
            description=f"Year built difference ({comp.year_built} vs {subject.year_built})",
            subject_value=subject.year_built,
            comp_value=comp.year_built,
            adjustment_percent=round(adjustment_percent, 4),
            adjustment_amount=round(comp_price * adjustment_percent, 2),
            confidence=0.7,
        )

    def _adjust_condition(
        self,
        subject: Property,
        comp: Property,
        comp_price: float,
    ) -> Optional[CMAAdjustment]:
        """
        Condition adjustment based on energy rating.

        Better energy rating = higher value.
        """
        subject_rating = (subject.energy_rating or "D").upper()
        comp_rating = (comp.energy_rating or "D").upper()

        subject_premium = self.ENERGY_PREMIUM.get(subject_rating, 0.0)
        comp_premium = self.ENERGY_PREMIUM.get(comp_rating, 0.0)

        if subject_premium == comp_premium:
            return None

        # Adjustment: how much to adjust comp to match subject
        # If comp has better rating (higher premium), we reduce its value
        adjustment_percent = -(comp_premium - subject_premium)

        return CMAAdjustment(
            category="condition",
            description=f"Energy rating difference ({comp_rating} vs {subject_rating})",
            subject_value=subject_rating,
            comp_value=comp_rating,
            adjustment_percent=round(adjustment_percent, 4),
            adjustment_amount=round(comp_price * adjustment_percent, 2),
            confidence=0.6,
        )

    def _adjust_amenities(
        self,
        subject: Property,
        comp: Property,
        comp_price: float,
    ) -> List[CMAAdjustment]:
        """
        Individual amenity adjustments.

        For each amenity, if subject has it but comp doesn't → negative adjustment
        If comp has it but subject doesn't → positive adjustment
        """
        adjustments = []

        for amenity, premium in self.AMENITY_PREMIUM.items():
            subject_has = bool(getattr(subject, amenity, False))
            comp_has = bool(getattr(comp, amenity, False))

            if subject_has == comp_has:
                continue

            # If comp has amenity but subject doesn't → positive adjustment
            # (comp is worth more, so we add to its value)
            # If subject has amenity but comp doesn't → negative adjustment
            # (comp is worth less, so we subtract)
            adjustment_percent = premium if comp_has else -premium

            amenity_name = amenity.replace("has_", "").replace("is_", "").replace("_", " ")

            adjustments.append(
                CMAAdjustment(
                    category="amenities",
                    description=f"{'Comparable has' if comp_has else 'Subject has'} {amenity_name}",
                    subject_value="Yes" if subject_has else "No",
                    comp_value="Yes" if comp_has else "No",
                    adjustment_percent=round(adjustment_percent, 4),
                    adjustment_amount=round(comp_price * adjustment_percent, 2),
                    confidence=0.8,
                )
            )

        return adjustments

    def _adjust_floor(
        self,
        subject: Property,
        comp: Property,
        comp_price: float,
    ) -> Optional[CMAAdjustment]:
        """
        Floor level adjustment (mainly for apartments).

        Ground floor: penalty
        Top floor: premium
        Middle floors: neutral
        """
        # Only apply for apartments
        if subject.property_type != "apartment" or comp.property_type != "apartment":
            return None

        if subject.floor is None or comp.floor is None:
            return None

        subject_floor_type = self._get_floor_type(subject.floor, subject.total_floors)
        comp_floor_type = self._get_floor_type(comp.floor, comp.total_floors)

        if subject_floor_type == comp_floor_type:
            return None

        subject_adj = self.FLOOR_ADJUSTMENTS.get(subject_floor_type, 0.0)
        comp_adj = self.FLOOR_ADJUSTMENTS.get(comp_floor_type, 0.0)

        adjustment_percent = -(comp_adj - subject_adj)

        if abs(adjustment_percent) < 0.005:
            return None

        return CMAAdjustment(
            category="floor",
            description=f"Floor level difference ({comp_floor_type} vs {subject_floor_type})",
            subject_value=f"Floor {subject.floor}",
            comp_value=f"Floor {comp.floor}",
            adjustment_percent=round(adjustment_percent, 4),
            adjustment_amount=round(comp_price * adjustment_percent, 2),
            confidence=0.6,
        )

    def _adjust_market_conditions(
        self,
        comp: Property,
        comp_price: float,
    ) -> Optional[CMAAdjustment]:
        """
        Market timing adjustment based on listing date.

        Adjusts for price changes since the comparable was listed.
        """
        listing_date = comp.scraped_at or comp.last_updated

        if not listing_date:
            return None

        now = datetime.now()

        # Handle timezone-aware datetime
        if hasattr(listing_date, "tzinfo") and listing_date.tzinfo:
            listing_date = listing_date.replace(tzinfo=None)

        months_old = (now - listing_date).days / 30.0

        # No adjustment for recent listings (< 30 days)
        if months_old < 1:
            return None

        # Apply market trend adjustment
        # If market is rising (positive trend), older listings need upward adjustment
        # If market is falling (negative trend), older listings need downward adjustment
        adjustment_percent = self.market_price_trend * months_old

        # Cap at ±10%
        adjustment_percent = max(min(adjustment_percent, 0.10), -0.10)

        return CMAAdjustment(
            category="market",
            description=f"Market conditions adjustment ({months_old:.1f} months old)",
            subject_value="Current",
            comp_value=f"{months_old:.0f} months ago",
            adjustment_percent=round(adjustment_percent, 4),
            adjustment_amount=round(comp_price * adjustment_percent, 2),
            confidence=0.5,
        )

    def _get_location_key(self, prop: Property) -> Optional[str]:
        """Get location key for price index lookup."""
        if prop.neighborhood:
            return f"{prop.city}:{prop.neighborhood}".lower()
        if prop.district:
            return f"{prop.city}:{prop.district}".lower()
        return prop.city.lower()

    def _get_floor_type(
        self,
        floor: Optional[float],
        total_floors: Optional[float],
    ) -> str:
        """Categorize floor type for adjustment."""
        if floor is None:
            return "middle"

        if floor <= 0 or floor == 1:
            return "ground"

        if total_floors and floor >= total_floors:
            return "top"

        return "middle"


def calculate_cma_adjustments(
    subject: Property,
    comparable: Property,
    comp_price: float,
    market_trend: Optional[float] = None,
    location_indices: Optional[Dict[str, float]] = None,
) -> AdjustedComparable:
    """
    Convenience function to calculate and apply CMA adjustments.

    Args:
        subject: Subject property
        comparable: Comparable property
        comp_price: Comparable's price
        market_trend: Optional market price trend
        location_indices: Optional location price indices

    Returns:
        AdjustedComparable with all adjustments applied
    """
    calculator = CMAAdjustmentCalculator(
        market_price_trend=market_trend,
        location_price_indices=location_indices,
    )

    adjustments = calculator.calculate_adjustments(subject, comparable, comp_price)
    result = calculator.apply_adjustments(comp_price, adjustments)
    result.property_id = comparable.id or ""

    return result
