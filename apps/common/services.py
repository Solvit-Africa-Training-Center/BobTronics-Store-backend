import logging
import re
from django.conf import settings
from django.core.mail import EmailMessage, send_mail

from apps.audit.services import log_audit_event
from apps.common.models import Notification, NotificationPriority, NotificationType

logger = logging.getLogger(__name__)


def _extract_email_address(raw_email):
    """Extract clean email address from 'Name <email@domain.com>' format if present."""
    match = re.search(r"<([^>]+)>", raw_email)
    if match:
        return match.group(1).strip()
    return raw_email.strip()


def create_user_notification(
    user,
    title,
    message,
    notification_type=NotificationType.SYSTEM,
    action_url="",
    data=None,
    priority=NotificationPriority.INFO,
):
    """
    Creates an in-app notification for a user with rich metadata and click destination.
    """
    if user is None:
        return None

    if data is None:
        data = {}

    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        action_url=action_url,
        data=data,
    )


def send_contact_form_notifications(contact_message, request=None):
    """
    Sends email notification to the store administrator and an acknowledgment
    email to the customer. Records an immutable audit log entry and creates
    an in-app notification if the sender is logged in.
    """
    admin_recipient = _extract_email_address(
        getattr(settings, "EMAIL_HOST_USER", "") or settings.DEFAULT_FROM_EMAIL
    )

    admin_subject = f"[BobTronics Contact Form] {contact_message.subject}"
    admin_body = (
        f"Hello Admin,\n\n"
        f"A new contact inquiry has been received on BobTronics Store.\n\n"
        f"Sender Information:\n"
        f"- Name: {contact_message.name}\n"
        f"- Email: {contact_message.email}\n"
        f"- Phone: {contact_message.phone or 'Not provided'}\n"
        f"- User Account: {contact_message.user.email if contact_message.user else 'Guest Visitor'}\n"
        f"- Privacy Consented: {'Yes' if contact_message.agreed_to_privacy_policy else 'No'}\n"
        f"- Submitted At: {contact_message.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if contact_message.created_at else 'Just now'}\n\n"
        f"Topic / Subject:\n"
        f"{contact_message.subject}\n\n"
        f"Message:\n"
        f"--------------------------------------------------\n"
        f"{contact_message.message}\n"
        f"--------------------------------------------------\n\n"
        f"You can reply directly to this email to respond to {contact_message.email}."
    )

    # 1. Send notification to administrator with reply-to set to the customer's email
    try:
        admin_email = EmailMessage(
            subject=admin_subject,
            body=admin_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[admin_recipient],
            reply_to=[contact_message.email],
        )

        # Attach file if uploaded
        if contact_message.attachment:
            try:
                admin_email.attach(
                    contact_message.attachment.name,
                    contact_message.attachment.read(),
                )
            except Exception as attach_err:
                logger.warning("Could not attach file to contact email: %s", attach_err)

        sent_admin = admin_email.send(fail_silently=False)
        print(f"[EMAIL_SUCCESS] Sent contact form notification to admin <{admin_recipient}> (sent={sent_admin})", flush=True)
    except Exception as exc:
        logger.warning("Failed to send contact form notification to admin (%s)", type(exc).__name__)

    # 2. Send acknowledgment to the sender
    customer_subject = f"We received your message - BobTronics Store"
    customer_body = (
        f"Hello {contact_message.name},\n\n"
        f"Thank you for contacting BobTronics Store! We have received your inquiry regarding \"{contact_message.subject}\".\n\n"
        f"Our support team will review your message and reply as soon as possible.\n\n"
        f"Your message:\n"
        f"--------------------------------------------------\n"
        f"{contact_message.message}\n"
        f"--------------------------------------------------\n\n"
        f"Warm regards,\n"
        f"BobTronics Support Team\n"
        f"{settings.SITE_URL}\n"
    )

    try:
        sent_customer = send_mail(
            customer_subject,
            customer_body,
            settings.DEFAULT_FROM_EMAIL,
            [contact_message.email],
            fail_silently=False,
        )
        print(f"[EMAIL_SUCCESS] Sent contact acknowledgment to customer <{contact_message.email}> (sent={sent_customer})", flush=True)
    except Exception as exc:
        logger.warning("Failed to send contact form acknowledgment to customer (%s)", type(exc).__name__)

    # 3. Create in-app notification for authenticated users
    if contact_message.user:
        try:
            create_user_notification(
                user=contact_message.user,
                title="Message Sent to Support",
                message=f"We received your message regarding '{contact_message.subject}'. Our team will respond shortly.",
                notification_type=NotificationType.CONTACT,
                action_url="/contact",
                data={
                    "contact_id": contact_message.pk,
                    "subject": contact_message.subject,
                    "status": contact_message.status,
                },
                priority=NotificationPriority.SUCCESS,
            )
        except Exception as notif_err:
            logger.warning("Failed to create in-app notification: %s", notif_err)

    # 4. Record audit event
    try:
        log_audit_event(
            action="CREATE",
            entry_type="ContactMessage",
            entity_id=str(contact_message.pk),
            user=contact_message.user or (request.user if request and request.user.is_authenticated else None),
            description=f"Contact message submitted by {contact_message.name} <{contact_message.email}>: '{contact_message.subject}'",
            request=request,
        )
    except Exception as exc:
        logger.warning("Failed to log audit event for contact message (%s)", type(exc).__name__)
