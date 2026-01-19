from types import SimpleNamespace

import pytest

from api.main import app, shutdown_event, startup_event


class _DummyScheduler:
    def __init__(self, *args, **kwargs):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


@pytest.mark.asyncio
async def test_startup_initializes_scheduler(monkeypatch):
    # Patch names used inside api.main
    import api.main as main_mod
    monkeypatch.setattr(main_mod, "EmailServiceFactory", SimpleNamespace(create_from_env=lambda: None))
    monkeypatch.setattr(main_mod, "NotificationScheduler", _DummyScheduler)
    monkeypatch.setattr(main_mod, "get_vector_store", lambda: None)

    await startup_event()

    assert isinstance(getattr(app.state, "scheduler", None), _DummyScheduler)
    assert app.state.scheduler.started is True


@pytest.mark.asyncio
async def test_shutdown_stops_scheduler(monkeypatch):
    # Ensure scheduler exists
    from api import main as main_mod

    main_mod.scheduler = _DummyScheduler()
    app.state.scheduler = main_mod.scheduler
    await shutdown_event()
    assert main_mod.scheduler.stopped is True
