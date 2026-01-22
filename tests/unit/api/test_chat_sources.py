from types import SimpleNamespace

from langchain_core.documents import Document

from api.chat_sources import serialize_chat_sources


def test_serialize_chat_sources_truncates_items():
    docs = [
        Document(page_content="a", metadata={"id": "1"}),
        Document(page_content="b", metadata={"id": "2"}),
        Document(page_content="c", metadata={"id": "3"}),
    ]
    sources = serialize_chat_sources(
        docs,
        max_items=2,
        max_content_chars=100,
        max_total_bytes=10_000,
    )
    assert len(sources) == 2
    assert sources[0]["metadata"]["id"] == "1"
    assert sources[1]["metadata"]["id"] == "2"


def test_serialize_chat_sources_truncates_content_chars():
    docs = [Document(page_content="abcdef", metadata={"id": "1"})]
    sources = serialize_chat_sources(
        docs,
        max_items=10,
        max_content_chars=3,
        max_total_bytes=10_000,
    )
    assert sources[0]["content"] == "abc"


def test_serialize_chat_sources_respects_total_bytes_budget():
    docs = [
        Document(page_content="x" * 50, metadata={"id": "1"}),
        Document(page_content="y" * 50, metadata={"id": "2"}),
    ]
    sources = serialize_chat_sources(
        docs,
        max_items=10,
        max_content_chars=100,
        max_total_bytes=150,
    )
    assert len(sources) == 1
    assert sources[0]["metadata"]["id"] == "1"


def test_serialize_chat_sources_sanitizes_non_dict_metadata():
    docs = [SimpleNamespace(page_content="a", metadata=["not", "a", "dict"])]
    sources = serialize_chat_sources(
        docs,
        max_items=10,
        max_content_chars=100,
        max_total_bytes=10_000,
    )
    assert sources == [{"content": "a", "metadata": {"value": "['not', 'a', 'dict']"}}]

