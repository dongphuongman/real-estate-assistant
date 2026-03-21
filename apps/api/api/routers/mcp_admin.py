"""
MCP Allowlist Admin API Router.

Provides endpoints for managing and monitoring MCP connector allowlist.
This is part of Task #68: MCP Allowlist Governance.

Endpoints:
- GET /api/v1/mcp/allowlist - List current allowlist
- POST /api/v1/mcp/allowlist - Add connector to allowlist
- DELETE /api/v1/mcp/allowlist/{name} - Remove from allowlist
- GET /api/v1/mcp/allowlist/violations - List violations for audit
- POST /api/v1/mcp/allowlist/reload - Reload from YAML
- GET /api/v1/mcp/connectors - List all connectors with allowlist status
- GET /api/v1/mcp/health - Health check all connectors
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth import get_api_key
from mcp import (
    AllowlistConfig,
    AllowlistEntry,
    MCPConnectorRegistry,
    MCPEdition,
    get_allowlist_validator,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mcp",
    tags=["MCP Admin"],
    dependencies=[Depends(get_api_key)],
)


# ============================================================================
# Pydantic Models for API
# ============================================================================


class MCPAllowlistEntryResponse(BaseModel):
    """Response model for allowlist entry."""

    name: str
    display_name: str
    description: str = ""
    enabled: bool = True
    edition: str = "community"
    added_at: Optional[str] = None
    added_by: str = "system"


class MCPAllowlistResponse(BaseModel):
    """Response model for allowlist listing."""

    edition: str
    allowlist: List[MCPAllowlistEntryResponse]
    restricted: List[MCPAllowlistEntryResponse]
    total_allowed: int
    total_restricted: int
    loaded_at: Optional[str] = None
    config_path: Optional[str] = None


class MCPAllowlistAddRequest(BaseModel):
    """Request model for adding connector to allowlist."""

    name: str = Field(..., description="Connector identifier")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field("", description="Connector description")
    edition: str = Field("community", description="Edition level")
    added_by: str = Field("admin", description="Who added this entry")


class MCPViolationResponse(BaseModel):
    """Response model for allowlist violation."""

    timestamp: str
    connector: str
    operation: str
    context: Dict[str, Any] = Field(default_factory=dict)
    config_edition: str


class MCPViolationsListResponse(BaseModel):
    """Response model for violations list."""

    violations: List[MCPViolationResponse]
    total: int


class MCPConnectorInfoResponse(BaseModel):
    """Response model for connector info."""

    name: str
    display_name: str
    description: str = ""
    enabled: bool = True
    edition: str
    status: str  # "allowlisted" or "restricted"
    accessible_in_ce: bool
    registered: bool = False
    has_instance: bool = False


class MCPConnectorsListResponse(BaseModel):
    """Response model for connectors list."""

    connectors: List[MCPConnectorInfoResponse]
    edition: str
    total: int


class MCPHealthResponse(BaseModel):
    """Response model for MCP health check."""

    status: str  # "healthy", "degraded", "unhealthy"
    edition: str
    connectors_checked: int
    results: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class MCPReloadResponse(BaseModel):
    """Response model for allowlist reload."""

    message: str
    allowlist_count: int
    restricted_count: int
    edition: str
    loaded_at: str


# ============================================================================
# Helper Functions
# ============================================================================


def _entry_to_response(entry: AllowlistEntry) -> MCPAllowlistEntryResponse:
    """Convert AllowlistEntry to response model."""
    return MCPAllowlistEntryResponse(
        name=entry.name,
        display_name=entry.display_name,
        description=entry.description,
        enabled=entry.enabled,
        edition=entry.edition.value,
        added_at=entry.added_at.isoformat() if entry.added_at else None,
        added_by=entry.added_by,
    )


def _config_to_response(config: AllowlistConfig) -> MCPAllowlistResponse:
    """Convert AllowlistConfig to response model."""
    return MCPAllowlistResponse(
        edition=config.edition.value,
        allowlist=[_entry_to_response(e) for e in config.allowlist],
        restricted=[_entry_to_response(e) for e in config.restricted],
        total_allowed=len([e for e in config.allowlist if e.enabled]),
        total_restricted=len(config.restricted),
        loaded_at=config.loaded_at.isoformat() if config.loaded_at else None,
        config_path=str(config.config_path) if config.config_path else None,
    )


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/allowlist", response_model=MCPAllowlistResponse)
async def get_allowlist():
    """
    Get current MCP connector allowlist configuration.

    Returns the full allowlist including:
    - Current edition
    - Allowlisted connectors (CE accessible)
    - Restricted connectors (PRO/Enterprise only)
    """
    validator = get_allowlist_validator()
    config = validator.config
    return _config_to_response(config)


@router.post(
    "/allowlist",
    response_model=MCPAllowlistEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_allowlist(request: MCPAllowlistAddRequest):
    """
    Add a connector to the allowlist at runtime.

    Note: This modifies the in-memory config only.
    For persistence, update the YAML file directly.
    """
    validator = get_allowlist_validator()

    # Parse edition
    try:
        edition = MCPEdition(request.edition.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid edition: {request.edition}. "
            f"Valid: community, pro, enterprise",
        ) from None

    entry = validator.add_connector(
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        edition=edition,
        added_by=request.added_by,
    )

    logger.info(
        f"Added connector '{request.name}' to allowlist via API by {request.added_by}"
    )

    return _entry_to_response(entry)


@router.delete("/allowlist/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_allowlist(name: str):
    """
    Remove a connector from the allowlist.

    Note: This modifies the in-memory config only.
    For persistence, update the YAML file directly.
    """
    validator = get_allowlist_validator()
    removed = validator.remove_connector(name)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector '{name}' not found in allowlist",
        )

    logger.info(f"Removed connector '{name}' from allowlist via API")


@router.get("/allowlist/violations", response_model=MCPViolationsListResponse)
async def get_violations():
    """
    Get all logged allowlist violations for audit.

    Returns violation records including:
    - Timestamp
    - Connector name
    - Operation attempted
    - Context and edition info
    """
    validator = get_allowlist_validator()
    violations = validator.get_violations()

    return MCPViolationsListResponse(
        violations=[
            MCPViolationResponse(**v) for v in violations
        ],
        total=len(violations),
    )


@router.delete("/allowlist/violations", status_code=status.HTTP_204_NO_CONTENT)
async def clear_violations():
    """
    Clear all logged allowlist violations.

    Use with caution - this removes audit trail.
    """
    validator = get_allowlist_validator()
    validator.clear_violations()
    logger.info("Allowlist violations cleared via API")


@router.post("/allowlist/reload", response_model=MCPReloadResponse)
async def reload_allowlist():
    """
    Reload allowlist configuration from YAML file.

    Use this after updating the YAML file to apply changes
    without restarting the application.
    """
    validator = get_allowlist_validator()
    config = validator.reload_config()

    # Also update registry
    MCPConnectorRegistry.set_edition(config.edition)
    MCPConnectorRegistry.set_allowlist(config.get_allowlist_names())

    logger.info("Allowlist reloaded from YAML via API")

    return MCPReloadResponse(
        message="Allowlist reloaded successfully",
        allowlist_count=len(config.allowlist),
        restricted_count=len(config.restricted),
        edition=config.edition.value,
        loaded_at=config.loaded_at.isoformat(),
    )


@router.get("/connectors", response_model=MCPConnectorsListResponse)
async def list_connectors():
    """
    List all connectors with allowlist status.

    Combines information from:
    - Allowlist config (YAML)
    - Registry (registered connectors)
    """
    validator = get_allowlist_validator()
    config = validator.config

    # Get all known connectors
    all_connectors_info = validator.get_all_connectors_info()

    # Add registry status
    result = []
    for name, info in all_connectors_info.items():
        registered = name in MCPConnectorRegistry.list_connectors(
            include_non_accessible=True
        )
        has_instance = name in MCPConnectorRegistry._instances

        result.append(
            MCPConnectorInfoResponse(
                name=name,
                display_name=info.get("display_name", name),
                description=info.get("description", ""),
                enabled=info.get("enabled", True),
                edition=info.get("edition", "community"),
                status=info.get("status", "unknown"),
                accessible_in_ce=info.get("accessible_in_ce", False),
                registered=registered,
                has_instance=has_instance,
            )
        )

    return MCPConnectorsListResponse(
        connectors=result,
        edition=config.edition.value,
        total=len(result),
    )


@router.get("/health", response_model=MCPHealthResponse)
async def health_check():
    """
    Health check for MCP connector system.

    Returns:
    - Overall status (healthy/degraded/unhealthy)
    - Health check results for each instantiated connector
    """
    validator = get_allowlist_validator()
    config = validator.config

    # Run health checks on all instantiated connectors

    health_results = {}
    try:
        health_results = await MCPConnectorRegistry.health_check_all()
    except Exception as e:
        logger.error(f"Health check failed: {e}")

    # Determine overall status
    total = len(health_results)
    if total == 0:
        overall_status = "healthy"  # No connectors = healthy
    else:
        successful = sum(1 for r in health_results.values() if r.success)
        if successful == total:
            overall_status = "healthy"
        elif successful > 0:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

    return MCPHealthResponse(
        status=overall_status,
        edition=config.edition.value,
        connectors_checked=total,
        results={
            name: {"success": r.success, "errors": r.errors}
            for name, r in health_results.items()
        },
        timestamp=datetime.utcnow().isoformat(),
    )
