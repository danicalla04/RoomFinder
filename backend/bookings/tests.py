from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from tempfile import TemporaryDirectory
from PIL import Image
from django.test import TransactionTestCase, override_settings
from django.db import close_old_connections
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework.exceptions import ValidationError
from accounts.models import User
from hotels.models import Hotel, HotelPhoto
from rooms.models import Floor, Room
from bookings.models import Booking
from payments.models import Payment
from promotions.models import Promotion
from notifications.models import Notification
from reviews.models import Review
from bookings.services import reserve


def fixture():
    owner = User.objects.create_user(
        username="owner",
        email="owner@test.local",
        password="Testing!9384",
        role="owner",
    )
    customer = User.objects.create_user(
        username="guest", email="guest@test.local", password="Testing!9384"
    )
    other = User.objects.create_user(
        username="other", email="other@test.local", password="Testing!9384"
    )
    admin = User.objects.create_user(
        username="admin",
        email="admin@test.local",
        password="Testing!9384",
        role="admin",
    )
    hotel = Hotel.objects.create(
        owner=owner,
        name="Test Retreat",
        city="Calapan City",
        address="1 Test Road",
        latitude=13.4,
        longitude=121.183333,
        description="A real test hotel.",
        status="verified",
        amenities=["Pool", "Wi-Fi"],
    )
    floor = Floor.objects.create(hotel=hotel, number=1, name="Garden", columns=6)
    room = Room.objects.create(
        floor=floor, number="101", price="2500.00", capacity=2, row=0, column=0
    )
    return owner, customer, other, admin, hotel, floor, room


