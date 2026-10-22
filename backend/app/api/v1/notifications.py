from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
def get_notifications(
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves user's in-app notifications with total unread count."""
    items, unread_count = NotificationService.get_user_notifications(db, current_user.id, limit=limit)
    return NotificationListResponse(
        total=len(items),
        unread_count=unread_count,
        items=[NotificationResponse.model_validate(it) for it in items]
    )


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marks a specific notification as read."""
    success = NotificationService.mark_as_read(db, current_user.id, notification_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return {"message": "Notification marked as read", "id": notification_id}


@router.post("/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marks all user notifications as read."""
    count = NotificationService.mark_all_read(db, current_user.id)
    return {"message": "All notifications marked as read", "marked_count": count}


@router.get("/preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves user's notification preferences."""
    pref = NotificationService.get_or_create_preferences(db, current_user.id)
    return NotificationPreferencesResponse.model_validate(pref)


@router.put("/preferences", response_model=NotificationPreferencesResponse)
def update_notification_preferences(
    updates: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates user's notification preferences."""
    pref = NotificationService.update_preferences(db, current_user.id, updates)
    return NotificationPreferencesResponse.model_validate(pref)
