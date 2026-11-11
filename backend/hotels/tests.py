from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase
from bookings.tests import fixture
from .models import Hotel
from .location import CITY_NAME, PROVINCE_NAME
from bookings.models import Booking
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
