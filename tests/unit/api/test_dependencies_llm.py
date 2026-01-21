import types

import pytest

import api.dependencies as deps
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
    llm = deps.get_llm()
    assert getattr(llm, "model_id", None) == "model-a"
    assert fake.created and fake.created[0]["model_id"] == "model-a"


def test_get_llm_raises_when_no_models(monkeypatch):
    settings.default_provider = "openai"
    settings.default_model = None
    fake = FakeProvider()
    fake._models = []
    monkeypatch.setattr(ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake)
    with pytest.raises(RuntimeError):
        _ = deps.get_llm()


def test_get_llm_uses_user_model_preferences(monkeypatch):
    settings.default_provider = "openai"
    settings.default_model = None

    fake = FakeProvider()
    monkeypatch.setattr(ModelProviderFactory, "get_provider", lambda name, config=None, use_cache=True: fake)

    class _Prefs:
        preferred_provider = "openai"
        preferred_model = "model-b"

    class _Mgr:
        def get_preferences(self, user_email: str):
            assert user_email == "u1@example.com"
            return _Prefs()

    monkeypatch.setattr(deps.user_model_preferences, "MODEL_PREFS_MANAGER", _Mgr())
    llm = deps.get_llm(x_user_email="u1@example.com")
    assert getattr(llm, "model_id", None) == "model-b"
    assert fake.created and fake.created[0]["model_id"] == "model-b"


def test_get_llm_falls_back_when_preferred_model_fails(monkeypatch):
    settings.default_provider = "ollama"
    settings.default_model = "model-a"

    created: list[dict] = []

    class FailingProvider(FakeProvider):
        def create_model(self, model_id, temperature, max_tokens, **kwargs):
            raise RuntimeError("bad model")

    class WorkingProvider(FakeProvider):
        def create_model(self, model_id, temperature, max_tokens, **kwargs):
            created.append({"model_id": model_id})
            return types.SimpleNamespace(model_id=model_id)

    failing = FailingProvider()
    working = WorkingProvider()

    def _get_provider(name, config=None, use_cache=True):
        return failing if name == "openai" else working

    monkeypatch.setattr(ModelProviderFactory, "get_provider", _get_provider)

    class _Prefs:
        preferred_provider = "openai"
        preferred_model = "bad"

    class _Mgr:
        def get_preferences(self, user_email: str):
            return _Prefs()

    monkeypatch.setattr(deps.user_model_preferences, "MODEL_PREFS_MANAGER", _Mgr())
    llm = deps.get_llm(x_user_email="u1@example.com")
    assert getattr(llm, "model_id", None) == "model-a"
    assert created and created[0]["model_id"] == "model-a"
