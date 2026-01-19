from types import SimpleNamespace
from typing import Any

import pytest

import api.dependencies as dep_mod
from api.dependencies import get_agent, get_llm, get_vector_store


class _StubDocRetriever:
    def get_relevant_documents(self, query: str) -> list[Any]:
        return []


class _StubStore:
    def get_retriever(self):
        return _StubDocRetriever()


def test_get_vector_store_returns_none_on_exception(monkeypatch):
    class _Boom:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    get_vector_store.cache_clear()
    monkeypatch.setattr(dep_mod, "ChromaPropertyStore", _Boom)
    store = get_vector_store()
    assert store is None


def test_get_vector_store_caches_success(monkeypatch):
    class _OK:
        def __init__(self, *args, **kwargs):
            self.created = True

    get_vector_store.cache_clear()
    monkeypatch.setattr(dep_mod, "ChromaPropertyStore", _OK)
    s1 = get_vector_store()
    s2 = get_vector_store()
    assert s1 is s2


def test_get_llm_chooses_first_model_when_default_missing(monkeypatch):
    class _ModelInfo(SimpleNamespace):
        pass

    class _Provider:
        def list_models(self):
            return [_ModelInfo(id="m1")]

        def create_model(self, model_id, provider_name, temperature, max_tokens):
            return SimpleNamespace(id=model_id, provider=provider_name, t=temperature, max_tokens=max_tokens)

    import models.provider_factory as pf_mod
    monkeypatch.setattr(pf_mod.ModelProviderFactory, "get_provider", lambda name: _Provider())
    llm = get_llm()
    assert getattr(llm, "id", "") == "m1"


def test_get_llm_raises_when_no_models(monkeypatch):
    class _Provider:
        def list_models(self):
            return []

        def create_model(self, *args, **kwargs):
            return SimpleNamespace()

    import models.provider_factory as pf_mod
    monkeypatch.setattr(pf_mod.ModelProviderFactory, "get_provider", lambda name: _Provider())
    with pytest.raises(RuntimeError):
        get_llm()


def test_get_agent_requires_store(monkeypatch):
    with pytest.raises(RuntimeError):
        # Pass None store via manual call (dependency layer tested directly)
        get_agent(None, SimpleNamespace())


def test_get_agent_success(monkeypatch):
    def _mk_agent(**kwargs):
        return SimpleNamespace(agent=True, **kwargs)

    monkeypatch.setattr(dep_mod, "create_hybrid_agent", _mk_agent)
    agent = get_agent(_StubStore(), SimpleNamespace())
    assert getattr(agent, "agent", False)
