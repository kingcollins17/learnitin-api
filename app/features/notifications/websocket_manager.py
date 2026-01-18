import logging
import json
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect, status
from app.common.events import (
    event_bus,
    AppEvent,
    NotificationInAppPushEvent,
)

logger = logging.getLogger(__name__)


class WebsocketManager:
    """
    Manages active WebSocket connections for real-time notifications.
    Enforces a strict one-connection-per-user policy.
    """

    def __init__(self):
        # user_id -> active WebSocket
        self.active_connections: Dict[int, WebSocket] = {}
        self._is_subscribed = False

    def subscribe_to_bus(self):
        """
        Subscribe the manager to the Event Bus.
        Should be called once during app initialization.
        """
        if not self._is_subscribed:
            # Main in-app push notifications
            event_bus.on(
                NotificationInAppPushEvent, self.handle_push_event
            )  # ty:ignore[no-matching-overload]
            self._is_subscribed = True
            logger.info("WebsocketManager subscribed to Event Bus")

    async def connect(self, user_id: int, websocket: WebSocket):
        """
        Accept a new connection and track it.
        Closes any existing connection for this user.
        """
        # Enforce one connection per user: close existing one if it exists
        if user_id in self.active_connections:
            old_socket = self.active_connections[user_id]
            try:
                await old_socket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="New connection established elsewhere",
                )
            except Exception:
                pass
            logger.info(
                f"Closed existing connection for user {user_id} to prioritize new one."
            )

        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(
            f"User {user_id} connected to notifications WebSocket. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, user_id: int, websocket: WebSocket):
        """Clean up connection tracking."""
        if user_id in self.active_connections:
            # Only remove if it's the SAME socket object
            if self.active_connections[user_id] == websocket:
                del self.active_connections[user_id]
        logger.debug(f"User {user_id} disconnected from notifications WebSocket")

    async def handle_push_event(self, event: AppEvent):
        """
        Handler for NOTIFICATION_IN_APP_PUSH events from the Event Bus.
        Dispatches the notification to the active connection for the target user.
        """
        logger.info(
            f"WebsocketManager.handle_push_event called with event: {event.event_type}"
        )
        try:
            payload = event.model_dump(mode="json")
            user_id = payload.get("user_id")
            logger.info(
                f"Event user_id: {user_id}. Active users: {list(self.active_connections.keys())}"
            )

            if user_id and user_id in self.active_connections:
                logger.info(f"Sending WS message to user {user_id}")
                socket = self.active_connections[user_id]
                # Include event type in the payload for the client
                message_data = {**payload, "event_type": event.event_type}
                message = json.dumps(message_data)
                try:
                    await socket.send_text(message)
                except Exception as e:
                    logger.error(f"Failed to send WS message to user {user_id}: {e}")
                    # We don't manually delete here; the socket loop in the router
                    # will catch the error and call disconnect()
        except Exception as e:
            logger.error(f"Error in NotificationManager.handle_push_event: {e}")


# Singleton instance
notification_manager = WebsocketManager()
