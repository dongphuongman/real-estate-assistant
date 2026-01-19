import types

import pytest

from api.dependencies import get_llm
from config.settings import settings
from models.provider_factory import ModelProviderFactory


class FakeProvider:
    def __init__(self, config=None):
        self.config = config or {}
        self._models = [
            types.SimpleNamespace(id="model-a"),
            types.SimpleNamespace(id="model-b"),
        ]
        self.created = []

    def list_models(self):
        return self._models

    def create_model(self, model_id, temperature, max_tokens, **kwargs):
        self.created.append(
            dict(model_id=model_id, temperature=temperature, max_tokens=max_tokens)
        )
        return types.SimpleNamespace(stream=True, model_id=model_id)


@pytest.fixture(autouse=True)
def _clear_factory_cache():
    ModelProviderFactory.clear_cache()
    yield
    ModelProviderFactory.clear_cache()


def test_get_llm_uses_default_provider_and_first_model(monkeypatch):
    settings.default_provider = "openai"
    settings.default_model = None
    fake = FakeProvider()
    monkeypatch.setattr(ModelProviderFactory, "_PROVIDERS", {"openai": lambda config=None: fake})
    monkeypatch.setattr(ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake)
    llm = get_llm()
    assert getattr(llm, "model_id", None) == "model-a"
    assert fake.created and fake.created[0]["model_id"] == "model-a"


def test_get_llm_raises_when_no_models(monkeypatch):
    settings.default_provider = "openai"
    settings.default_model = None
    fake = FakeProvider()
    fake._models = []
    monkeypatch.setattr(ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake)
    with pytest.raises(RuntimeError):
        _ = get_llm()
