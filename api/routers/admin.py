import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from api.dependencies import get_vector_store
from api.models import HealthCheck, IngestRequest, IngestResponse, ReindexRequest, ReindexResponse
from config.settings import settings
from data.csv_loader import DataLoaderCsv
from data.schemas import Property, PropertyCollection
from utils.property_cache import load_collection, save_collection
from vector_store.chroma_store import ChromaPropertyStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin"])

@router.post("/admin/ingest", response_model=IngestResponse)
async def ingest_data(request: IngestRequest):
    """
    Trigger data ingestion from URLs.
    Downloads CSVs, processes them, and saves to local cache.
    Does NOT automatically reindex vector store (call /reindex for that).
    """
    urls = request.file_urls or settings.default_datasets
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided and no defaults configured")
    
    try:
        all_properties = []
        errors = []
        
        for url in urls:
            try:
                loader = DataLoaderCsv(url)
                df = loader.load_df()
                df_formatted = loader.load_format_df(df)
                
                # Convert to Property objects
                # We use to_dict('records') and validate with Pydantic
                records = df_formatted.to_dict(orient="records")
                props = []
                for record in records:
                    try:
                        props.append(Property(**record))
                    except Exception:
                        # Skip invalid records but log?
                        pass
                        
                all_properties.extend(props)
                logger.info(f"Loaded {len(props)} properties from {url}")
            except Exception as e:
                msg = f"Failed to load {url}: {str(e)}"
                logger.error(msg)
                errors.append(msg)
            
        if not all_properties:
            raise HTTPException(status_code=500, detail="No properties could be loaded")
            
        collection = PropertyCollection(properties=all_properties, total_count=len(all_properties))
        save_collection(collection)
        
        return IngestResponse(
            message="Ingestion successful",
            properties_processed=len(all_properties),
            errors=errors
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/admin/reindex", response_model=ReindexResponse)
async def reindex_data(
    request: ReindexRequest,
    store: Annotated[ChromaPropertyStore, Depends(get_vector_store)],
):
    """
    Reindex data from cache to vector store.
    """
    collection = load_collection()
    if not collection:
        raise HTTPException(
            status_code=404,
            detail="No data in cache. Run ingestion first.",
        )
        
    try:
        # In a real scenario, we might want to clear the collection first if
        # request.clear_existing is True.
        # Currently ChromaPropertyStore doesn't expose a clear method publicly in the
        # interface we checked.
        # We will just add documents (upsert behavior usually).
        
        if not store:
            raise HTTPException(status_code=503, detail="Vector store unavailable")

        store.add_documents(collection.properties)
        
        return ReindexResponse(
            message="Reindexing successful",
            count=len(collection.properties)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reindexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/admin/health", response_model=HealthCheck)
async def admin_health_check(
    store: Annotated[ChromaPropertyStore, Depends(get_vector_store)],
):
    """
    Detailed health check for admin.
    """
    status = "healthy"
    
    # Check cache
    if not load_collection():
        status = "degraded (no data cache)"
        
    # Check vector store
    if not store:
        status = "degraded (vector store unavailable)"
        
    return HealthCheck(status=status, version=settings.version)

@router.get("/admin/metrics", response_model=dict)
async def admin_metrics(request: Request):
    """
    Return simple API metrics.
    """
    try:
        metrics = getattr(request.app.state, "metrics", {})
        return dict(metrics)
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
