"""
Business logic services for the users app.
"""

import logging
import random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.notifications.services import NotificationService

User = get_user_model()

logger = logging.getLogger(__name__)

EMAIL_VERIFICATION_CACHE_KEY = "email_verify:{token}"
PASSWORD_RESET_CACHE_KEY = "pwd_reset:{token}"
OTP_TTL = 60 * 10  # 10 minutes — short window reduces brute-force risk on 6-digit codes


class UserService:
    """Service layer for user-related operations."""

    @staticmethod
    @transaction.atomic
    def register_user(validated_data: dict) -> User:
        """
        Create a new user with profile from validated registration data.
        Sends an email verification notification asynchronously.
        """
        from .serializers import UserRegistrationSerializer

        serializer = UserRegistrationSerializer(data=validated_data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Schedule email verification (async if Celery is available, sync otherwise)
        try:
            from apps.users.tasks import send_verification_email

            send_verification_email.delay(str(user.id))
        except Exception:
            logger.warning(
                "Celery unavailable — sending verification email synchronously for %s",
                user.id,
            )
            UserService.send_verification_email_sync(user)

        logger.info("New user registered: %s (type=%s)", user.email, user.user_type)
        return user

    @staticmethod
    def generate_email_verification_token(user: User) -> str:
        """Generate and cache a 6-digit email verification OTP for the user."""
        token = str(random.randint(100000, 999999))
        cache_key = EMAIL_VERIFICATION_CACHE_KEY.format(token=token)
        cache.set(cache_key, str(user.id), timeout=OTP_TTL)
        return token

    @staticmethod
    def send_verification_email_sync(user: User) -> None:
        """Generate a verification OTP and email it to the user synchronously."""
        token = UserService.generate_email_verification_token(user)
        subject = "Verify your SaveFood DZ email"
        message = (
            f"Hello,\n\n"
            f"Your email verification code is:\n\n"
            f"    {token}\n\n"
            f"Enter this code in the app to confirm your email address.\n"
            f"The code expires in 10 minutes.\n\n"
            f"If you did not register on SaveFood DZ, please ignore this email.\n\n"
            f"— The SaveFood DZ Team"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info("Verification email sent to %s", user.email)
        except Exception as e:
            logger.error("Failed to send verification email to %s: %s", user.email, e)

    @staticmethod
    def send_password_reset_email_sync(user: User, token: str) -> None:
        """Email a pre-generated password-reset OTP to the user synchronously."""
        subject = "Reset your SaveFood DZ password"
        message = (
            f"Hello,\n\n"
            f"Your password reset code is:\n\n"
            f"    {token}\n\n"
            f"Enter this code in the app to set a new password.\n"
            f"The code expires in 10 minutes.\n\n"
            f"If you did not request a password reset, please ignore this email.\n\n"
            f"— The SaveFood DZ Team"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info("Password reset email sent to %s", user.email)
        except Exception as e:
            logger.error("Failed to send password reset email to %s: %s", user.email, e)

    @staticmethod
    def verify_email(token: str) -> User:
        """
        Verify the user's email using the provided token.
        Raises ValueError if the token is invalid or expired.
        """
        cache_key = EMAIL_VERIFICATION_CACHE_KEY.format(token=token)
        user_id = cache.get(cache_key)
        if not user_id:
            raise ValueError("Invalid or expired verification token.")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError("User not found.")

        user.email_verified = True
        user.save(update_fields=["email_verified"])
        cache.delete(cache_key)
        logger.info("Email verified for user %s", user.email)
        return user

    @staticmethod
    def request_password_reset(email: str) -> None:
        """
        Generate a password reset token and send it via email.
        Does not raise errors for unknown emails (to prevent user enumeration).
        """
        try:
            user = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            # Silently succeed to prevent user enumeration
            return

        token = str(random.randint(100000, 999999))
        cache_key = PASSWORD_RESET_CACHE_KEY.format(token=token)
        cache.set(cache_key, str(user.id), timeout=OTP_TTL)

        # Send email (async if Celery is available, sync otherwise)
        try:
            from apps.users.tasks import send_password_reset_email

            send_password_reset_email.delay(str(user.id), token)
        except Exception:
            logger.warning(
                "Celery unavailable — sending password reset email synchronously for %s",
                user.id,
            )
            UserService.send_password_reset_email_sync(user, token)

    @staticmethod
    def reset_password(token: str, new_password: str) -> User:
        """
        Validate the reset token and set the user's new password.
        Raises ValueError if the token is invalid or expired.
        """
        cache_key = PASSWORD_RESET_CACHE_KEY.format(token=token)
        user_id = cache.get(cache_key)
        if not user_id:
            raise ValueError("Invalid or expired password reset token.")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError("User not found.")

        user.set_password(new_password)
        user.save(update_fields=["password"])
        cache.delete(cache_key)
        logger.info("Password reset completed for user %s", user.email)
        return user

    @staticmethod
    def resend_verification_email(user: User) -> None:
        """
        Re-generate a verification OTP and send it to the user.
        Raises ValueError if the email is already verified.
        """
        if user.email_verified:
            raise ValueError("Email is already verified.")
        UserService.send_verification_email_sync(user)

    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> User:
        """
        Validate the old password and update to the new one.
        Raises ValueError if the old password is incorrect.
        """
        if not user.check_password(old_password):
            raise ValueError("Current password is incorrect.")
        user.set_password(new_password)
        user.save(update_fields=["password"])
        logger.info("Password changed for user %s", user.email)
        return user

    @staticmethod
    @transaction.atomic
    def update_merchant_verification(
        merchant, status: str, notes: str, admin_user: User
    ):
        """
        Update the verification status of a merchant.
        Sends a notification to the merchant upon status change.
        """
        from .models import Merchant

        old_status = merchant.verification_status
        merchant.verification_status = status
        merchant.verification_notes = notes
        if status == "approved":
            merchant.verified_at = timezone.now()
            merchant.verified_by = admin_user
        merchant.save(
            update_fields=[
                "verification_status",
                "verification_notes",
                "verified_at",
                "verified_by",
                "updated_at",
            ]
        )

        if old_status != status:
            try:
                NotificationService.notify_account_verified(merchant.user)
            except Exception:
                logger.warning(
                    "Failed to send verification notification to merchant %s",
                    merchant.user.email,
                )

        logger.info(
            "Merchant %s verification updated to %s by %s",
            merchant.user.email,
            status,
            admin_user.email,
        )
        return merchant

    @staticmethod
    @transaction.atomic
    def update_charity_verification(
        charity, status: str, notes: str, admin_user: User
    ):
        """
        Update the verification status of a charity.
        Sends a notification to the charity upon status change.
        """
        old_status = charity.verification_status
        charity.verification_status = status
        charity.verification_notes = notes
        if status == "approved":
            charity.verified_at = timezone.now()
            charity.verified_by = admin_user
        charity.save(
            update_fields=[
                "verification_status",
                "verification_notes",
                "verified_at",
                "verified_by",
                "updated_at",
            ]
        )

        if old_status != status:
            try:
                NotificationService.notify_account_verified(charity.user)
            except Exception:
                logger.warning(
                    "Failed to send verification notification to charity %s",
                    charity.user.email,
                )

        logger.info(
            "Charity %s verification updated to %s by %s",
            charity.user.email,
            status,
            admin_user.email,
        )
        return charity

    @staticmethod
    @transaction.atomic
    def request_profile_update(user: User, changes: dict, documents: list) -> "ProfileUpdateRequest":
        """
        Create a new profile update request for a merchant or charity.
        """
        from .models import ProfileUpdateRequest, ProfileUpdateDocument

        profile = user.profile
        if not profile:
            raise ValueError("User does not have a profile to update.")

        # Prepare change log with old values
        processed_changes = {}
        for field, new_value in changes.items():
            if hasattr(profile, field):
                old_value = getattr(profile, field)
                processed_changes[field] = {
                    "old": old_value,
                    "new": new_value
                }
            elif hasattr(user, field):
                old_value = getattr(user, field)
                processed_changes[field] = {
                    "old": old_value,
                    "new": new_value
                }

        request = ProfileUpdateRequest.objects.create(
            user=user,
            changes=processed_changes
        )

        for doc in documents:
            ProfileUpdateDocument.objects.create(
                request=request,
                document_type=doc.get("document_type", "other"),
                file_url=doc.get("file_url"),
                file_name=doc.get("file_name", "unnamed_document")
            )

        logger.info("Profile update request %s created for %s", request.id, user.email)
        return request

    @staticmethod
    @transaction.atomic
    def approve_profile_update(update_request: "ProfileUpdateRequest", admin_user: User) -> None:
        """
        Approve the request and apply changes to the user's profile.
        """
        from .models import PROFILE_UPDATE_STATUS_APPROVED
        from apps.notifications.services import NotificationService

        user = update_request.user
        profile = user.profile
        
        # Apply changes
        for field, values in update_request.changes.items():
            new_value = values["new"]
            if hasattr(profile, field):
                setattr(profile, field, new_value)
            elif hasattr(user, field):
                setattr(user, field, new_value)

        # Save changes
        user.save()
        if profile:
            profile.save()

        # Update request status
        update_request.status = PROFILE_UPDATE_STATUS_APPROVED
        update_request.processed_at = timezone.now()
        update_request.processed_by = admin_user
        update_request.save()

        # Notify user
        NotificationService.notify_profile_update_processed(
            user, 
            status="approved", 
            admin_note=update_request.admin_note
        )

        logger.info("Profile update request %s approved by %s", update_request.id, admin_user.email)

    @staticmethod
    @transaction.atomic
    def reject_profile_update(update_request: "ProfileUpdateRequest", admin_user: User, admin_note: str) -> None:
        """
        Reject the request and notify the user.
        """
        from .models import PROFILE_UPDATE_STATUS_REJECTED
        from apps.notifications.services import NotificationService

        update_request.status = PROFILE_UPDATE_STATUS_REJECTED
        update_request.admin_note = admin_note
        update_request.processed_at = timezone.now()
        update_request.processed_by = admin_user
        update_request.save()

        # Notify user
        NotificationService.notify_profile_update_processed(
            update_request.user, 
            status="rejected", 
            admin_note=admin_note
        )

        logger.info("Profile update request %s rejected by %s", update_request.id, admin_user.email)
