from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.common.models import ContactMessage, Notification, NotificationType
from apps.common.services import create_user_notification


class ContactAndNotificationAPITestCase(APITestCase):
    def setUp(self):
        mail.outbox = []

        # Customer 1
        self.customer = User.objects.create_user(
            email="customer@example.com",
            first_name="Alice",
            last_name="Uwase",
            password="StrongPassword123!",
            role=Role.CUSTOMER,
            is_active=True,
        )

        # Customer 2
        self.other_customer = User.objects.create_user(
            email="other@example.com",
            first_name="Other",
            last_name="Customer",
            password="StrongPassword123!",
            role=Role.CUSTOMER,
            is_active=True,
        )

        # Store Administrator
        self.admin_user = User.objects.create_user(
            email="admin@bobtronics.com",
            first_name="Admin",
            last_name="Manager",
            password="StrongPassword123!",
            role=Role.ADMIN,
            is_active=True,
        )

        # URLs
        self.contact_url = reverse("common:contact-list-create")
        self.admin_contact_list_url = reverse("common:contact-admin-list")
        self.notifications_url = reverse("notification-list")
        self.unread_count_url = reverse("notification-unread-count")
        self.mark_all_read_url = reverse("notification-mark-all-read")

    # ========================================================================
    # CONTACT MESSAGE TESTS (CUSTOMER SEND, EDIT, DELETE & AUTH REQUIRED)
    # ========================================================================

    def test_unauthenticated_user_cannot_send_contact_message(self):
        """Unauthenticated visitor is rejected because contact form requires authentication."""
        payload = {
            "full_name": "David Shema",
            "email": "david.shema@example.com",
            "phone_number": "+250 78 555 0184",
            "message": "I want to inquire about laptop availability.",
            "agree_to_privacy_policy": True,
        }
        response = self.client.post(self.contact_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_customer_send_message_dispatches_emails_and_notifications(self):
        """Authenticated customer sends message; emails and in-app notification are dispatched."""
        self.client.force_authenticate(user=self.customer)
        payload = {
            "full_name": "David Shema",
            "email": "david.shema@example.com",
            "phone_number": "+250 78 555 0184",
            "message": "I'm looking for a laptop for design work. Can your team help me choose the right configuration?",
            "agree_to_privacy_policy": True,
        }

        response = self.client.post(self.contact_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        data = response.data["data"]
        self.assertEqual(data["full_name"], "David Shema")
        self.assertEqual(data["email"], "david.shema@example.com")
        self.assertEqual(data["phone_number"], "+250 78 555 0184")
        self.assertFalse(data["is_read"])

        # Check DB object
        msg = ContactMessage.objects.get(pk=data["id"])
        self.assertEqual(msg.user, self.customer)
        self.assertEqual(msg.full_name, "David Shema")
        self.assertTrue(msg.agree_to_privacy_policy)

        # Check email dispatches
        self.assertEqual(len(mail.outbox), 2)
        admin_email = mail.outbox[0]
        self.assertIn("David Shema", admin_email.body)
        self.assertIn("david.shema@example.com", admin_email.reply_to)

        customer_ack = mail.outbox[1]
        self.assertIn("david.shema@example.com", customer_ack.to)

        # Check in-app notification
        notif = Notification.objects.filter(user=self.customer, notification_type=NotificationType.CONTACT).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.title, "Message Sent to Support")

    def test_customer_can_list_edit_and_delete_message(self):
        """Customer can view their message list, retrieve detail, edit message, and delete it."""
        self.client.force_authenticate(user=self.customer)

        # 1. Create message
        create_res = self.client.post(
            self.contact_url,
            {
                "full_name": "Alice Uwase",
                "email": "customer@example.com",
                "phone_number": "+250 78 123 4567",
                "message": "Initial inquiry message before edit.",
                "agree_to_privacy_policy": True,
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        msg_id = create_res.data["data"]["id"]

        # 2. List own messages
        list_res = self.client.get(self.contact_url)
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.data["results"] if "results" in list_res.data else list_res.data), 1)

        # 3. Retrieve single message detail
        detail_url = reverse("common:contact-detail", kwargs={"pk": msg_id})
        detail_res = self.client.get(detail_url)
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_res.data["message"], "Initial inquiry message before edit.")

        # 4. Edit message (PATCH)
        edit_res = self.client.patch(
            detail_url,
            {"message": "Updated inquiry message: need fast delivery to Kigali."},
            format="json",
        )
        self.assertEqual(edit_res.status_code, status.HTTP_200_OK)
        self.assertEqual(edit_res.data["message"], "Updated inquiry message: need fast delivery to Kigali.")

        # 5. Other customer cannot edit or access
        self.client.force_authenticate(user=self.other_customer)
        forbidden_res = self.client.patch(detail_url, {"message": "Hacked message"}, format="json")
        self.assertEqual(forbidden_res.status_code, status.HTTP_404_NOT_FOUND)

        # 6. Delete message
        self.client.force_authenticate(user=self.customer)
        del_res = self.client.delete(detail_url)
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ContactMessage.objects.filter(pk=msg_id).exists())

    # ========================================================================
    # ADMIN DASHBOARD CONTACT TESTS (SEE ALL, READ, CANNOT EDIT)
    # ========================================================================

    def test_admin_dashboard_can_read_and_cannot_edit_message(self):
        """Admin can list and read any message (auto-marking read), but cannot edit message content."""
        msg = ContactMessage.objects.create(
            user=self.customer,
            full_name="David Shema",
            email="david.shema@example.com",
            phone_number="+250 78 555 0184",
            message="Customer query about product guarantee.",
            agree_to_privacy_policy=True,
        )
        self.assertFalse(msg.is_read)

        # Admin authenticates
        self.client.force_authenticate(user=self.admin_user)

        # 1. Admin lists all messages
        list_res = self.client.get(self.admin_contact_list_url)
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(list_res.data["unread_count"], 1)

        # 2. Admin reads message detail -> auto marks as read
        admin_detail_url = reverse("common:contact-admin-detail", kwargs={"pk": msg.pk})
        get_res = self.client.get(admin_detail_url)
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertTrue(get_res.data["data"]["is_read"])

        msg.refresh_from_db()
        self.assertTrue(msg.is_read)
        self.assertIsNotNone(msg.read_at)

        # 3. Admin CANNOT EDIT message -> PUT/PATCH returns 405 Method Not Allowed
        patch_res = self.client.patch(admin_detail_url, {"message": "Altered by admin"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        put_res = self.client.put(admin_detail_url, {"message": "Altered by admin"}, format="json")
        self.assertEqual(put_res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # ========================================================================
    # NOTIFICATIONS API TESTS
    # ========================================================================

    def test_notification_list_and_unread_count(self):
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
