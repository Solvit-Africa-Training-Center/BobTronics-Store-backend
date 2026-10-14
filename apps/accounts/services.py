import logging
from smtplib import SMTPException
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User

ACTIVATION_MESSAGE = "Registration successful. Check your email for account activation instructions."
PASSWORD_RESET_MESSAGE = "If an active account matches that email, password reset instructions have been sent."
logger = logging.getLogger(__name__)


def _uid_and_token(user):
    return urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)


def _send_account_email(user, subject, intro, endpoint):
    uid, token = _uid_and_token(user)
    query = urlencode({"uid": uid, "token": token})
    link = f"{settings.SITE_URL}{endpoint}?{query}"
    body = (
        f"{intro}\n\n"
        f"Link: {link}\n"
        f"Account reference: {uid}\n"
        f"Verification token: {token}\n"
        f"API endpoint: {settings.SITE_URL}{endpoint}\n\n"
        "Submit these values to the endpoint above. "
        "If you did not request this, you can ignore this message."
    )
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    except (SMTPException, OSError, TimeoutError) as exc:
        # Log only the exception type; backend exception text can contain connection details.
        logger.warning("Account email delivery failed (%s).", type(exc).__name__)


@transaction.atomic
def register_user(*, email, password, first_name, last_name, phone="", residence=""):
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        residence=residence,
        is_active=False,
    )
    _send_account_email(
        user,
        "Activate your BobTronics account",
        "Complete account validation using the details below.",
        "/api/v1/accounts/activate/",
    )
    return user


def _user_from_uid(uid):
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        return User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


def activate_account(uid, token):
    user = _user_from_uid(uid)
    if user is None or user.is_active or not default_token_generator.check_token(user, token):
        return False
    user.is_active = True
    user.save(update_fields=["is_active"])
    return True


def request_password_reset(email):
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is not None:
        _send_account_email(
            user,
            "Reset your BobTronics password",
            "Use the details below to reset your password.",
            "/api/v1/accounts/password-reset/confirm/",
        )


def complete_password_reset(uid, token, new_password):
    user = _user_from_uid(uid)
    if user is None or not user.is_active or not default_token_generator.check_token(user, token):
        return False
    user.set_password(new_password)
    user.save(update_fields=["password"])
    return True


def blacklist_refresh_token(raw_token):
    try:
        RefreshToken(raw_token).blacklist()
    except TokenError as exc:
        raise ValueError("Invalid refresh token") from exc
