from typing import Protocol, runtime_checkable, Dict, Any


@runtime_checkable
class LegalCheckService(Protocol):
    def analyze_contract(self, text: str) -> Dict[str, Any]:
        ...


class BasicLegalCheckService:
    def analyze_contract(self, text: str) -> Dict[str, Any]:
        return {"risks": [], "score": 0.0}

