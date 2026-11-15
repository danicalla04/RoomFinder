from datetime import timedelta
from decimal import Decimal
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


class MeasuredPlanTests(APITestCase):
    def setUp(self):
        self.owner, self.customer, _, _, self.hotel, self.floor, self.existing = fixture()
        self.client.force_authenticate(self.owner)

    def test_owner_can_create_a_floor_with_measured_dimensions(self):
        response = self.client.post("/api/v1/floors/", {
            "hotel": self.hotel.pk, "number": 2, "name": "Second floor",
            "columns": 6, "plan_width_m": "24.00", "plan_height_m": "16.00",
            "areas": [{"label": "Outdoor pool", "x": 2, "y": 2, "width": 6, "height": 4}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["plan_width_m"], "24.00")
        self.assertEqual(response.data["plan_height_m"], "16.00")
        self.assertEqual(response.data["areas"][0]["label"], "Outdoor pool")
        response = self.client.patch(f"/api/v1/floors/{response.data['id']}/", {
            "areas": [{"label": "Lagoon pool", "x": 3, "y": 3, "width": 7, "height": 4}],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["areas"][0]["x"], 3)
        self.assertEqual(response.data["areas"][0]["label"], "Lagoon pool")

    def test_room_box_and_bathroom_are_measured_and_booking_is_preserved(self):
        plan = {
            "x": 6, "y": 0, "width": 4, "height": 5,
            "zones": [{"label": "Private bath", "x": 0, "y": 0, "width": 1.5, "height": 2}],
        }
        response = self.client.post("/api/v1/rooms/", {
            "floor": self.floor.pk, "number": "102", "price": "2200.00",
            "row": 0, "column": 1, "plan": plan,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        room = Room.objects.get(pk=response.data["id"])
        self.assertEqual(room.area, 20)
        self.assertEqual(room.plan["zones"][0]["label"], "Private bath")

        booking = Booking.objects.create(
            customer=self.customer, room=room,
            check_in=self.floor.hotel.created_at.date() + timedelta(days=1),
            check_out=self.floor.hotel.created_at.date() + timedelta(days=2), total="2200.00",
        )
        response = self.client.patch(f"/api/v1/rooms/{room.pk}/", {
            "plan": {**plan, "x": 7, "width": 5},
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Room.objects.get(pk=room.pk).area, 25)
        self.assertTrue(Booking.objects.filter(pk=booking.pk, room=room).exists())
        renamed = {**plan, "x": 7, "width": 5, "zones": [{**plan["zones"][0], "label": "Bathroom beside bed"}]}
        response = self.client.patch(f"/api/v1/rooms/{room.pk}/", {"plan": renamed}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["plan"]["zones"][0]["label"], "Bathroom beside bed")

    def test_overlap_outside_floor_and_invalid_interior_area_are_rejected(self):
        room = Room.objects.create(floor=self.floor, number="102", row=0, column=1, price=2200)
        url = f"/api/v1/rooms/{room.pk}/"
        for plan in (
            {"x": 2, "y": 2, "width": 4, "height": 4, "zones": []},
            {"x": 29, "y": 0, "width": 4, "height": 4, "zones": []},
            {"x": 6, "y": 0, "width": 4, "height": 4, "zones": [
                {"kind": "kitchen", "x": 3, "y": 0, "width": 2, "height": 2},
            ]},
        ):
            with self.subTest(plan=plan):
                response = self.client.patch(url, {"plan": plan}, format="json")
                self.assertEqual(response.status_code, 400)
        self.assertIsNone(Room.objects.get(pk=room.pk).plan)

    def test_floor_area_cannot_cover_a_room_and_room_cannot_cover_floor_area(self):
        response = self.client.patch(f"/api/v1/floors/{self.floor.pk}/", {
            "areas": [{"label": "Pool", "x": 2, "y": 2, "width": 4, "height": 4}],
        }, format="json")
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(f"/api/v1/floors/{self.floor.pk}/", {
            "areas": [{"label": "Pool", "x": 6, "y": 0, "width": 4, "height": 4}],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post("/api/v1/rooms/", {
            "floor": self.floor.pk, "number": "102", "price": "2000.00",
            "row": 0, "column": 1,
            "plan": {"x": 6, "y": 0, "width": 4, "height": 4, "zones": []},
        }, format="json")
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
                self.assertEqual(booking.payment.amount, (booking.total / 2).quantize(Decimal("0.01")))
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