class RoomFinderTests(APITestCase):
    def setUp(self):
        (
            self.owner,
            self.customer,
            self.other,
            self.admin,
            self.hotel,
            self.floor,
            self.room,
        ) = fixture()
        self.start = timezone.localdate() + timedelta(days=5)
        self.end = self.start + timedelta(days=2)
        self.client.force_authenticate(self.customer)

    def payload(self, **kw):
        return dict(
            room=self.room.pk,
            check_in=str(self.start),
            check_out=str(self.end),
            guests=2,
            **kw,
        )

    def book(self, **kw):
        response = self.client.post(
            "/api/v1/bookings/", self.payload(**kw), format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_registration_cannot_escalate_role(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "username": "attacker",
                "email": "attacker@test.local",
                "password": "ValidPassword!938",
                "role": "admin",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_owner_registration_and_jwt_login(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "username": "newowner",
                "email": "new@test.local",
                "password": "StrongUnique!938",
                "role": "owner",
            },
        )
        self.assertEqual(response.status_code, 201, response.data)
        tokens = self.client.post(
            "/api/v1/auth/token/",
            {"username": "newowner", "password": "StrongUnique!938"},
        )
        self.assertEqual(tokens.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens.data["access"])
        self.assertEqual(self.client.get("/api/v1/auth/me/").data["role"], "owner")

    def test_profile_cannot_change_role(self):
        self.client.patch("/api/v1/auth/me/", {"role": "admin", "first_name": "Alex"})
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, "customer")
        self.assertEqual(self.customer.first_name, "Alex")

    def test_confirmation_payment_and_notification_are_persisted(self):
        b = self.book(total="1.00", status="cancelled")
        self.assertEqual(Decimal(b["total"]), Decimal("5000"))
        self.assertEqual(b["status"], "confirmed")
        self.assertEqual(b["payment"]["status"], "approved")
        self.assertEqual(Payment.objects.count(), 1)
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer, title="Reservation confirmed"
            ).exists()
        )

    def test_overlap_rejected_adjacent_allowed(self):
        self.book()
        r = self.client.post("/api/v1/bookings/", self.payload(), format="json")
        self.assertEqual(r.status_code, 400)
        data = self.payload()
        data["check_in"] = str(self.end)
        data["check_out"] = str(self.end + timedelta(days=1))
        self.assertEqual(
            self.client.post("/api/v1/bookings/", data, format="json").status_code, 201
        )
        self.assertEqual(Booking.objects.count(), 2)

    def test_containing_and_partial_overlap_rejected(self):
        self.book()
        for start, end in [
            (self.start - timedelta(days=1), self.end + timedelta(days=1)),
            (self.start - timedelta(days=1), self.start + timedelta(days=1)),
            (self.start + timedelta(days=1), self.end + timedelta(days=2)),
        ]:
            data = self.payload()
            data.update(check_in=str(start), check_out=str(end))
            self.assertEqual(
                self.client.post("/api/v1/bookings/", data, format="json").status_code,
                400,
            )

    def test_date_capacity_and_zero_guests_validation(self):
        for changes in [
            {"guests": 3},
            {"guests": 0},
            {"check_out": str(self.start)},
            {"check_in": str(timezone.localdate() - timedelta(days=1))},
        ]:
            data = self.payload()
            data.update(changes)
            self.assertEqual(
                self.client.post("/api/v1/bookings/", data, format="json").status_code,
                400,
            )
        self.assertEqual(Booking.objects.count(), 0)

    def test_cancel_refunds_payment_and_frees_room(self):
        b = self.book()
        url = f"/api/v1/bookings/{b['id']}/cancel/"
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(Payment.objects.get().status, "refunded")
        self.book()

    def test_customers_cannot_see_or_cancel_other_bookings(self):
        b = self.book()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/v1/bookings/").data, [])
        self.assertEqual(
            self.client.post(f"/api/v1/bookings/{b['id']}/cancel/").status_code, 404
        )
        self.assertEqual(self.client.get("/api/v1/payments/").data, [])

    def test_owners_only_see_own_reservations(self):
        b = self.book()
        self.client.force_authenticate(self.owner)
        self.assertEqual(len(self.client.get("/api/v1/bookings/").data), 1)
        self.assertEqual(
            self.client.post(f"/api/v1/bookings/{b['id']}/cancel/").status_code, 403
        )
        another = User.objects.create_user(
            username="anotherowner", email="another@test.local", role="owner"
        )
        self.client.force_authenticate(another)
        self.assertEqual(self.client.get("/api/v1/bookings/").data, [])

    def test_owners_cannot_create_customer_bookings(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(
            self.client.post(
                "/api/v1/bookings/", self.payload(), format="json"
            ).status_code,
            403,
        )

    def test_unverified_hotels_hidden_and_cannot_be_booked(self):
        self.hotel.status = "pending"
        self.hotel.save()
        self.assertEqual(self.client.get("/api/v1/hotels/").data, [])
        self.assertEqual(
            self.client.post(
                "/api/v1/bookings/", self.payload(), format="json"
            ).status_code,
            400,
        )
        self.client.force_authenticate(self.owner)
        self.assertEqual(
            len(self.client.get("/api/v1/hotels/", {"mine": "true"}).data), 1
        )

    def test_only_admin_verifies_hotel(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(
            self.client.post(
                f"/api/v1/hotels/{self.hotel.pk}/verify/", {"status": "verified"}
            ).status_code,
            403,
        )
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.post(
                f"/api/v1/hotels/{self.hotel.pk}/verify/", {"status": "verified"}
            ).status_code,
            200,
        )

    def test_foreign_room_floor_and_promotion_edits_forbidden(self):
        stranger = User.objects.create_user(
            username="stranger", email="stranger@test.local", role="owner"
        )
        self.client.force_authenticate(stranger)
        self.assertEqual(
            self.client.patch(
                f"/api/v1/rooms/{self.room.pk}/", {"price": "1.00"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/floors/{self.floor.pk}/", {"name": "Hacked"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/hotels/{self.hotel.pk}/", {"name": "Hacked"}
            ).status_code,
            403,
        )
        self.room.refresh_from_db()
        self.assertEqual(self.room.price, Decimal("2500"))

    def test_layout_prevents_duplicate_position_and_shrinking_over_rooms(self):
        self.client.force_authenticate(self.owner)
        data = {
            "floor": self.floor.pk,
            "number": "102",
            "price": "1500",
            "capacity": 2,
            "row": 0,
            "column": 0,
        }
        self.assertEqual(self.client.post("/api/v1/rooms/", data).status_code, 400)
        self.room.column = 5
        self.room.save()
        self.assertEqual(
            self.client.patch(
                f"/api/v1/floors/{self.floor.pk}/", {"columns": 3}
            ).status_code,
            400,
        )

    def test_room_crud_and_protected_booking_history(self):
        self.client.force_authenticate(self.owner)
        r = self.client.post(
            "/api/v1/rooms/",
            {
                "floor": self.floor.pk,
                "number": "102",
                "price": "1500",
                "capacity": 2,
                "row": 0,
                "column": 1,
            },
        )
        self.assertEqual(r.status_code, 201, r.data)
        url = f"/api/v1/rooms/{r.data['id']}/"
        self.assertEqual(self.client.patch(url, {"price": "1800"}).status_code, 200)
        self.assertEqual(self.client.get(url).data["price"], "1800.00")
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.client.force_authenticate(self.customer)
        self.book()
        self.client.force_authenticate(self.owner)
        self.assertEqual(
            self.client.delete(f"/api/v1/rooms/{self.room.pk}/").status_code, 400
        )

    def test_promotion_discount_and_expiry(self):
        Promotion.objects.create(
            hotel=self.hotel,
            code="SAVE10",
            percent=10,
            starts_on=timezone.localdate(),
            ends_on=self.end,
        )
        b = self.book(promotion_code="save10")
        self.assertEqual(Decimal(b["total"]), Decimal("4500"))
        self.assertEqual(Decimal(b["discount"]), Decimal("500"))
        self.client.post(f"/api/v1/bookings/{b['id']}/cancel/")
        Promotion.objects.update(
            ends_on=timezone.localdate() - timedelta(days=1),
            starts_on=timezone.localdate() - timedelta(days=2),
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/bookings/",
                self.payload(promotion_code="SAVE10"),
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(Payment.objects.count(), 1)

    def test_payment_failure_rolls_back_entire_reservation(self):
        with patch(
            "bookings.services.Payment.objects.create",
            side_effect=RuntimeError("simulated database failure"),
        ):
            with self.assertRaises(RuntimeError):
                reserve(
                    self.customer,
                    {
                        "room": self.room,
                        "check_in": self.start,
                        "check_out": self.end,
                        "guests": 2,
                    },
                )
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_availability_and_search_filters(self):
        self.book()
        params = {
            "hotel": self.hotel.pk,
            "check_in": str(self.start),
            "check_out": str(self.end),
        }
        self.assertFalse(self.client.get("/api/v1/rooms/", params).data[0]["available"])
        self.assertEqual(
            self.client.get(
                "/api/v1/hotels/",
                {"check_in": str(self.start), "check_out": str(self.end)},
            ).data,
            [],
        )
        self.assertEqual(
            len(
                self.client.get(
                    "/api/v1/hotels/",
                    {"search": "Calapan", "max_price": 3000, "amenities": "Pool"},
                ).data
            ),
            1,
        )
        self.assertEqual(
            self.client.get("/api/v1/hotels/", {"max_price": 1000}).data, []
        )
        self.assertEqual(
            self.client.get(
                "/api/v1/rooms/", {"check_in": "bad", "check_out": "bad"}
            ).status_code,
            400,
        )

    def test_nearby_distance(self):
        r = self.client.get(
            "/api/v1/hotels/nearby/", {"lat": 13.4, "lng": 121.183333, "radius": 10}
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data[0]["distance_km"], 0)
        self.assertEqual(
            self.client.get(
                "/api/v1/hotels/nearby/", {"lat": "nan", "lng": 121}
            ).status_code,
            400,
        )

    def test_reports_role_scope_and_csv(self):
        self.book()
        self.assertEqual(self.client.get("/api/v1/reports/summary/").status_code, 403)
        self.client.force_authenticate(self.owner)
        r = self.client.get("/api/v1/reports/summary/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["booking_count"], 1)
        csv = self.client.get("/api/v1/reports/summary/?format=csv")
        self.assertEqual(csv.status_code, 200)
        self.assertIn(b"Test Retreat", csv.content)

    def test_notifications_are_private(self):
        Notification.objects.create(user=self.other, title="Private", message="Secret")
        self.assertEqual(self.client.get("/api/v1/notifications/").data, [])
        self.client.post("/api/v1/notifications/read_all/")
        self.assertFalse(Notification.objects.get().read)

    def test_review_only_after_completed_own_stay(self):
        b = self.book()
        r = self.client.post(
            "/api/v1/reviews/",
            {"booking": b["id"], "rating": 5, "comment": "Very good."},
        )
        self.assertEqual(r.status_code, 400)
        Booking.objects.filter(pk=b["id"]).update(
            check_in=timezone.localdate() - timedelta(days=3),
            check_out=timezone.localdate() - timedelta(days=1),
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/reviews/",
                {"booking": b["id"], "rating": 5, "comment": "Very good."},
            ).status_code,
            201,
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/reviews/",
                {"booking": b["id"], "rating": 5, "comment": "Again"},
            ).status_code,
            400,
        )

    def test_image_upload_stored_and_unauthorized_upload_rejected(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):

            def upload():
                buffer = BytesIO()
                Image.new("RGB", (8, 8), "green").save(buffer, format="PNG")
                return SimpleUploadedFile(
                    "hotel.png", buffer.getvalue(), content_type="image/png"
                )

            self.assertEqual(
                self.client.post(
                    "/api/v1/hotel-photos/",
                    {"hotel": self.hotel.pk, "image": upload()},
                    format="multipart",
                ).status_code,
                403,
            )
            self.client.force_authenticate(self.owner)
            r = self.client.post(
                "/api/v1/hotel-photos/",
                {"hotel": self.hotel.pk, "image": upload(), "caption": "Garden"},
                format="multipart",
            )
            self.assertEqual(r.status_code, 201, r.data)
            photo = HotelPhoto.objects.get()
            self.assertTrue(photo.image.storage.exists(photo.image.name))


class ConcurrentReservationTests(TransactionTestCase):
    reset_sequences = True

    def test_two_connections_competing_for_one_room(self):
        owner, customer, other, admin, hotel, floor, room = fixture()
        barrier = Barrier(2)
        start = timezone.localdate() + timedelta(days=10)

        def attempt(user_id):
            close_old_connections()
            try:
                user = User.objects.get(pk=user_id)
                r = Room.objects.get(pk=room.pk)
                barrier.wait(timeout=10)
                reserve(
                    user,
                    {
                        "room": r,
                        "check_in": start,
                        "check_out": start + timedelta(days=2),
                        "guests": 1,
                    },
                )
                return "confirmed"
            except ValidationError:
                return "conflict"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, [customer.pk, other.pk]))
        self.assertCountEqual(results, ["confirmed", "conflict"])
        self.assertEqual(Booking.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
