"""
Celery tasks for the users app.
Wraps synchronous service methods so they can run asynchronously when
a Celery worker is available.
"""

import logging

from celery import shared_task
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email(self, user_id: str):
    """Async: generate an email-verification OTP and email it to the user."""
    try:
        from apps.users.services import UserService

        user = User.objects.get(id=user_id)
        UserService.send_verification_email_sync(user)
    except User.DoesNotExist:
        logger.error("send_verification_email: user %s not found", user_id)
    except Exception as exc:
        logger.error("send_verification_email task failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, user_id: str, token: str):
    """Async: email a pre-generated password-reset OTP to the user."""
    try:
        from apps.users.services import UserService

        user = User.objects.get(id=user_id)
        UserService.send_password_reset_email_sync(user, token)
    except User.DoesNotExist:
        logger.error("send_password_reset_email: user %s not found", user_id)
    except Exception as exc:
        logger.error("send_password_reset_email task failed: %s", exc)
        raise self.retry(exc=exc)
