from rest_framework.test import APITestCase
from datetime import timedelta
from .models import User
from bookings.tests import fixture
from bookings.models import Booking
from hotels.models import Hotel
from rooms.models import Floor, Room
from datetime import date


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


class RegistrationWithoutEmailVerificationTests(APITestCase):
    def register(self, username="new_guest", email="new@example.test", role="customer"):
        return self.client.post("/api/v1/auth/register/", {
            "username": username,
            "email": email,
            "password": "LongTestPassword!2026",
            "role": role,
        })

    def test_customer_can_register_and_sign_in_without_email_delivery(self):
        response = self.register()
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(username="new_guest")
        self.assertTrue(user.is_active)
        login = self.client.post("/api/v1/auth/token/", {
            "username": "new_guest", "password": "LongTestPassword!2026",
        })
        self.assertEqual(login.status_code, 200, login.data)

    def test_owner_can_register_without_email_but_still_needs_admin_approval(self):
        response = self.register(username="new_owner", role="owner")
        self.assertEqual(response.status_code, 201, response.data)
        owner = User.objects.get(username="new_owner")
        self.assertTrue(owner.is_active)
        self.assertEqual(owner.owner_approval_status, User.OwnerApproval.PENDING)
        login = self.client.post("/api/v1/auth/token/", {
            "username": "new_owner", "password": "LongTestPassword!2026",
        })
        self.assertEqual(login.status_code, 401)
        self.assertIn("awaiting administrator approval", str(login.data["detail"]))
        admin = User.objects.create_user(
            username="admin_reviewer", email="admin@example.test",
            password="AdminPassword!2026", role="admin",
        )
        self.client.force_authenticate(user=admin)
        result = self.client.post(
            f"/api/v1/admin/users/{owner.pk}/review/", {"decision": "approved"}
        )
        self.assertEqual(result.status_code, 200, result.data)
        owner.refresh_from_db()
        self.assertTrue(owner.is_active)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.post("/api/v1/auth/token/", {
            "username": "new_owner", "password": "LongTestPassword!2026",
        }).status_code, 200)


class AdminUserDeletionTests(APITestCase):
    def test_deleting_owner_removes_property_records_but_keeps_guests(self):
        owner, customer, other, admin, hotel, floor, room = fixture()
        booking = Booking.objects.create(
            customer=customer, room=room,
            check_in=date.today() + timedelta(days=1),
            check_out=date.today() + timedelta(days=2), total="3000.00",
        )
        url = f"/api/v1/admin/users/{owner.pk}/"
        self.assertEqual(self.client.delete(url, {"confirm_username": "owner"}, format="json").status_code, 401)
        self.client.force_authenticate(owner)
        self.assertEqual(self.client.delete(url, {"confirm_username": "owner"}, format="json").status_code, 403)
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.delete(url, {"confirm_username": "wrong"}, format="json").status_code, 400)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url, {"confirm_username": "owner"}, format="json")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=owner.pk).exists())
        self.assertTrue(User.objects.filter(pk__in=[customer.pk, other.pk, admin.pk]).count() == 3)
        self.assertFalse(Hotel.objects.filter(pk=hotel.pk).exists())
        self.assertFalse(Room.objects.filter(pk=room.pk).exists())
        self.assertFalse(Booking.objects.filter(pk=booking.pk).exists())

    def test_deleting_customer_removes_bookings_but_keeps_hotel_and_admin(self):
        owner, customer, other, admin, hotel, floor, room = fixture()
        booking = Booking.objects.create(
            customer=customer, room=room,
            check_in=date.today() + timedelta(days=1),
            check_out=date.today() + timedelta(days=2), total="3000.00",
        )
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.delete(
            f"/api/v1/admin/users/{customer.pk}/", {"confirm_username": customer.username}, format="json"
        ).status_code, 204)
        self.assertFalse(User.objects.filter(pk=customer.pk).exists())
        self.assertFalse(Booking.objects.filter(pk=booking.pk).exists())
        self.assertTrue(Hotel.objects.filter(pk=hotel.pk).exists())
        self.assertTrue(User.objects.filter(pk=admin.pk).exists())

    def test_administrator_cannot_be_deleted(self):
        owner, customer, other, admin, hotel, floor, room = fixture()
        self.client.force_authenticate(admin)
        response = self.client.delete(
            f"/api/v1/admin/users/{admin.pk}/", {"confirm_username": admin.username}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=admin.pk).exists())
