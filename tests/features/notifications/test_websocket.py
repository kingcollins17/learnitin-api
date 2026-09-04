"""Tests for notification WebSocket connection manager and endpoint."""

import pytest
from fastapi import status, WebSocketDisconnect

from app.features.notifications.ws_manager import NotificationWebSocketManager
from app.common.events.schemas import NotificationInAppPushEvent, NotificationMulticastPushEvent, InAppEventType


class DummyWebSocket:
    def __init__(self, fail_send=False):
        self.accepted = False
        self.closed = False
        self.close_code = None
        self.close_reason = None
        self.sent_json = []
        self.sent_text = []
        self.fail_send = fail_send

    async def accept(self):
        self.accepted = True

    async def close(self, code=1000, reason=None):
        self.closed = True
        self.close_code = code
        self.close_reason = reason

    async def send_json(self, data):
        if self.fail_send:
            raise WebSocketDisconnect()
        self.sent_json.append(data)

    async def send_text(self, data):
        if self.fail_send:
            raise WebSocketDisconnect()
        self.sent_text.append(data)


@pytest.fixture
def ws_manager():
    return NotificationWebSocketManager()


@pytest.fixture
def mock_websocket():
    return DummyWebSocket()


@pytest.mark.asyncio
async def test_connect(ws_manager, mock_websocket):
    user_id = 1
    await ws_manager.connect(user_id, mock_websocket)

    assert mock_websocket.accepted is True
    assert ws_manager.active_connections[user_id] == mock_websocket


@pytest.mark.asyncio
async def test_connect_replaces_existing(ws_manager, mock_websocket):
    user_id = 1
    old_ws = DummyWebSocket()

    await ws_manager.connect(user_id, old_ws)
    assert ws_manager.active_connections[user_id] == old_ws

    # New connection for same user
    await ws_manager.connect(user_id, mock_websocket)

    assert old_ws.closed is True
    assert old_ws.close_code == status.WS_1000_NORMAL_CLOSURE
    assert old_ws.close_reason == "Replaced by a new connection from user"
    assert ws_manager.active_connections[user_id] == mock_websocket


@pytest.mark.asyncio
async def test_disconnect(ws_manager, mock_websocket):
    user_id = 1
    await ws_manager.connect(user_id, mock_websocket)
    assert user_id in ws_manager.active_connections

    await ws_manager.disconnect(user_id, mock_websocket)
    assert user_id not in ws_manager.active_connections


@pytest.mark.asyncio
async def test_send_success(ws_manager, mock_websocket):
    user_id = 1
    await ws_manager.connect(user_id, mock_websocket)

    data = {"title": "Hello", "message": "World"}
    success = await ws_manager.send(user_id, data)

    assert success is True
    assert mock_websocket.sent_json == [data]


@pytest.mark.asyncio
async def test_send_unconnected_user(ws_manager):
    success = await ws_manager.send(999, {"title": "Hello"})
    assert success is False


@pytest.mark.asyncio
async def test_send_handles_disconnect(ws_manager):
    user_id = 1
    failing_ws = DummyWebSocket(fail_send=True)
    await ws_manager.connect(user_id, failing_ws)

    success = await ws_manager.send(user_id, {"title": "Hello"})

    assert success is False
    assert user_id not in ws_manager.active_connections


@pytest.mark.asyncio
async def test_broadcast(ws_manager):
    ws1 = DummyWebSocket()
    ws2 = DummyWebSocket()

    await ws_manager.connect(1, ws1)
    await ws_manager.connect(2, ws2)

    data = {"title": "Announcement"}
    await ws_manager.broadcast(data)

    assert ws1.sent_json == [data]
    assert ws2.sent_json == [data]


@pytest.mark.asyncio
async def test_handle_in_app_push_event(ws_manager, mock_websocket):
    user_id = 1
    await ws_manager.connect(user_id, mock_websocket)

    event = NotificationInAppPushEvent(
        user_id=user_id,
        notification_id=10,
        title="Audio Ready",
        message="Your audio is ready",
        type="info",
        in_app_event=InAppEventType.AUDIO_READY,
        data={"lesson_id": 5},
    )

    await ws_manager.handle_in_app_push_event(event)

    assert mock_websocket.sent_json == [{
        "id": 10,
        "title": "Audio Ready",
        "message": "Your audio is ready",
        "type": "info",
        "in_app_event": "audio_ready",
        "data": {"lesson_id": 5},
        "created_at": None,
    }]


@pytest.mark.asyncio
async def test_handle_multicast_push_event(ws_manager, mock_websocket):
    user_id = 1
    await ws_manager.connect(user_id, mock_websocket)

    event = NotificationMulticastPushEvent(
        user_ids=[1, 2, 3],
        title="Broadcast Alert",
        message="System update scheduled",
        type="warning",
        data={"version": "1.0"},
    )

    await ws_manager.handle_multicast_push_event(event)

    assert mock_websocket.sent_json == [{
        "title": "Broadcast Alert",
        "message": "System update scheduled",
        "type": "warning",
        "data": {"version": "1.0"},
    }]
