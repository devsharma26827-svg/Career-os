import logging
import re
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Optional, Tuple

from app.core.config import settings
from app.models.application import ApplicationAuditLog
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EmailDeliveryService:
    """
    Handles consent-based recruiter outreach emails.
    Enforces server-side credentials, recipient address validation, rate limiting,
    duplicate prevention, and honest status reporting.
    Never fabricates delivery if credentials are not configured.
    """

    EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")

    @classmethod
    def is_configured(cls) -> bool:
        """
        Checks whether SMTP sending credentials are configured on the server.
        """
        if settings.EMAIL_PROVIDER == "mock":
            return True
        return bool(settings.SMTP_HOST and settings.SMTP_USER)

    @classmethod
    def validate_recipient(cls, email: Optional[str]) -> Tuple[bool, Optional[str]]:
        if not email or not email.strip():
            return False, "Recipient email address is missing."
        email = email.strip()
        if not cls.EMAIL_REGEX.match(email):
            return False, f"Invalid email format: '{email}'."
        return True, None

    @classmethod
    def check_duplicate_and_rate_limit(
        cls,
        db: Session,
        user_id: int,
        job_id: Optional[int],
        recipient_email: str
    ) -> Tuple[bool, Optional[str]]:
        # 1. Duplicate check: has user already sent an email to this recipient for this job?
        if job_id:
            duplicate_log = (
                db.query(ApplicationAuditLog)
                .filter(
                    ApplicationAuditLog.user_id == user_id,
                    ApplicationAuditLog.job_id == job_id,
                    ApplicationAuditLog.action == "email_sent",
                    ApplicationAuditLog.status == "success",
                    ApplicationAuditLog.recipient == recipient_email.strip().lower()
                )
                .first()
            )
            if duplicate_log:
                return False, (
                    f"Duplicate outreach prevented: You already sent an email to {recipient_email} "
                    f"for this position on {duplicate_log.created_at.strftime('%Y-%m-%d %H:%M')}. "
                    "Repeated messages can harm your professional reputation."
                )

        # 2. Hourly rate limit check
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_sends = (
            db.query(ApplicationAuditLog)
            .filter(
                ApplicationAuditLog.user_id == user_id,
                ApplicationAuditLog.action == "email_sent",
                ApplicationAuditLog.status == "success",
                ApplicationAuditLog.created_at >= one_hour_ago
            )
            .count()
        )

        if recent_sends >= settings.EMAIL_RATE_LIMIT_PER_HOUR:
            return False, (
                f"Rate limit exceeded: You have sent {recent_sends} emails in the last hour. "
                f"Max allowed is {settings.EMAIL_RATE_LIMIT_PER_HOUR}/hour to comply with anti-spam standards."
            )

        return True, None

    @classmethod
    def send_email(
        cls,
        db: Session,
        user_id: int,
        job_id: Optional[int],
        workspace_id: Optional[int],
        recipient_email: str,
        subject: str,
        body: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Sends recruiter outreach email with strict authorization, audit logging,
        and honest error reporting.
        """
        recipient_email = (recipient_email or "").strip().lower()

        # Step 1: Validate recipient format
        is_valid, validation_err = cls.validate_recipient(recipient_email)
        if not is_valid:
            cls._log_audit(
                db=db,
                user_id=user_id,
                job_id=job_id,
                workspace_id=workspace_id,
                action="email_failed",
                status="failed",
                recipient=recipient_email,
                details=validation_err,
                idempotency_key=idempotency_key
            )
            return {
                "status": "failed",
                "message": validation_err or "Invalid recipient",
                "error": validation_err
            }

        # Step 2: Check duplicate outreach and rate limit
        allowed, limit_err = cls.check_duplicate_and_rate_limit(
            db=db,
            user_id=user_id,
            job_id=job_id,
            recipient_email=recipient_email
        )
        if not allowed:
            cls._log_audit(
                db=db,
                user_id=user_id,
                job_id=job_id,
                workspace_id=workspace_id,
                action="email_duplicate_blocked",
                status="cancelled",
                recipient=recipient_email,
                details=limit_err,
                idempotency_key=idempotency_key
            )
            return {
                "status": "duplicate_prevented",
                "message": limit_err or "Outreach blocked by anti-spam guard.",
                "error": limit_err
            }

        # Step 3: Check server-side credentials
        if not cls.is_configured():
            msg = (
                "SMTP email credentials are not configured on this server. "
                "The email was NOT sent. Please configure SMTP_HOST and SMTP_USER in .env, "
                "or use the 'Copy Email' button in the workspace to send directly from your personal client."
            )
            cls._log_audit(
                db=db,
                user_id=user_id,
                job_id=job_id,
                workspace_id=workspace_id,
                action="email_not_configured",
                status="not_configured",
                recipient=recipient_email,
                details=msg,
                idempotency_key=idempotency_key
            )
            return {
                "status": "not_configured",
                "message": msg,
                "error": "SMTP not configured"
            }

        # Step 4: Dispatch email via SMTP or Mock provider
        if settings.EMAIL_PROVIDER == "mock":
            # Testing / mock delivery
            cls._log_audit(
                db=db,
                user_id=user_id,
                job_id=job_id,
                workspace_id=workspace_id,
                action="email_sent",
                status="success",
                recipient=recipient_email,
                details=f"Mock email delivered successfully to {recipient_email}. Subject: '{subject}'",
                idempotency_key=idempotency_key
            )
            return {
                "status": "sent",
                "message": f"Email successfully delivered to {recipient_email} (Test Mode).",
                "error": None
            }

        try:
            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
            msg["To"] = recipient_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            if settings.SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                if settings.SMTP_TLS:
                    server.starttls()

            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.send_message(msg)
            server.quit()

            cls._log_audit(
                db=db,
                user_id=user_id,
                job_id=job_id,
                workspace_id=workspace_id,
                action="email_sent",
                status="success",
                recipient=recipient_email,
                details=f"Email delivered via SMTP to {recipient_email}. Subject: '{subject}'",
                idempotency_key=idempotency_key
            )

            return {
                "status": "sent",
                "message": f"Email delivered successfully to {recipient_email}.",
                "error": None
            }

        except Exception as e:
            err_msg = f"SMTP transmission failed: {str(e)}"
            logger.error("Failed to send email to %s: %s", recipient_email, err_msg)

            cls._log_audit(
                db=db,
                user_id=user_id,
                job_id=job_id,
                workspace_id=workspace_id,
                action="email_failed",
                status="failed",
                recipient=recipient_email,
                details=err_msg,
                idempotency_key=idempotency_key
            )

            return {
                "status": "failed",
                "message": "Failed to send email due to a mail server error.",
                "error": err_msg
            }

    @classmethod
    def _log_audit(
        cls,
        db: Session,
        user_id: int,
        job_id: Optional[int],
        workspace_id: Optional[int],
        action: str,
        status: str,
        recipient: Optional[str],
        details: Optional[str],
        idempotency_key: Optional[str]
    ):
        log = ApplicationAuditLog(
            user_id=user_id,
            job_id=job_id,
            workspace_id=workspace_id,
            action=action,
            status=status,
            destination="email",
            recipient=recipient,
            details=details,
            idempotency_key=idempotency_key,
            created_at=datetime.now(timezone.utc)
        )
        db.add(log)
        db.commit()
