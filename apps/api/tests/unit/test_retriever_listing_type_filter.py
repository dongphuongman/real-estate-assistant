from unittest.mock import patch

from langchain_core.documents import Document

from data.schemas import ListingType, Property, PropertyCollection, PropertyType
from vector_store.chroma_store import ChromaPropertyStore
from vector_store.hybrid_retriever import HybridPropertyRetriever


def _store_docs_to_documents(store):
    """Convert cached store properties to LangChain Documents with metadata."""
    docs = []
    for d in store._documents:
        docs.append(Document(page_content=d.page_content, metadata=d.metadata))
    return docs


class FakeInnerRetriever:
    """Fake retriever that returns all store docs (filtering is done by the outer retriever)."""

    def __init__(self, docs):
        self._docs = docs

    def get_relevant_documents(self, query: str):
        return list(self._docs)

    def invoke(self, query: str):
        return self.get_relevant_documents(query)


def test_hybrid_retriever_filters_rent_vs_sale(tmp_path):
    with patch.object(ChromaPropertyStore, "_create_embeddings", return_value=None):
        store = ChromaPropertyStore(persist_directory=str(tmp_path))

    props = [
        Property(
            id="r1",
            city="Warsaw",
            price=5000,
            rooms=2,
            property_type=PropertyType.APARTMENT,
            listing_type=ListingType.RENT,
            description="balcony",
        ),
        Property(
            id="s1",
            city="Krakow",
            price=95000,
            rooms=3,
            property_type=PropertyType.APARTMENT,
            listing_type=ListingType.SALE,
            description="garage",
        ),
    ]
    coll = PropertyCollection(properties=props, total_count=len(props))
    store.add_property_collection(coll)

    all_docs = _store_docs_to_documents(store)
    store.get_retriever = lambda **kwargs: FakeInnerRetriever(all_docs)

    retr = HybridPropertyRetriever(vector_store=store, k=5, search_type="mmr")

    rent_docs = retr.invoke("for rent balcony")
    assert any(d.metadata.get("listing_type") == "rent" for d in rent_docs)
    assert all(d.metadata.get("listing_type") == "rent" for d in rent_docs)

    sale_docs = retr.invoke("for sale")
    assert any(d.metadata.get("listing_type") == "sale" for d in sale_docs)
    assert all(d.metadata.get("listing_type") == "sale" for d in sale_docs)
