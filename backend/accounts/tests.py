from rest_framework.test import APITestCase
from django.test import override_settings
from django.core import mail
from django.utils import timezone
from datetime import timedelta
import re
from .models import User


class RoleLoginTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        for role in ["customer", "owner", "admin"]:
            User.objects.create_user(
                username=f"login_{role}",
                email=f"{role}@login.test",
                password="RoleLogin!2026",
                role=role,
            )

    def test_each_role_authenticates_with_its_own_account(self):
        for role in ["customer", "owner", "admin"]:
            with self.subTest(role=role):
                response = self.client.post(
                    "/api/v1/auth/token/",
                    {
                        "username": f"login_{role}",
                        "password": "RoleLogin!2026",
                        "role": role,
                    },
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.client.credentials(
                    HTTP_AUTHORIZATION="Bearer " + response.data["access"]
                )
                self.assertEqual(self.client.get("/api/v1/auth/me/").data["role"], role)
                self.client.credentials()

    def test_selecting_admin_does_not_promote_customer_or_return_tokens(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {
                "username": "login_customer",
                "password": "RoleLogin!2026",
                "role": "admin",
            },
        )
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertEqual(User.objects.get(username="login_customer").role, "customer")

    def test_role_selection_does_not_replace_password_verification(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {"username": "login_admin", "password": "incorrect", "role": "admin"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("access", response.data)

    def test_existing_api_clients_can_still_log_in_without_role_field(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {"username": "login_owner", "password": "RoleLogin!2026"},
        )
        self.assertEqual(response.status_code, 200)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST_USER="sender@example.test",
    EMAIL_HOST_PASSWORD="test-only",
    DEFAULT_FROM_EMAIL="sender@example.test",
)
class EmailVerificationTests(APITestCase):
    def register(self, username="new_guest", email="new@example.test", role="customer"):
        return self.client.post("/api/v1/auth/register/", {
            "username": username,
            "email": email,
            "password": "LongTestPassword!2026",
            "role": role,
        })

    def code(self, message):
        return re.search(r"\b\d{6}\b", message.body).group()

    def test_registration_requires_email_then_verifies_once(self):
        response = self.register()
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(username="new_guest")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        credentials = {"username": "new_guest", "password": "LongTestPassword!2026"}
        login = self.client.post("/api/v1/auth/token/", credentials)
        self.assertEqual(login.status_code, 401)
        self.assertIn("Verify your email", str(login.data["detail"]))
        self.assertNotIn("access", login.data)
        self.assertNotIn("refresh", login.data)
        code = self.code(mail.outbox[0])
        self.assertEqual(self.client.post("/api/v1/auth/verify-email/", {"email": "new@example.test", "code": code}).status_code, 200)
        self.assertEqual(self.client.post("/api/v1/auth/verify-email/", {"email": "new@example.test", "code": code}).status_code, 400)
        self.assertEqual(self.client.post("/api/v1/auth/token/", credentials).status_code, 200)

    def test_resend_cooldown_and_old_code_invalidation(self):
        self.register()
        first = self.code(mail.outbox[0])
        response = self.client.post("/api/v1/auth/resend-verification/", {"email": "new@example.test"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(len(mail.outbox), 1)
        user = User.objects.get(username="new_guest")
        user.email_verification_sent_at = timezone.now() - timedelta(seconds=61)
        user.save(update_fields=["email_verification_sent_at"])
        response = self.client.post("/api/v1/auth/resend-verification/", {"email": "new@example.test"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(self.client.post("/api/v1/auth/verify-email/", {"email": "new@example.test", "code": first}).status_code, 400)
        self.assertEqual(self.client.post("/api/v1/auth/verify-email/", {"email": "new@example.test", "code": self.code(mail.outbox[1])}).status_code, 200)

    def test_code_expires_after_three_minutes(self):
        self.register()
        code = self.code(mail.outbox[0])
        user = User.objects.get(username="new_guest")
        user.email_verification_sent_at = timezone.now() - timedelta(seconds=181)
        user.save(update_fields=["email_verification_sent_at"])
        response = self.client.post("/api/v1/auth/verify-email/", {"email": "new@example.test", "code": code})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.get(username="new_guest").is_active)

    def test_five_bad_codes_lock_until_resend(self):
        self.register()
        code = self.code(mail.outbox[0])
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.assertEqual(self.client.post("/api/v1/auth/verify-email/", {"email": "new@example.test", "code": wrong}).status_code, 400)
        self.assertEqual(self.client.post("/api/v1/auth/verify-email/", {"email": "new@example.test", "code": code}).status_code, 400)

    def test_owner_needs_admin_approval_after_email_verification(self):
        response = self.register(username="new_owner", role="owner")
        self.assertEqual(response.status_code, 201, response.data)
        owner = User.objects.get(username="new_owner")
        self.assertEqual(owner.owner_approval_status, User.OwnerApproval.PENDING)
        code = self.code(mail.outbox[0])
        response = self.client.post("/api/v1/auth/verify-email/", {"email": owner.email, "code": code})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_sign_in"])
        owner.refresh_from_db()
        self.assertFalse(owner.is_active)
        login = self.client.post("/api/v1/auth/token/", {"username": "new_owner", "password": "LongTestPassword!2026"})
        self.assertEqual(login.status_code, 401)
        review_url = f"/api/v1/admin/users/{owner.pk}/review/"
        self.assertEqual(self.client.post(review_url, {"decision": "approved"}).status_code, 401)
        admin = User.objects.create_user(username="admin_reviewer", email="admin@example.test", password="AdminPassword!2026", role="admin")
        self.client.force_authenticate(user=admin)
        self.assertEqual(self.client.get("/api/v1/admin/users/").status_code, 200)
        self.assertEqual(self.client.post(review_url, {"decision": "approved"}).status_code, 200)
        owner.refresh_from_db()
        self.assertTrue(owner.is_active)
        self.assertEqual(owner.owner_approval_status, User.OwnerApproval.APPROVED)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.post("/api/v1/auth/token/", {"username": "new_owner", "password": "LongTestPassword!2026"}).status_code, 200)

    def test_unverified_owner_cannot_be_approved(self):
        self.register(username="new_owner", role="owner")
        owner = User.objects.get(username="new_owner")
        admin = User.objects.create_user(username="admin_reviewer", email="admin@example.test", password="AdminPassword!2026", role="admin")
        self.client.force_authenticate(user=admin)
        response = self.client.post(f"/api/v1/admin/users/{owner.pk}/review/", {"decision": "approved"})
        self.assertEqual(response.status_code, 400)
        owner.refresh_from_db()
        self.assertFalse(owner.is_active)
