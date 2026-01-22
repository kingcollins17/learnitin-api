"""Notification API endpoints."""

import traceback
from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.database.session import get_async_session
from app.common.deps import get_current_active_user
from app.common.responses import ApiResponse, success_response
from app.common.security import decode_access_token
from app.features.users.models import User
from .service import NotificationService
from .schemas import NotificationResponse, NotificationUpdate, NotificationCreate
from .websocket_manager import notification_manager
from app.common.events import event_bus, NotificationInAppPushEvent, InAppEventType
import random

router = APIRouter()


@router.get("/", response_model=ApiResponse[List[NotificationResponse]])
async def get_my_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get current user's notifications.
    """
    try:
        assert current_user.id
        service = NotificationService(session)
        notifications = await service.get_user_notifications(
            user_id=current_user.id, skip=skip, limit=limit
        )
        return success_response(
            data=notifications,
            details=f"Retrieved {len(notifications)} notification(s)",
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notifications: {str(e)}",
        )


@router.get("/unread-count", response_model=ApiResponse[int])
async def get_unread_count(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get count of unread notifications.
    """
    try:
        assert current_user.id
        service = NotificationService(session)
        count = await service.get_unread_count(user_id=current_user.id)
        return success_response(data=count)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch unread count: {str(e)}",
        )


@router.put("/{notification_id}/read", response_model=ApiResponse[NotificationResponse])
async def mark_as_read(
    notification_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Mark a notification as read.
    """
    try:
        assert current_user.id
        service = NotificationService(session)
        notification = await service.mark_as_read(
            notification_id=notification_id, user_id=current_user.id
        )
        return success_response(
            data=notification, details="Notification marked as read"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notification: {str(e)}",
        )


@router.put("/read-all", response_model=ApiResponse[int])
async def mark_all_as_read(
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Mark all notifications as read for current user.
    """
    try:
        assert current_user.id
        service = NotificationService(session)
        count = await service.mark_all_as_read(user_id=current_user.id)
        await session.commit()
        return success_response(data=count, details=f"Marked {count} items as read")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notifications: {str(e)}",
        )


@router.delete("/{notification_id}", response_model=ApiResponse[bool])
async def delete_notification(
    notification_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a notification.
    """
    try:
        assert current_user.id
        service = NotificationService(session)
        await service.delete_notification(
            notification_id=notification_id, user_id=current_user.id
        )
        await session.commit()
        return success_response(data=True, details="Notification deleted")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notification: {str(e)}",
        )


@router.post("/test-create", response_model=ApiResponse[NotificationResponse])
async def test_create_notification(
    notification_data: NotificationCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Unprotected endpoint to create a notification for testing.
    """
    try:
        service = NotificationService(session)
        notification = await service.create_notification(notification_data)
        await session.commit()
        return success_response(data=notification, details="Test notification created")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create test notification: {str(e)}",
        )


@router.get("/test-fire", response_model=ApiResponse[dict])
async def test_fire_notification(user_id: int):
    """
    Fire a random NotificationInAppPushEvent for testing.
    """
    titles = [
        "New Course Available",
        "Lesson Completed!",
        "Streak Updated",
        "Achievement Unlocked",
        "Audio Ready",
    ]
    messages = [
        "Check out our new course on FastAPI!",
        "Great job on completing your daily lesson.",
        "You've hit a 7-day streak! Keep it up.",
        "You've earned the 'Fast Learner' badge.",
        "Your lesson audio has been generated successfully.",
    ]
    types = ["info", "success", "warning", "error"]

    # Pick a random user ID. If there are active connections, pick one of them
    # so someone actually receives the event.
    active_users = list(notification_manager.active_connections.keys())

    event = NotificationInAppPushEvent(
        user_id=user_id,
        notification_id=random.randint(1000, 9999),
        title=random.choice(titles),
        message=random.choice(messages),
        type=random.choice(types),
        # in_app_event=random.choice(list(InAppEventType)),
        in_app_event=InAppEventType.AUDIO_READY,
        data={"lesson_id": random.randint(1, 100)},
    )

    event_bus.dispatch(event)

    return success_response(
        data={
            "user_id": user_id,
            "title": event.title,
            "message": event.message,
            "type": event.type,
            "in_app_event": event.in_app_event,
        },
        details="Random notification event emitted",
    )


@router.websocket("/ws")
async def notification_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time notifications.
    Expects a JWT token in the query parameters for authentication.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = int(user_id_str)

    # Accept connection and track it
    await notification_manager.connect(user_id, websocket)

    try:
        # Keep connection open until client disconnects or an error occurs
        while True:
            # We don't expect messages from the client yet, but we need to listen
            # to detect disconnection
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect(user_id, websocket)
    except Exception:
        notification_manager.disconnect(user_id, websocket)
        await websocket.close()
