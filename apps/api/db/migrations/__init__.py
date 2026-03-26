"""Database migrations package."""

from .add_cma_reports_006 import MIGRATION_ID as cma_reports_migration_id
from .add_market_anomalies_001 import MIGRATION_ID as market_anomalies_migration_id

__all__ = ["cma_reports_migration_id", "market_anomalies_migration_id"]
