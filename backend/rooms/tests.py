from datetime import timedelta
from tempfile import TemporaryDirectory
from io import StringIO
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from bookings.tests import fixture
from bookings.services import reserve
from bookings.models import Booking
from bookings.demo import DEMO_PREFIX
from payments.models import Payment
from accounts.models import User
from .models import Room


class RoomStateTests(APITestCase):
    def setUp(self):
        (
            self.owner,
            self.customer,
            self.other,
            self.admin,
            self.hotel,
            self.floor,
            self.available,
        ) = fixture()
        self.booked = Room.objects.create(
            floor=self.floor, number="102", row=0, column=1, price=1800, capacity=2
        )
        self.unavailable = Room.objects.create(
            floor=self.floor,
            number="103",
            row=0,
            column=2,
            price=1800,
            capacity=2,
            active=False,
        )
        self.today = timezone.localdate()
        reserve(
            self.customer,
            {
                "room": self.booked,
                "check_in": self.today,
                "check_out": self.today + timedelta(days=2),
                "guests": 1,
            },
        )
        self.client.force_authenticate(self.customer)

    def states(self, **params):
        response = self.client.get(
            "/api/v1/rooms/", dict(hotel=self.hotel.pk, **params)
        )
        self.assertEqual(response.status_code, 200)
        return {r["number"]: r for r in response.data}

    def test_today_distinguishes_available_booked_and_unavailable(self):
        rooms = self.states()
        self.assertEqual(rooms["101"]["availability_status"], "available")
        self.assertEqual(rooms["102"]["availability_status"], "booked")
        self.assertEqual(rooms["103"]["availability_status"], "unavailable")
        self.assertTrue(rooms["101"]["available"])
        self.assertFalse(rooms["102"]["available"])
        self.assertFalse(rooms["103"]["available"])

    def test_booked_state_is_date_specific_and_checkout_is_exclusive(self):
        rooms = self.states(
            check_in=str(self.today + timedelta(days=2)),
            check_out=str(self.today + timedelta(days=3)),
        )
        self.assertEqual(rooms["102"]["availability_status"], "available")
        self.assertEqual(rooms["103"]["availability_status"], "unavailable")

    def test_delete_eligibility_requires_ownership_and_no_reservation_history(self):
        self.assertTrue(all(not room["can_delete"] for room in self.states().values()))
        self.client.force_authenticate(self.owner)
        rooms = self.states()
        self.assertTrue(rooms["101"]["can_delete"])
        self.assertFalse(rooms["102"]["can_delete"])
        self.assertTrue(rooms["103"]["can_delete"])
        self.assertEqual(
            self.client.delete(f"/api/v1/rooms/{self.booked.pk}/").status_code, 400
        )
        self.assertEqual(Booking.objects.count(), 1)

    def test_owner_availability_change_blocks_new_reservations(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/v1/rooms/{self.available.pk}/",
            {"active": False, "availability_status": "available", "can_delete": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["availability_status"], "unavailable")
        self.assertTrue(response.data["can_delete"])
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            "/api/v1/bookings/",
            {
                "room": self.available.pk,
                "check_in": str(self.today + timedelta(days=3)),
                "check_out": str(self.today + timedelta(days=4)),
                "guests": 1,
            },
        )
        self.assertEqual(response.status_code, 400)


class DemoActivityTests(APITestCase):
    def test_demo_seed_is_idempotent_nonoverlapping_and_populates_real_reports(self):
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            call_command("seed_demo", stdout=StringIO())
            before = (Booking.objects.count(), Payment.objects.count())
            call_command("seed_demo_activity", stdout=StringIO())
            self.assertEqual(before, (Booking.objects.count(), Payment.objects.count()))
            demo = Booking.objects.filter(special_requests__startswith=DEMO_PREFIX)
            self.assertGreater(demo.count(), 0)
            for room in Room.objects.all():
                bookings = list(
                    room.bookings.filter(status="confirmed").order_by("check_in")
                )
                for first, second in zip(bookings, bookings[1:]):
                    self.assertLessEqual(first.check_out, second.check_in)
            for booking in demo.select_related("payment"):
                self.assertEqual(booking.payment.amount, booking.total)
                self.assertEqual(booking.payment.status, "approved")
            self.assertTrue(
                all(
                    not u.has_usable_password()
                    for u in User.objects.filter(username__startswith="rf_demo_guest_")
                )
            )
            self.client.force_authenticate(User.objects.get(username="hotelowner"))
            report = self.client.get("/api/v1/reports/summary/").data
            self.assertEqual(report["demo_booking_count"], demo.count())
            self.assertTrue(
                all(
                    day["bookings"] > 0 and day["revenue"] > 0
                    for day in report["trend"]
                )
            )
            self.assertGreater(report["occupancy"], 0)
            self.assertTrue(
                any(b["is_demo"] for b in self.client.get("/api/v1/bookings/").data)
            )
