from typing import Protocol, runtime_checkable, Dict, Any


@runtime_checkable
class DataEnrichmentService(Protocol):
    def enrich(self, address: str) -> Dict[str, Any]:
        ...


class BasicDataEnrichmentService:
    def enrich(self, address: str) -> Dict[str, Any]:
        return {}

