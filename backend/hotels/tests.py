from django.db import IntegrityError, transaction
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from tempfile import TemporaryDirectory
from pathlib import Path
from rest_framework.test import APITestCase
from bookings.tests import fixture
from .models import Hotel, HotelPhoto
from .location import CITY_NAME, PROVINCE_NAME
from bookings.models import Booking
from payments.models import Payment
from reviews.models import Review
from promotions.models import Promotion
from rooms.models import Floor, Room, RoomPhoto
from datetime import date, timedelta


class CalapanLocationTests(APITestCase):
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
        self.client.force_authenticate(self.owner)

    def payload(self, **changes):
        return dict(
            name="Local Calapan Stay",
            description="A local test property.",
            address="Test Street, Calapan City",
            latitude="13.400000",
            longitude="121.183333",
            **changes,
        )

    def test_omitted_city_defaults_to_calapan(self):
        response = self.client.post("/api/v1/hotels/", self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["city"], CITY_NAME)
        self.assertEqual(Hotel.objects.get(pk=response.data["id"]).city, CITY_NAME)

    def test_pending_owner_cannot_create_hotel(self):
        self.owner.owner_approval_status = "pending"
        self.owner.save(update_fields=["owner_approval_status"])
        response = self.client.post("/api/v1/hotels/", self.payload(), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(Hotel.objects.count(), 1)

    def test_admin_users_page_includes_owner_hotel_details(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/admin/users/")
        self.assertEqual(response.status_code, 200)
        owner = next(user for user in response.data if user["id"] == self.owner.id)
        self.assertEqual(owner["role"], "owner")
        self.assertEqual(owner["display_name"], self.owner.username)
        self.assertEqual(owner["hotels"][0]["name"], self.hotel.name)

    def test_admin_can_monitor_property_rooms_and_reservations(self):
        booking = Booking.objects.create(
            customer=self.customer, room=self.room,
            check_in=date.today() + timedelta(days=2),
            check_out=date.today() + timedelta(days=3),
            total=self.room.price,
        )
        url = f"/api/v1/admin/hotels/{self.hotel.pk}/"
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["hotel"]["owner"], self.owner.username)
        self.assertEqual(response.data["floors"][0]["id"], self.floor.pk)
        self.assertEqual(response.data["rooms"][0]["floor_id"], self.floor.pk)
        self.assertEqual(response.data["rooms"][0]["number"], self.room.number)
        self.assertEqual(response.data["rooms"][0]["beds"], self.room.beds)
        self.assertEqual(response.data["rooms"][0]["photos"], [])
        self.assertEqual(response.data["bookings"][0]["id"], booking.pk)
        self.assertEqual(response.data["bookings"][0]["room_id"], self.room.pk)
        self.assertEqual(response.data["bookings"][0]["customer__username"], self.customer.username)

    def test_only_admin_can_delete_hotel_and_its_records(self):
        booking = Booking.objects.create(
            customer=self.customer, room=self.room,
            check_in=date.today() + timedelta(days=2),
            check_out=date.today() + timedelta(days=3), total=self.room.price,
        )
        payment = Payment.objects.create(booking=booking, amount=self.room.price)
        review = Review.objects.create(booking=booking, rating=5, comment="Great stay")
        promotion = Promotion.objects.create(
            hotel=self.hotel, code="DELETE-TEST", percent=10,
            starts_on=date.today(), ends_on=date.today() + timedelta(days=10),
        )
        other_hotel = Hotel.objects.create(
            owner=self.owner, name="Keep this hotel", description="Still available",
            city=CITY_NAME, address="Another street", latitude=13.4, longitude=121.18,
        )
        url = f"/api/v1/admin/hotels/{self.hotel.pk}/"
        self.assertEqual(self.client.delete(url, {"confirm_name": self.hotel.name}, format="json").status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(url, {"confirm_name": "wrong"}, format="json").status_code, 400)
        self.assertTrue(Hotel.objects.filter(pk=self.hotel.pk).exists())

        with TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir):
            hotel_photo = HotelPhoto.objects.create(
                hotel=self.hotel, image=SimpleUploadedFile("hotel.jpg", b"hotel image")
            )
            room_photo = RoomPhoto.objects.create(
                room=self.room, image=SimpleUploadedFile("room.jpg", b"room image")
            )
            hotel_file = Path(media_dir) / hotel_photo.image.name
            room_file = Path(media_dir) / room_photo.image.name
            self.assertTrue(hotel_file.exists())
            self.assertTrue(room_file.exists())
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.delete(url, {"confirm_name": self.hotel.name}, format="json")
            self.assertEqual(response.status_code, 204, response.data)
            self.assertFalse(hotel_file.exists())
            self.assertFalse(room_file.exists())

        for model, pk in (
            (Hotel, self.hotel.pk), (Floor, self.floor.pk), (Room, self.room.pk),
            (Booking, booking.pk), (Payment, payment.pk), (Review, review.pk),
            (Promotion, promotion.pk),
        ):
            self.assertFalse(model.objects.filter(pk=pk).exists(), model.__name__)
        self.assertTrue(Hotel.objects.filter(pk=other_hotel.pk).exists())
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_owner_and_admin_cannot_create_outside_calapan(self):
        for user in [self.owner, self.admin]:
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                response = self.client.post(
                    "/api/v1/hotels/", self.payload(city="Manila"), format="json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("city", response.data)
        self.assertEqual(Hotel.objects.count(), 1)

    def test_owner_and_admin_cannot_move_a_property_to_another_city(self):
        for user in [self.owner, self.admin]:
            with self.subTest(role=user.role):
                self.client.force_authenticate(user)
                response = self.client.patch(
                    f"/api/v1/hotels/{self.hotel.pk}/",
                    {"city": "Batangas"},
                    format="json",
                )
                self.assertEqual(response.status_code, 400)
        self.hotel.refresh_from_db()
        self.assertEqual(self.hotel.city, CITY_NAME)
        self.assertEqual(self.hotel.status, "verified")

    def test_database_rejects_outside_city_even_without_serializer(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Hotel.objects.filter(pk=self.hotel.pk).update(city="Tagaytay")
        self.hotel.refresh_from_db()
        self.assertEqual(self.hotel.city, CITY_NAME)

    def test_all_roles_and_nearby_search_only_return_calapan(self):
        for user in [None, self.customer, self.owner, self.admin]:
            with self.subTest(role=getattr(user, "role", "anonymous")):
                self.client.force_authenticate(user)
                response = self.client.get("/api/v1/hotels/")
                self.assertEqual(len(response.data), 1)
                self.assertTrue(all(h["city"] == CITY_NAME for h in response.data))
                self.assertEqual(
                    self.client.get("/api/v1/hotels/", {"city": "Manila"}).data, []
                )
                response = self.client.get(
                    "/api/v1/hotels/nearby/",
                    {"lat": 13.4, "lng": 121.183333, "radius": 50},
                )
                self.assertEqual(len(response.data), 1)
                self.assertTrue(all(h["city"] == CITY_NAME for h in response.data))

    def test_reports_and_csv_identify_the_service_location(self):
        for user in [self.owner, self.admin]:
            self.client.force_authenticate(user)
            response = self.client.get("/api/v1/reports/summary/")
            self.assertEqual(response.data["city"], CITY_NAME)
            self.assertEqual(response.data["province"], PROVINCE_NAME)
            self.assertEqual(response.data["hotel_count"], 1)
            response = self.client.get("/api/v1/reports/summary/?format=csv")
            self.assertIn(b"City,Province", response.content)
