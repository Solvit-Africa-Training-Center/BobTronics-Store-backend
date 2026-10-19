"""Google ID-token verification and customer account lookup."""

from django.conf import settings
from django.db import IntegrityError, transaction
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from apps.accounts.models import User


class GoogleLoginError(Exception):
    """Base error for Google sign-in failures safe to show to the user."""


class GoogleLoginNotConfigured(GoogleLoginError):
    pass


class GoogleLoginUnavailable(GoogleLoginError):
    pass


def _email_is_google_authoritative(email, hosted_domain):
    email_domain = email.rpartition("@")[2].lower()
    if email_domain == "gmail.com":
        return True
    return bool(hosted_domain) and email_domain == str(hosted_domain).lower()


def _account_names(claims, email):
    name_parts = str(claims.get("name") or "").strip().split()
    first_name = str(claims.get("given_name") or "").strip()
    last_name = str(claims.get("family_name") or "").strip()
    if not first_name:
        first_name = name_parts[0] if name_parts else email.partition("@")[0]
    if not last_name and len(name_parts) > 1:
        last_name = " ".join(name_parts[1:])
    return first_name[:150], last_name[:150]


def login_with_google_credential(credential):
    """Verify a Google ID token and return its linked or newly created user."""
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    if not client_id:
        raise GoogleLoginNotConfigured("Google sign-in is not configured.")

    try:
        claims = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            audience=client_id,
        )
    except google_auth_exceptions.TransportError as exc:
        raise GoogleLoginUnavailable from exc
    except (ValueError, google_auth_exceptions.GoogleAuthError) as exc:
        raise GoogleLoginError(
            "Google sign-in failed. Check your Google account and try again."
        ) from exc

    email = str(claims.get("email") or "").strip().lower()
    google_sub = str(claims.get("sub") or "").strip()
    if not email or not google_sub or claims.get("email_verified") is not True:
        raise GoogleLoginError("Google couldn't verify this account. Try another account.")

    if not _email_is_google_authoritative(email, claims.get("hd")):
        raise GoogleLoginError("Use a Gmail or Google Workspace account to sign in.")

    first_name, last_name = _account_names(claims, email)
    with transaction.atomic():
        user = User.objects.select_for_update().filter(google_sub=google_sub).first()
        if user is None:
            user = User.objects.select_for_update().filter(email__iexact=email).first()

        if user is not None:
            if user.google_sub and user.google_sub != google_sub:
                raise GoogleLoginError(
                    "This email is linked to another Google account. Sign in with your password."
                )
            if not user.google_sub:
                user.google_sub = google_sub
                user.save(update_fields=["google_sub"])
            return user

        try:
            with transaction.atomic():
                return User.objects.create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    google_sub=google_sub,
                )
        except IntegrityError:
            # Another request may have created or linked the same Google account.
            user = User.objects.select_for_update().filter(google_sub=google_sub).first()
            if user is None:
                user = User.objects.select_for_update().filter(email__iexact=email).first()
            if user is None:
                raise
            if user.google_sub and user.google_sub != google_sub:
                raise GoogleLoginError(
                    "This email is linked to another Google account. Sign in with your password."
                )
            if not user.google_sub:
                user.google_sub = google_sub
                user.save(update_fields=["google_sub"])
            return user
