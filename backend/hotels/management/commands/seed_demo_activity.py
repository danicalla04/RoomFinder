from datetime import datetime, time, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from accounts.models import User
from hotels.models import Hotel
from hotels.demo_data import DEMO_HOTELS
from rooms.models import Room
from bookings.models import Booking
from bookings.services import reserve
from bookings.demo import DEMO_PREFIX
from payments.models import Payment


class Command(BaseCommand):
    help = "Add clearly marked, idempotent demo activity for the four Calapan sample hotels; preserve existing reservations."

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()
        now = timezone.now()
        hotels = Hotel.objects.filter(
            owner__username="hotelowner",
            name__in=[spec[0] for spec in DEMO_HOTELS],
            status="verified",
        )
        if not hotels.exists():
            self.stdout.write(
                "No verified sample properties found; run seed_demo first."
            )
            return
        customers = []
        for index, first in enumerate(["Maya", "Luis", "Sofia", "Daniel"], start=1):
            username = f"rf_demo_guest_{index}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@roomfinder.test",
                    "first_name": first,
                    "last_name": "Demo",
                    "role": "customer",
                },
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            if user.role != "customer":
                raise CommandError(
                    f"{username} is not a customer; no role will be changed."
                )
            customers.append(user)
        created_count = unavailable_count = skipped = 0
        for index, hotel in enumerate(hotels.order_by("pk")):
            rooms = {
                room.number: room
                for room in Room.objects.filter(
                    floor__hotel=hotel, floor__number=1
                ).select_related("floor__hotel")
            }
            maintenance = rooms.get("112")
            if (
                maintenance
                and maintenance.active
                and not maintenance.bookings.filter(
                    status="confirmed", check_out__gt=today
                ).exists()
            ):
                maintenance.active = False
                maintenance.save(update_fields=["active"])
                unavailable_count += 1
            scenarios = [
                (
                    today - timedelta(days=offset),
                    str(105 + 6 - offset),
                    today - timedelta(days=offset),
                    today - timedelta(days=offset) + timedelta(days=1),
                    "daily",
                )
                for offset in range(6, -1, -1)
            ]
            scenarios += [
                (today, number, today, today + timedelta(days=3), f"booked-{number}")
                for number in ["103", "104"]
            ]
            for created_day, number, start, end, kind in scenarios:
                marker = f"{DEMO_PREFIX} activity hotel={hotel.pk} day={created_day.isoformat()} scenario={kind}"
                if Booking.objects.filter(special_requests=marker).exists():
                    continue
                room = rooms.get(number)
                if not room or not room.active:
                    skipped += 1
                    continue
                if room.bookings.filter(
                    status="confirmed", check_in__lt=end, check_out__gt=start
                ).exists():
                    skipped += 1
                    continue
                try:
                    booking = reserve(
                        customers[(index + created_day.day) % len(customers)],
                        {
                            "room": room,
                            "check_in": start,
                            "check_out": end,
                            "guests": min(2, room.capacity),
                            "special_requests": marker,
                        },
                    )
                except ValidationError:
                    skipped += 1
                    continue
                created_at = min(
                    now,
                    timezone.make_aware(
                        datetime.combine(created_day, time(12)),
                        timezone.get_current_timezone(),
                    ),
                )
                Booking.objects.filter(pk=booking.pk).update(created_at=created_at)
                Payment.objects.filter(booking=booking).update(created_at=created_at)
                created_count += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo activity ready: {created_count} new simulated reservations, {unavailable_count} sample rooms marked unavailable, {skipped} conflicting/missing scenarios skipped. Existing reservations were preserved."
            )
        )
