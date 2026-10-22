from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(
        String,
        nullable=False,
        default="system"
    )  # 'job_search_completed', 'action_required', 'application_submitted', 'submission_failed', 'status_updated', 'system'

    read = Column(Boolean, default=False, index=True)
    link = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User", back_populates="notifications")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    notify_in_app_searches = Column(Boolean, default=True)
    notify_in_app_actions = Column(Boolean, default=True)
    notify_in_app_submissions = Column(Boolean, default=True)
    notify_in_app_failures = Column(Boolean, default=True)
    notify_email_digest = Column(Boolean, default=False)

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="notification_preferences")
