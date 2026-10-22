from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    read: bool
    link: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    items: List[NotificationResponse]


class NotificationPreferencesResponse(BaseModel):
    notify_in_app_searches: bool
    notify_in_app_actions: bool
    notify_in_app_submissions: bool
    notify_in_app_failures: bool
    notify_email_digest: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferencesUpdate(BaseModel):
    notify_in_app_searches: Optional[bool] = None
    notify_in_app_actions: Optional[bool] = None
    notify_in_app_submissions: Optional[bool] = None
    notify_in_app_failures: Optional[bool] = None
    notify_email_digest: Optional[bool] = None
