from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.files import File
from django.db import transaction
from django.utils import timezone
from accounts.models import User
from hotels.models import Hotel, HotelPhoto
from hotels.demo_data import DEMO_HOTELS
from rooms.models import Floor, Room, RoomPhoto
from bookings.models import Booking
from payments.models import Payment
from promotions.models import Promotion
from reviews.models import Review
from notifications.models import Notification


class Command(BaseCommand):
    help = "Create idempotent local demo data. Never resets existing passwords or hotel records."

    @transaction.atomic
    def handle(self, *args, **options):
        users = {}
        for name, role, first in [
            ("traveler", "customer", "Alex"),
            ("hotelowner", "owner", "Isabel"),
            ("administrator", "admin", "Sam"),
        ]:
            user, created = User.objects.get_or_create(
                username=name,
                defaults={
                    "email": f"{name}@roomfinder.test",
                    "role": role,
                    "first_name": first,
                    "is_staff": role == "admin",
                    "is_superuser": role == "admin",
                },
            )
            if created:
                user.set_password("RoomFinder!2026")
                user.save()
            users[role] = user
        specs = DEMO_HOTELS
        for idx, (
            name,
            city,
            description,
            lat,
            lng,
            price,
            address,
            stars,
            amenities,
            photo,
        ) in enumerate(specs):
            hotel, created = Hotel.objects.get_or_create(
                name=name,
                owner=users["owner"],
                defaults={
                    "city": city,
                    "description": description,
                    "latitude": lat,
                    "longitude": lng,
                    "address": address,
                    "stars": stars,
                    "amenities": amenities,
                    "status": "verified",
                },
            )
            if not created:
                continue
            source = (
                Path(__file__).resolve().parents[4]
                / "database"
                / "sample_images"
                / photo
            )
            if source.exists():
                with source.open("rb") as f:
                    HotelPhoto.objects.create(
                        hotel=hotel, image=File(f, name=photo), caption=name
                    )
            for number in [1, 2]:
                floor = Floor.objects.create(
                    hotel=hotel,
                    number=number,
                    name=f'{"Garden" if number==1 else "Sky"} floor',
                    columns=6,
                )
                for i in range(12):
                    room = Room.objects.create(
                        floor=floor,
                        number=str(number * 100 + i + 1),
                        kind="Suite" if i % 5 == 0 else "Deluxe",
                        price=price + (1000 if i % 5 == 0 else 0) + (number - 1) * 250,
                        capacity=4 if i % 5 == 0 else 2,
                        beds="1 king + sofa bed" if i % 5 == 0 else "1 queen bed",
                        area=42 if i % 5 == 0 else 28,
                        row=i // 6,
                        column=i % 6,
                        description="Natural textures, crisp linens, a private bathroom, air conditioning, and a peaceful view.",
                    )
                    room_source = source.parent / "room.jpg"
                    if i in [0, 1] and room_source.exists():
                        with room_source.open("rb") as f:
                            RoomPhoto.objects.create(
                                room=room,
                                image=File(f, name="room.jpg"),
                                caption="Room interior",
                            )
            Promotion.objects.get_or_create(
                code=f"STAY{idx+1}0",
                defaults={
                    "hotel": hotel,
                    "percent": 10,
                    "starts_on": timezone.localdate() - timedelta(days=1),
                    "ends_on": timezone.localdate() + timedelta(days=90),
                },
            )
            room = hotel.floors.first().rooms.first()
            past = Booking.objects.create(
                customer=users["customer"],
                room=room,
                check_in=timezone.localdate() - timedelta(days=8 + idx),
                check_out=timezone.localdate() - timedelta(days=6 + idx),
                guests=2,
                total=room.price * 2,
            )
            Payment.objects.create(booking=past, amount=past.total)
            Review.objects.create(
                booking=past,
                rating=5 if idx % 2 == 0 else 4,
                comment="A lovely stay. The room was comfortable, the team was welcoming, and the location was easy to explore.",
            )
        Notification.objects.get_or_create(
            user=users["customer"],
            title="Welcome to RoomFinder",
            defaults={
                "message": "Explore a stay, choose your exact room, and reserve with simulated payment. No real money is charged."
            },
        )
        call_command("seed_demo_activity", stdout=self.stdout)
        self.stdout.write(
            self.style.SUCCESS(
                "Demo data ready. traveler / hotelowner / administrator; password: RoomFinder!2026 (new accounts only)."
            )
        )
