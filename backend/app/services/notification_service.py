from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationPreference
from app.schemas.notification import NotificationPreferencesUpdate


class NotificationService:
    @staticmethod
    def get_or_create_preferences(db: Session, user_id: int) -> NotificationPreference:
        pref = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
        if not pref:
            pref = NotificationPreference(
                user_id=user_id,
                notify_in_app_searches=True,
                notify_in_app_actions=True,
                notify_in_app_submissions=True,
                notify_in_app_failures=True,
                notify_email_digest=False,
            )
            db.add(pref)
            db.commit()
            db.refresh(pref)
        return pref

    @staticmethod
    def update_preferences(
        db: Session,
        user_id: int,
        updates: NotificationPreferencesUpdate
    ) -> NotificationPreference:
        pref = NotificationService.get_or_create_preferences(db, user_id)
        if updates.notify_in_app_searches is not None:
            pref.notify_in_app_searches = updates.notify_in_app_searches
        if updates.notify_in_app_actions is not None:
            pref.notify_in_app_actions = updates.notify_in_app_actions
        if updates.notify_in_app_submissions is not None:
            pref.notify_in_app_submissions = updates.notify_in_app_submissions
        if updates.notify_in_app_failures is not None:
            pref.notify_in_app_failures = updates.notify_in_app_failures
        if updates.notify_email_digest is not None:
            pref.notify_email_digest = updates.notify_email_digest

        db.commit()
        db.refresh(pref)
        return pref

    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "system",
        link: Optional[str] = None
    ) -> Optional[Notification]:
        """Creates an in-app notification if user preferences permit."""
        pref = NotificationService.get_or_create_preferences(db, user_id)

        # Check user-configured notification preferences
        if notification_type == "job_search_completed" and not pref.notify_in_app_searches:
            return None
        if notification_type == "action_required" and not pref.notify_in_app_actions:
            return None
        if notification_type == "application_submitted" and not pref.notify_in_app_submissions:
            return None
        if notification_type == "submission_failed" and not pref.notify_in_app_failures:
            return None

        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            link=link,
            read=False
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        limit: int = 30
    ) -> Tuple[List[Notification], int]:
        query = (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        total = query.count()
        unread_count = (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.read == False)
            .count()
        )
        items = query.limit(limit).all()
        return items, unread_count

    @staticmethod
    def mark_as_read(db: Session, user_id: int, notification_id: int) -> bool:
        notif = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if not notif:
            return False
        notif.read = True
        db.commit()
        return True

    @staticmethod
    def mark_all_read(db: Session, user_id: int) -> int:
        updated = (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.read == False)
            .update({"read": True})
        )
        db.commit()
        return updated
