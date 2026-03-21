"""Filter presets API endpoints (Task #75: Advanced Filter Presets)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_active_user
from config.settings import get_settings
from db.database import get_db
from db.models import User
from db.repositories import FilterPresetRepository
from db.schemas import (
    FilterPresetCreate,
    FilterPresetListResponse,
    FilterPresetResponse,
    FilterPresetUpdate,
)

router = APIRouter(prefix="/filter-presets", tags=["Filter Presets"])
settings = get_settings()


@router.post(
    "",
    response_model=FilterPresetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a filter preset",
    description="Create a new filter preset for quick access to common searches.",
)
async def create_filter_preset(
    body: FilterPresetCreate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FilterPresetResponse:
    """Create a new filter preset."""
    repo = FilterPresetRepository(session)

    # Check preset limit
    current_count = await repo.count_by_user(user.id)
    if current_count >= settings.max_filter_presets_per_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum number of filter presets ({settings.max_filter_presets_per_user}) reached",
        )

    # If setting as default, unset other defaults first
    if body.is_default:
        current_default = await repo.get_default(user.id)
        if current_default:
            await repo.set_default(current_default, user.id)

    preset = await repo.create(
        user_id=user.id,
        name=body.name,
        description=body.description,
        filters=body.filters,
        is_default=body.is_default,
    )

    return FilterPresetResponse.model_validate(preset)


@router.get(
    "",
    response_model=FilterPresetListResponse,
    summary="List user's filter presets",
    description="Get all filter presets for the current authenticated user.",
)
async def list_filter_presets(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum presets to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FilterPresetListResponse:
    """Get all filter presets for the current user."""
    repo = FilterPresetRepository(session)
    presets = await repo.get_by_user(user.id, limit=limit, offset=offset)
    total = await repo.count_by_user(user.id)

    return FilterPresetListResponse(
        items=[FilterPresetResponse.model_validate(p) for p in presets],
        total=total,
    )


@router.get(
    "/default",
    response_model=FilterPresetResponse,
    summary="Get user's default preset",
    description="Get the default filter preset for the current user.",
)
async def get_default_preset(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FilterPresetResponse:
    """Get the user's default filter preset."""
    repo = FilterPresetRepository(session)
    preset = await repo.get_default(user.id)

    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No default filter preset found",
        )

    return FilterPresetResponse.model_validate(preset)


@router.get(
    "/{preset_id}",
    response_model=FilterPresetResponse,
    summary="Get a filter preset",
    description="Get a specific filter preset by ID.",
)
async def get_filter_preset(
    preset_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FilterPresetResponse:
    """Get a specific filter preset."""
    repo = FilterPresetRepository(session)
    preset = await repo.get_by_id(preset_id, user.id)

    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter preset not found",
        )

    return FilterPresetResponse.model_validate(preset)


@router.patch(
    "/{preset_id}",
    response_model=FilterPresetResponse,
    summary="Update a filter preset",
    description="Update a filter preset's name, description, or filters.",
)
async def update_filter_preset(
    preset_id: str,
    body: FilterPresetUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FilterPresetResponse:
    """Update a filter preset."""
    repo = FilterPresetRepository(session)
    preset = await repo.get_by_id(preset_id, user.id)

    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter preset not found",
        )

    update_data = body.model_dump(exclude_unset=True)

    # If setting as default, unset other defaults first
    if update_data.get("is_default"):
        await repo.set_default(preset, user.id)
        update_data.pop("is_default", None)  # Already handled by set_default

    preset = await repo.update(preset, **update_data)

    return FilterPresetResponse.model_validate(preset)


@router.delete(
    "/{preset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a filter preset",
    description="Permanently delete a filter preset.",
)
async def delete_filter_preset(
    preset_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a filter preset."""
    repo = FilterPresetRepository(session)
    preset = await repo.get_by_id(preset_id, user.id)

    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter preset not found",
        )

    await repo.delete(preset)


@router.post(
    "/{preset_id}/use",
    response_model=FilterPresetResponse,
    summary="Mark preset as used",
    description="Increment usage count when user applies a filter preset.",
)
async def mark_preset_used(
    preset_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FilterPresetResponse:
    """Increment usage count when user applies a filter preset."""
    repo = FilterPresetRepository(session)
    preset = await repo.get_by_id(preset_id, user.id)

    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter preset not found",
        )

    preset = await repo.increment_usage(preset)
    return FilterPresetResponse.model_validate(preset)


@router.post(
    "/{preset_id}/set-default",
    response_model=FilterPresetResponse,
    summary="Set preset as default",
    description="Set this preset as the default for the user.",
)
async def set_preset_default(
    preset_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FilterPresetResponse:
    """Set a filter preset as the default."""
    repo = FilterPresetRepository(session)
    preset = await repo.get_by_id(preset_id, user.id)

    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filter preset not found",
        )

    preset = await repo.set_default(preset, user.id)
    return FilterPresetResponse.model_validate(preset)
