"""
PropertyListingStub for deterministic property data testing.

Provides configurable property responses without database or network access.
"""

from typing import Any, Dict, List, Optional

from data.schemas import Property, PropertyCollection, PropertyType
from mcp.config import MCPEdition
from mcp.result import MCPConnectorResult
from mcp.stubs.base_stub import MCPStub


class PropertyListingStub(MCPStub[PropertyCollection]):
    """
    Stub for property listing data operations.

    Provides deterministic property data for testing without
    requiring database or external API access.

    Attributes:
        name: "property_listing_stub"
        display_name: "Property Listing Stub (Testing)"

    Operations:
        - get_all: Return all properties
        - get_by_id: Get property by ID
        - search: Filter properties by criteria
        - count: Return property count

    Example:
        stub = PropertyListingStub(properties=[
            Property(id="1", city="Krakow", rooms=2, ...),
            Property(id="2", city="Warsaw", rooms=3, ...),
        ])

        # Get all properties
        result = await stub.execute("get_all", {})
        assert result.success
        assert len(result.data.properties) == 2

        # Search by city
        result = await stub.execute("search", {"city": "Krakow"})
        assert len(result.data.properties) == 1
    """

    name = "property_listing_stub"
    display_name = "Property Listing Stub (Testing)"
    description = "Stub for property listing data operations"
    requires_api_key = False
    allowlisted = True
    min_edition = MCPEdition.COMMUNITY
    supports_streaming = False

    def __init__(
        self,
        properties: Optional[List[Property]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the property listing stub.

        Args:
            properties: Initial list of properties
            **kwargs: Additional arguments for MCPStub
        """
        super().__init__(**kwargs)
        self._properties: List[Property] = properties or []

    def set_properties(self, properties: List[Property]) -> None:
        """
        Set the property list.

        Args:
            properties: List of properties to use
        """
        self._properties = properties

    def add_property(self, property: Property) -> None:
        """
        Add a property to the list.

        Args:
            property: Property to add
        """
        self._properties.append(property)

    async def execute(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> MCPConnectorResult[PropertyCollection]:
        """
        Execute a property operation.

        Args:
            operation: Operation to execute
            params: Operation parameters

        Returns:
            MCPConnectorResult with PropertyCollection
        """
        await self._simulate_latency()

        self._call_count += 1

        # Check for queued errors first
        if self._error_queue:
            error = self._error_queue.popleft()
            result = MCPConnectorResult.error_result(
                errors=[error],
                connector_name=self.name,
                operation=operation,
            )
            self._record_call(operation, params, kwargs, result=result)
            return result

        # Route to operation handler
        handler = self._get_operation_handler(operation)
        try:
            data = handler(params or {})
            result = MCPConnectorResult.success_result(
                data=data,
                connector_name=self.name,
                operation=operation,
                metadata={"stub": True},
            )
            self._record_call(operation, params, kwargs, result=result)
            return result
        except Exception as e:
            result = MCPConnectorResult.error_result(
                errors=[str(e)],
                connector_name=self.name,
                operation=operation,
            )
            self._record_call(operation, params, kwargs, error=str(e))
            return result

    def _get_operation_handler(self, operation: str):
        """Get the handler for an operation."""
        handlers = {
            "get_all": self._op_get_all,
            "get_by_id": self._op_get_by_id,
            "search": self._op_search,
            "count": self._op_count,
            "filter": self._op_search,  # Alias
        }
        if operation not in handlers:
            raise ValueError(f"Unknown operation: {operation}")
        return handlers[operation]

    def _op_get_all(self, params: Dict[str, Any]) -> PropertyCollection:
        """Return all properties."""
        return PropertyCollection(
            properties=self._properties,
            total_count=len(self._properties),
            source="stub",
        )

    def _op_get_by_id(self, params: Dict[str, Any]) -> PropertyCollection:
        """Get property by ID."""
        property_id = params.get("id")
        if not property_id:
            raise ValueError("Missing required parameter: id")

        for prop in self._properties:
            if prop.id == property_id:
                return PropertyCollection(
                    properties=[prop],
                    total_count=1,
                    source="stub",
                )

        return PropertyCollection(
            properties=[],
            total_count=0,
            source="stub",
        )

    def _op_search(self, params: Dict[str, Any]) -> PropertyCollection:
        """Search/filter properties by criteria."""
        results = []

        for prop in self._properties:
            if self._matches_criteria(prop, params):
                results.append(prop)

        return PropertyCollection(
            properties=results,
            total_count=len(results),
            source="stub",
        )

    def _op_count(self, params: Dict[str, Any]) -> PropertyCollection:
        """Return count (as empty collection with total_count set)."""
        # Apply filters if provided
        if params:
            filtered = self._op_search(params)
            return PropertyCollection(
                properties=[],
                total_count=filtered.total_count,
                source="stub",
            )

        return PropertyCollection(
            properties=[],
            total_count=len(self._properties),
            source="stub",
        )

    def _matches_criteria(self, prop: Property, criteria: Dict[str, Any]) -> bool:
        """Check if property matches search criteria."""
        # City filter
        if "city" in criteria:
            if prop.city.lower() != criteria["city"].lower():
                return False

        # Room count filters
        if "min_rooms" in criteria and prop.rooms is not None:
            if prop.rooms < criteria["min_rooms"]:
                return False
        if "max_rooms" in criteria and prop.rooms is not None:
            if prop.rooms > criteria["max_rooms"]:
                return False

        # Price filters
        if "min_price" in criteria and prop.price is not None:
            if prop.price < criteria["min_price"]:
                return False
        if "max_price" in criteria and prop.price is not None:
            if prop.price > criteria["max_price"]:
                return False

        # Area filters
        if "min_area" in criteria and prop.area_sqm is not None:
            if prop.area_sqm < criteria["min_area"]:
                return False
        if "max_area" in criteria and prop.area_sqm is not None:
            if prop.area_sqm > criteria["max_area"]:
                return False

        # Property type filter
        if "property_type" in criteria:
            expected = criteria["property_type"]
            if isinstance(expected, str):
                expected = PropertyType(expected)
            if prop.property_type != expected:
                return False

        # Boolean filters
        if criteria.get("has_parking") and not prop.has_parking:
            return False
        if criteria.get("has_garden") and not prop.has_garden:
            return False
        if criteria.get("has_elevator") and not prop.has_elevator:
            return False

        return True

    def reset(self) -> None:
        """Reset stub to initial state."""
        super().reset()
        # Keep properties on reset for convenience
