import secrets
from datetime import timedelta
from hmac import compare_digest
from math import ceil

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import User

EXPIRY_SECONDS = 180
RESEND_SECONDS = 60
MAX_ATTEMPTS = 5


def code_digest(user_id, code):
    return salted_hmac("roomfinder.email-code", f"{user_id}:{code}").hexdigest()


def send_verification(user):
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        raise RuntimeError("Email sending is not configured")
    code = f"{secrets.randbelow(1_000_000):06d}"
    user.email_verification_nonce = code_digest(user.pk, code)
    user.email_verification_attempts = 0
    user.email_verification_sent_at = None
    user.save(update_fields=["email_verification_nonce", "email_verification_attempts", "email_verification_sent_at"])
    send_mail(
        "Your RoomFinder verification code",
        f"Your RoomFinder verification code is {code}. It expires 3 minutes after this email is sent.\n\nIf you did not register, ignore this email.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    user.email_verification_sent_at = timezone.now()
    user.save(update_fields=["email_verification_sent_at"])


def verify_code(email, code):
    if not isinstance(email, str) or not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        return False
    try:
        user = User.objects.select_for_update().get(
            email__iexact=email.strip(), is_active=False, email_verified_at__isnull=True
        )
    except User.DoesNotExist:
        return False
    if not user.email_verification_sent_at or not user.email_verification_nonce:
        return False
    if timezone.now() >= user.email_verification_sent_at + timedelta(seconds=EXPIRY_SECONDS):
        return False
    if user.email_verification_attempts >= MAX_ATTEMPTS:
        return False
    if not compare_digest(user.email_verification_nonce, code_digest(user.pk, code)):
        user.email_verification_attempts += 1
        user.save(update_fields=["email_verification_attempts"])
        return False
    user.is_active = user.role != User.Role.OWNER or user.owner_approval_status == User.OwnerApproval.APPROVED
    user.email_verified_at = timezone.now()
    user.email_verification_nonce = ""
    user.email_verification_attempts = 0
    user.save(update_fields=["is_active", "email_verified_at", "email_verification_nonce", "email_verification_attempts"])
    return user


def resend_wait_seconds(user):
    if not user.email_verification_sent_at:
        return 0
    remaining = user.email_verification_sent_at + timedelta(seconds=RESEND_SECONDS) - timezone.now()
    return max(0, ceil(remaining.total_seconds()))
