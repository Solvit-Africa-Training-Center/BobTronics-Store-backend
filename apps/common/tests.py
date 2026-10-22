from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog
from apps.common.models import ContactMessage, ContactStatus, Notification, NotificationType
from apps.common.services import create_user_notification


class ContactAndNotificationAPITestCase(APITestCase):
    def setUp(self):
        mail.outbox = []

        # Regular customer
        self.customer = User.objects.create_user(
            email="customer@example.com",
            first_name="Alice",
            last_name="Uwase",
            password="StrongPassword123!",
            role=Role.CUSTOMER,
            is_active=True,
        )

        # Another customer
        self.other_customer = User.objects.create_user(
            email="other@example.com",
            first_name="Other",
            last_name="Customer",
            password="StrongPassword123!",
            role=Role.CUSTOMER,
            is_active=True,
        )

        # Store administrator
        self.admin_user = User.objects.create_user(
            email="admin@bobtronics.com",
            first_name="Admin",
            last_name="Manager",
            password="StrongPassword123!",
            role=Role.ADMIN,
            is_active=True,
        )

        # URLs
        self.contact_url = reverse("common:contact-submit")
        self.contact_direct_url = reverse("contact-submit-direct")
        self.admin_list_url = reverse("common:contact-admin-list")
        self.notifications_url = reverse("notification-list")
        self.unread_count_url = reverse("notification-unread-count")
        self.mark_all_read_url = reverse("notification-mark-all-read")

    # ========================================================================
    # CONTACT FORM TESTS (Matching exact frontend payload)
    # ========================================================================

    def test_submit_contact_form_exact_frontend_fields(self):
        """Tests submission using exact frontend naming: full_name, phone_number, how_can_we_help."""
        payload = {
            "full_name": "David Shema",
            "email": "david.shema@example.com",
            "phone_number": "+250 78 555 0184",
            "how_can_we_help": "Product advice",
            "message": "I'm looking for a laptop for design work. Can your team help me choose the right configuration?",
            "agree_to_privacy_policy": True,
        }

        response = self.client.post(self.contact_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get("success"))
        self.assertIn("message", response.data)
        data = response.data["data"]
        self.assertEqual(data["name"], "David Shema")
        self.assertEqual(data["email"], "david.shema@example.com")
        self.assertEqual(data["phone"], "+250 78 555 0184")
        self.assertEqual(data["subject"], "Product advice")
        self.assertEqual(data["status"], ContactStatus.PENDING)

        # Verify DB
        msg_obj = ContactMessage.objects.get(email="david.shema@example.com")
        self.assertEqual(msg_obj.name, "David Shema")
        self.assertEqual(msg_obj.subject, "Product advice")
        self.assertTrue(msg_obj.agreed_to_privacy_policy)

        # Verify email dispatches (1 admin, 1 customer)
        self.assertEqual(len(mail.outbox), 2)
        admin_email = mail.outbox[0]
        self.assertIn("David Shema", admin_email.body)
        self.assertIn("Product advice", admin_email.subject)
        self.assertIn("david.shema@example.com", admin_email.reply_to)

        customer_ack = mail.outbox[1]
        self.assertIn("david.shema@example.com", customer_ack.to)
        self.assertIn("Product advice", customer_ack.body)

    def test_submit_contact_form_with_attachment(self):
        """Tests uploading an attachment via multipart form."""
        fake_file = SimpleUploadedFile("spec_sheet.txt", b"Need RTX 4080 and 32GB RAM", content_type="text/plain")
        payload = {
            "name": "David Shema",
            "email": "david.shema@example.com",
            "subject": "Hardware specification",
            "message": "Attached are our laptop specs.",
            "attachment": fake_file,
        }

        response = self.client.post(self.contact_direct_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data["data"]
        self.assertIsNotNone(data["attachment_url"])

        msg_obj = ContactMessage.objects.get(subject="Hardware specification")
        self.assertTrue(bool(msg_obj.attachment))

    def test_submit_contact_form_authenticated_user_creates_notification(self):
        """Authenticated user receives an in-app notification upon submitting contact message."""
        self.client.force_authenticate(user=self.customer)
        payload = {
            "name": "Alice Uwase",
            "email": "customer@example.com",
            "subject": "Order tracking question",
            "message": "When will my package arrive in Kigali?",
        }

        response = self.client.post(self.contact_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check in-app notification
        notif = Notification.objects.filter(user=self.customer, notification_type=NotificationType.CONTACT).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.title, "Message Sent to Support")
        self.assertIn("Order tracking question", notif.message)
        self.assertEqual(notif.action_url, "/contact")

    def test_contact_form_validation(self):
        # Invalid email
        res1 = self.client.post(self.contact_url, {"name": "Test", "email": "not-an-email", "message": "Valid text"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)

        # Too short message
        res2 = self.client.post(self.contact_url, {"name": "Test", "email": "test@example.com", "message": "Hey"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    # ========================================================================
    # NOTIFICATIONS API TESTS
    # ========================================================================

    def test_notification_list_and_unread_count(self):
        # Create notifications for customer
        create_user_notification(
            user=self.customer,
            title="Order #101 Confirmed",
            message="Your order #101 has been confirmed.",
            notification_type=NotificationType.ORDER,
            action_url="/orders/101",
            data={"order_id": 101, "total": 125000},
        )
        create_user_notification(
            user=self.customer,
            title="Package Dispatched",
            message="Courier is on the way with your package.",
            notification_type=NotificationType.DELIVERY,
            action_url="/deliveries/55",
            data={"delivery_id": 55, "courier": "FastCourier"},
        )

        # Unauthenticated cannot view
        res_guest = self.client.get(self.notifications_url)
        self.assertEqual(res_guest.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated customer
        self.client.force_authenticate(user=self.customer)
        res = self.client.get(self.notifications_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["unread_count"], 2)
        self.assertEqual(len(res.data["notifications"]), 2)

        # Check unread count endpoint
        count_res = self.client.get(self.unread_count_url)
        self.assertEqual(count_res.status_code, status.HTTP_200_OK)
        self.assertEqual(count_res.data["unread_count"], 2)

    def test_notification_detail_auto_marks_as_read(self):
        notif = create_user_notification(
            user=self.customer,
            title="Special Deal",
            message="Get 15% off smart home appliances today!",
            notification_type=NotificationType.PROMOTION,
            action_url="/promotions/deal-1",
            data={"discount_percent": 15, "deal_code": "SMART15"},
        )
        self.assertFalse(notif.is_read)

        detail_url = reverse("notification-detail", kwargs={"pk": notif.pk})

        # Other customer cannot view this notification
        self.client.force_authenticate(user=self.other_customer)
        res_forbidden = self.client.get(detail_url)
        self.assertEqual(res_forbidden.status_code, status.HTTP_404_NOT_FOUND)

        # Owner retrieves notification
        self.client.force_authenticate(user=self.customer)
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["notification"]["title"], "Special Deal")
        self.assertEqual(res.data["notification"]["data"]["deal_code"], "SMART15")

        # Verify auto marked as read
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
        self.assertIsNotNone(notif.read_at)

    def test_notification_mark_single_and_all_read(self):
        n1 = create_user_notification(user=self.customer, title="Notice 1", message="Desc 1")
        n2 = create_user_notification(user=self.customer, title="Notice 2", message="Desc 2")

        self.client.force_authenticate(user=self.customer)

        # Mark single
        mark_url = reverse("notification-mark-read", kwargs={"pk": n1.pk})
        patch_res = self.client.patch(mark_url)
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        n1.refresh_from_db()
        self.assertTrue(n1.is_read)

        # Mark all
        post_res = self.client.post(self.mark_all_read_url)
        self.assertEqual(post_res.status_code, status.HTTP_200_OK)
        n2.refresh_from_db()
        self.assertTrue(n2.is_read)
