"""Slice 5/6 — Event-driven Hard Block dispatch tests.

Covers, without needing a live DB/Kafka/ntfy:
  1. LogPublisher — always-on fallback never raises
  2. NtfyPublisher — posts to the configured topic URL (httpx mocked)
  3. CompositePublisher — fans out to every sink; one failure doesn't block
     the others, but is still surfaced so the outbox relay retries
  4. get_publisher() factory — selects sinks based on settings
  5. Outbox write/drain — staging + publish + mark-published, with retry
     semantics on a failing sink (duck-typed fake DB session, matching the
     project's existing no-live-DB unit-test style)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.events.composite_publisher import CompositePublisher
from app.events.factory import get_publisher
from app.events.log_publisher import LogPublisher
from app.events.ntfy_publisher import NtfyPublisher
from app.events.outbox import drain_outbox_once, write_outbox_event
from app.events.publisher import EventPublisher

# ---------------------------------------------------------------------------
# LogPublisher
# ---------------------------------------------------------------------------


async def test_log_publisher_never_raises():
    await LogPublisher().publish("device.hardblock", {"session_id": "s1"})


# ---------------------------------------------------------------------------
# NtfyPublisher (httpx mocked — no real network call)
# ---------------------------------------------------------------------------


class _FakeResponse:
    status_code = 200


class _FakeAsyncClient:
    last_call: dict[str, Any] = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, content=None, headers=None):
        _FakeAsyncClient.last_call = {
            "url": url,
            "content": content,
            "headers": headers,
        }
        return _FakeResponse()


async def test_ntfy_publisher_posts_to_topic_url(monkeypatch):
    import app.events.ntfy_publisher as mod

    monkeypatch.setattr(mod.httpx, "AsyncClient", _FakeAsyncClient)

    publisher = NtfyPublisher(topic="mana-poct-hardblock-test")
    await publisher.publish(
        "device.hardblock",
        {
            "session_id": "s1",
            "device_serial": "SN-1",
            "system_action": "LOCKDOWN_DEVICE",
        },
    )

    assert (
        _FakeAsyncClient.last_call["url"] == "https://ntfy.sh/mana-poct-hardblock-test"
    )
    assert b"SN-1" in _FakeAsyncClient.last_call["content"]
    assert _FakeAsyncClient.last_call["headers"]["Priority"] == "urgent"

    # Title must be pure ASCII
    title = _FakeAsyncClient.last_call["headers"]["Title"]
    title.encode("ascii")  # raises if any non-ASCII slipped back in
    assert title == "MANA POCT - device.hardblock"


# ---------------------------------------------------------------------------
# CompositePublisher
# ---------------------------------------------------------------------------


@dataclass
class _SpyPublisher(EventPublisher):
    name: str
    calls: list[tuple[str, dict]] = field(default_factory=list)
    should_fail: bool = False

    async def publish(self, event_type: str, payload: dict) -> None:
        self.calls.append((event_type, payload))
        if self.should_fail:
            raise RuntimeError(f"{self.name} sink unavailable")


async def test_composite_publisher_fans_out_to_all_sinks():
    a, b = _SpyPublisher(name="a"), _SpyPublisher(name="b")
    composite = CompositePublisher([a, b])

    await composite.publish("device.hardblock", {"session_id": "s1"})

    assert a.calls == [("device.hardblock", {"session_id": "s1"})]
    assert b.calls == [("device.hardblock", {"session_id": "s1"})]


async def test_composite_publisher_one_failure_does_not_block_others():
    good, bad = _SpyPublisher(name="good"), _SpyPublisher(name="bad", should_fail=True)
    composite = CompositePublisher([bad, good])

    with pytest.raises(RuntimeError):
        await composite.publish("device.hardblock", {"session_id": "s1"})

    # The good sink still received the event despite the bad one raising.
    assert good.calls == [("device.hardblock", {"session_id": "s1"})]


# ---------------------------------------------------------------------------
# get_publisher() factory
# ---------------------------------------------------------------------------


def test_factory_defaults_to_log_only(monkeypatch):
    from app import config as config_mod

    monkeypatch.setattr(config_mod.settings, "NTFY_TOPIC", "")
    monkeypatch.setattr(config_mod.settings, "KAFKA_BOOTSTRAP_SERVERS", "")

    publisher = get_publisher()
    assert isinstance(publisher, LogPublisher)


def test_factory_adds_ntfy_when_configured(monkeypatch):
    from app import config as config_mod

    monkeypatch.setattr(config_mod.settings, "NTFY_TOPIC", "some-topic")
    monkeypatch.setattr(config_mod.settings, "KAFKA_BOOTSTRAP_SERVERS", "")

    publisher = get_publisher()
    assert isinstance(publisher, CompositePublisher)
    assert {p.name for p in publisher._publishers} == {"log", "ntfy"}


# ---------------------------------------------------------------------------
# Outbox write + drain (duck-typed fake AsyncSession — no live DB needed)
# ---------------------------------------------------------------------------


@dataclass
class _FakeEvent:
    id: str
    type: str
    payload: dict
    published: bool = False


class _FakeScalars:
    def __init__(self, items: list) -> None:
        self._items = items

    def all(self) -> list:
        return self._items


class _FakeResult:
    def __init__(self, items: list) -> None:
        self._items = items

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._items)


class _FakeDb:
    def __init__(self, events: list[_FakeEvent]) -> None:
        self._events = events
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, _stmt):
        pending = [e for e in self._events if not e.published]
        return _FakeResult(pending)

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1


def test_write_outbox_event_stages_a_row_via_db_add():
    db = _FakeDb(events=[])
    event = write_outbox_event(
        db, session_id="s1", event_type="device.hardblock", payload={"x": 1}
    )
    assert db.added == [event]
    assert event.session_id == "s1"
    assert event.type == "device.hardblock"
    assert event.published is False


async def test_drain_outbox_once_publishes_and_marks_published():
    events = [
        _FakeEvent(id="e1", type="device.hardblock", payload={"session_id": "s1"})
    ]
    db = _FakeDb(events=events)
    spy = _SpyPublisher(name="spy")

    count = await drain_outbox_once(db, spy)

    assert count == 1
    assert events[0].published is True
    assert spy.calls == [("device.hardblock", {"session_id": "s1"})]
    assert db.commits == 1


async def test_drain_outbox_once_leaves_failed_events_unpublished_for_retry():
    events = [
        _FakeEvent(id="e1", type="device.hardblock", payload={"session_id": "s1"})
    ]
    db = _FakeDb(events=events)
    failing = _SpyPublisher(name="failing", should_fail=True)

    count = await drain_outbox_once(db, failing)

    assert count == 0
    assert events[0].published is False  # left pending — next pass retries
    assert db.commits == 0


async def test_drain_outbox_once_is_a_noop_when_nothing_pending():
    db = _FakeDb(events=[])
    count = await drain_outbox_once(db, LogPublisher())
    assert count == 0
    assert db.commits == 0
