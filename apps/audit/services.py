"""Helpers for recording immutable audit events."""

from .models import AuditLog


def log_audit_event(*, action, entry_type, entity_id=None, user=None, description="", request=None):
    """Persist an audit event without copying request payloads or credentials."""
    ip_address = None
    if request is not None:
        # REMOTE_ADDR is supplied by Django's server/proxy configuration.
        ip_address = request.META.get("REMOTE_ADDR")

    return AuditLog.objects.create(
        user=user,
        action=action,
        entry_type=entry_type,
        entity_id=entity_id,
        description=description,
        ip_address=ip_address,
    )
