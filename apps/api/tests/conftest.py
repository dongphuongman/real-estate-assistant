"""
Pytest configuration and shared fixtures.
"""

import importlib.util
import os
import sys
import types

import pytest
from langchain_core.documents import Document

from agents.query_analyzer import QueryAnalyzer
from data.schemas import Property, PropertyCollection, PropertyType
from vector_store.reranker import PropertyReranker


def _install_stub_module(module_name: str, attrs: dict[str, object] | None = None) -> None:
    if module_name in sys.modules:
        return
    module = types.ModuleType(module_name)
    if module_name == "odf":
        module.__path__ = []
    if attrs:
        for key, value in attrs.items():
            setattr(module, key, value)
    sys.modules[module_name] = module


def _ensure_optional_excel_modules() -> None:
    if importlib.util.find_spec("xlrd") is None:
        _install_stub_module("xlrd", {"open_workbook": lambda *_args, **_kwargs: None})
    if importlib.util.find_spec("odf") is None:
        _install_stub_module("odf")
    if importlib.util.find_spec("odf.opendocument") is None:
        _install_stub_module("odf.opendocument", {"load": lambda *_args, **_kwargs: None})


def pytest_configure() -> None:
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ["API_ACCESS_KEY"] = "dev-secret-key"
    _ensure_optional_excel_modules()


def pytest_asyncio_mode() -> str:
    """Set pytest-asyncio mode to auto for async test support."""
    return "auto"


@pytest.fixture
def query_analyzer():
    """Fixture for query analyzer."""
    return QueryAnalyzer()


@pytest.fixture
def sample_properties():
    """Fixture for sample property data."""
    properties = [
        Property(
            id="prop1",
            city="Krakow",
            rooms=2,
            bathrooms=1,
            price=950,
            area_sqm=55,
            has_parking=True,
            has_garden=False,
            property_type=PropertyType.APARTMENT,
            source_url="http://example.com/1",
        ),
        Property(
            id="prop2",
            city="Krakow",
            rooms=2,
            bathrooms=1,
            price=890,
            area_sqm=48,
            has_parking=False,
            has_garden=True,
            property_type=PropertyType.APARTMENT,
            source_url="http://example.com/2",
        ),
        Property(
            id="prop3",
            city="Warsaw",
            rooms=3,
            bathrooms=2,
            price=1350,
            area_sqm=75,
            has_parking=True,
            has_garden=False,
            property_type=PropertyType.APARTMENT,
            source_url="http://example.com/3",
        ),
        Property(
            id="prop4",
            city="Krakow",
            rooms=1,
            bathrooms=1,
            price=650,
            area_sqm=35,
            has_parking=False,
            has_garden=False,
            property_type=PropertyType.STUDIO,
            source_url="http://example.com/4",
        ),
        Property(
            id="prop5",
            city="Warsaw",
            rooms=2,
            bathrooms=1,
            price=1100,
            area_sqm=60,
            has_parking=True,
            has_garden=True,
            property_type=PropertyType.APARTMENT,
            source_url="http://example.com/5",
        ),
    ]
    return PropertyCollection(properties=properties, total_count=5)


@pytest.fixture
def sample_documents(sample_properties):
    """Fixture for sample documents from properties."""
    documents = []
    for prop in sample_properties.properties:
        doc = Document(
            page_content=prop.to_search_text(),
            metadata=prop.to_dict(),
        )
        documents.append(doc)
    return documents


@pytest.fixture
def reranker():
    """Fixture for property reranker."""
    return PropertyReranker()
