"""
Context window metrics logging for token usage tracking.

This module provides async SQLite-based storage for context window optimization metrics,
enabling analysis of token usage, costs, and optimization effectiveness.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import aiosqlite

# Default path for context metrics database
CONTEXT_METRICS_DB_PATH = Path("data/context_metrics.db")


@dataclass
class ContextUsageMetrics:
    """Metrics for a single context optimization event."""

    timestamp: datetime
    session_id: str
    model_id: str
    provider: str
    input_tokens: int
    output_tokens: int
    context_window_limit: int
    utilization_percent: float
    estimated_cost_usd: float
    compression_applied: bool
    summarization_applied: bool
    messages_before: int
    messages_after: int
    processing_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "model_id": self.model_id,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "context_window_limit": self.context_window_limit,
            "utilization_percent": self.utilization_percent,
            "estimated_cost_usd": self.estimated_cost_usd,
            "compression_applied": self.compression_applied,
            "summarization_applied": self.summarization_applied,
            "messages_before": self.messages_before,
            "messages_after": self.messages_after,
            "processing_time_ms": self.processing_time_ms,
        }


async def init_context_metrics_db(db_path: Path = CONTEXT_METRICS_DB_PATH) -> None:
    """Initialize the context metrics database table."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS context_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER,
                context_window_limit INTEGER NOT NULL,
                utilization_percent REAL NOT NULL,
                estimated_cost_usd REAL,
                compression_applied INTEGER NOT NULL,
                summarization_applied INTEGER NOT NULL,
                messages_before INTEGER NOT NULL,
                messages_after INTEGER NOT NULL,
                processing_time_ms REAL
            )
        """)
        await conn.commit()


async def log_context_metrics(
    metrics: ContextUsageMetrics,
    db_path: Path = CONTEXT_METRICS_DB_PATH,
) -> None:
    """Log a context optimization event to the database."""
    await init_context_metrics_db(db_path)

    async with aiosqlite.connect(db_path) as conn:
        await conn.execute(
            """
            INSERT INTO context_metrics (
                timestamp, session_id, model_id, provider,
                input_tokens, output_tokens, context_window_limit,
                utilization_percent, estimated_cost_usd,
                compression_applied, summarization_applied,
                messages_before, messages_after, processing_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metrics.timestamp.isoformat(),
                metrics.session_id,
                metrics.model_id,
                metrics.provider,
                metrics.input_tokens,
                metrics.output_tokens,
                metrics.context_window_limit,
                metrics.utilization_percent,
                metrics.estimated_cost_usd,
                int(metrics.compression_applied),
                int(metrics.summarization_applied),
                metrics.messages_before,
                metrics.messages_after,
                metrics.processing_time_ms,
            ),
        )
        await conn.commit()


async def get_usage_by_session(
    session_id: str,
    days: int = 7,
    db_path: Path = CONTEXT_METRICS_DB_PATH,
) -> List[ContextUsageMetrics]:
    """Get context usage metrics for a specific session."""
    cutoff = datetime.now() - timedelta(days=days)

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            """
            SELECT timestamp, session_id, model_id, provider,
                   input_tokens, output_tokens, context_window_limit,
                   utilization_percent, estimated_cost_usd,
                   compression_applied, summarization_applied,
                   messages_before, messages_after, processing_time_ms
            FROM context_metrics
            WHERE session_id = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            """,
            (session_id, cutoff.isoformat()),
        )

        results = []
        async for row in cursor:
            results.append(
                ContextUsageMetrics(
                    timestamp=datetime.fromisoformat(row[0]),
                    session_id=row[1],
                    model_id=row[2],
                    provider=row[3],
                    input_tokens=row[4],
                    output_tokens=row[5],
                    context_window_limit=row[6],
                    utilization_percent=row[7],
                    estimated_cost_usd=row[8],
                    compression_applied=bool(row[9]),
                    summarization_applied=bool(row[10]),
                    messages_before=row[11],
                    messages_after=row[12],
                    processing_time_ms=row[13],
                )
            )

    return results


async def get_total_costs(
    days: int = 7,
    db_path: Path = CONTEXT_METRICS_DB_PATH,
) -> Dict[str, float]:
    """Get total estimated costs by provider for the last N days."""
    cutoff = datetime.now() - timedelta(days=days)

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            """
            SELECT provider, SUM(estimated_cost_usd) as total_cost
            FROM context_metrics
            WHERE timestamp >= ?
            GROUP BY provider
            ORDER BY total_cost DESC
            """,
            (cutoff.isoformat(),),
        )

        results = {}
        async for row in cursor:
            results[row[0]] = row[1]

    return results


async def get_usage_summary(
    days: int = 7,
    db_path: Path = CONTEXT_METRICS_DB_PATH,
) -> Dict[str, Any]:
    """Get a comprehensive summary of context usage metrics."""
    cutoff = datetime.now() - timedelta(days=days)

    async with aiosqlite.connect(db_path) as conn:
        # Total tokens by provider
        cursor = await conn.execute(
            """
            SELECT provider,
                   SUM(input_tokens) as total_input,
                   SUM(output_tokens) as total_output,
                   COUNT(*) as event_count,
                   AVG(utilization_percent) as avg_utilization
            FROM context_metrics
            WHERE timestamp >= ?
            GROUP BY provider
            """,
            (cutoff.isoformat(),),
        )

        by_provider: Dict[str, Any] = {}
        async for row in cursor:
            by_provider[row[0]] = {
                "total_input_tokens": row[1],
                "total_output_tokens": row[2],
                "event_count": row[3],
                "avg_utilization_percent": row[4],
            }

        # Optimization stats
        cursor = await conn.execute(
            """
            SELECT
                SUM(CASE WHEN compression_applied THEN 1 ELSE 0 END) as compressions,
                SUM(CASE WHEN summarization_applied THEN 1 ELSE 0 END) as summarizations,
                AVG(messages_before - messages_after) as avg_messages_reduced
            FROM context_metrics
            WHERE timestamp >= ?
            """,
            (cutoff.isoformat(),),
        )

        row = await cursor.fetchone()
        optimization_stats = {
            "total_compressions": row[0] or 0,
            "total_summarizations": row[1] or 0,
            "avg_messages_reduced": row[2] or 0.0,
        }

    return {
        "by_provider": by_provider,
        "total_costs_by_provider": await get_total_costs(db_path=db_path, days=days),
        "optimization_stats": optimization_stats,
        "period_days": days,
    }


async def cleanup_old_metrics(
    retention_days: int = 90,
    db_path: Path = CONTEXT_METRICS_DB_PATH,
) -> int:
    """Remove metrics older than retention period. Returns count deleted."""
    cutoff = datetime.now() - timedelta(days=retention_days)

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "DELETE FROM context_metrics WHERE timestamp < ?",
            (cutoff.isoformat(),),
        )
        await conn.commit()
        return cursor.rowcount
