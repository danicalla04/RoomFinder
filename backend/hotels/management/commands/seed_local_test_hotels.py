from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from hotels.models import Hotel, HotelPhoto
from rooms.models import Floor, Room, RoomPhoto


class Command(BaseCommand):
    help = "Create local-only Calapan test owners, verified hotels, measured floors, rooms, and photos."

    @transaction.atomic
    def handle(self, *args, **options):
        if not getattr(settings, "ROOMFINDER_LOCAL_ONLY", False):
            raise CommandError("This command only runs with localhost_settings; it never creates test data on a hosted database.")

        hero_path = Path(settings.BASE_DIR).parent / "frontend" / "public" / "hero.jpg"
        if not hero_path.exists():
            raise CommandError(f"Required local demo image is missing: {hero_path}")
        image_content = hero_path.read_bytes()

        specs = [
            {
                "username": "rf_test_owner_1",
                "email": "rf_test_owner_1@roomfinder.local",
                "name": "RoomFinder Test Retreat",
                "description": "A fictional Calapan City property for testing room photos, measured floor layouts, and booking flows.",
                "address": "Sample Layout Road, Calapan City, Oriental Mindoro",
                "latitude": Decimal("13.405000"),
                "longitude": Decimal("121.180000"),
                "base_price": Decimal("3200.00"),
            },
            {
                "username": "rf_test_owner_2",
                "email": "rf_test_owner_2@roomfinder.local",
                "name": "RoomFinder Floorplan Inn",
                "description": "A second fictional Calapan City property for comparing ground and first floor room layouts.",
                "address": "Sample Courtyard Street, Calapan City, Oriental Mindoro",
                "latitude": Decimal("13.410000"),
                "longitude": Decimal("121.185000"),
                "base_price": Decimal("2600.00"),
            },
        ]

        for spec in specs:
            owner, _ = User.objects.get_or_create(
                username=spec["username"],
                defaults={"email": spec["email"], "role": User.Role.OWNER},
            )
            owner.email = spec["email"]
            owner.role = User.Role.OWNER
            owner.owner_approval_status = User.OwnerApproval.APPROVED
            owner.is_active = True
            owner.first_name = "Test Owner"
            owner.save(update_fields=[
                "email", "role", "owner_approval_status",
                "is_active", "first_name",
            ])
            owner.set_password("RoomFinder!2026")
            owner.save(update_fields=["password"])

            hotel, _ = Hotel.objects.get_or_create(
                owner=owner,
                name=spec["name"],
                defaults={
                    "city": "Calapan City",
                    "description": spec["description"],
                    "address": spec["address"],
                    "latitude": spec["latitude"],
                    "longitude": spec["longitude"],
                    "amenities": ["Wi-Fi", "Parking", "Room layout demo"],
                    "status": "verified",
                },
            )
            if not hotel.photos.exists():
                HotelPhoto.objects.create(
                    hotel=hotel,
                    image=ContentFile(image_content, name=f"{owner.username}-hotel.jpg"),
                    caption="Local testing property photo",
                )

            for floor_number, floor_name in [(0, "Ground Floor"), (1, "First Floor")]:
                floor, _ = Floor.objects.get_or_create(
                    hotel=hotel,
                    number=floor_number,
                    defaults={
                        "name": floor_name,
                        "columns": 6,
                        "plan_width_m": Decimal("26.00"),
                        "plan_height_m": Decimal("18.00"),
                        "areas": [],
                    },
                )
                if floor.rooms.exists():
                    continue
                for position, (x, y) in enumerate([(1, 1), (13, 1), (1, 10), (13, 10)], start=1):
                    number = f"{floor_number}{position:02d}"
                    room = Room.objects.create(
                        floor=floor,
                        number=number,
                        kind="Suite" if position == 4 else "Deluxe",
                        description="A sample room with a measured floor-plan box and a bathroom area. Room photo is included for the guest preview.",
                        price=spec["base_price"] + Decimal((position - 1) * 500),
                        capacity=4 if position == 4 else 2,
                        beds="1 king bed" if position == 4 else "1 queen bed",
                        area=Decimal("70.00"),
                        row=(position - 1) // 2,
                        column=(position - 1) % 2,
                        plan={
                            "x": x,
                            "y": y,
                            "width": 10,
                            "height": 7,
                            "zones": [
                                {"label": "Bathroom", "x": 0.3, "y": 0.3, "width": 2.5, "height": 2.2},
                                {"label": "Bed area", "x": 4.0, "y": 2.0, "width": 5.5, "height": 4.5},
                            ],
                        },
                        active=True,
                    )
                    RoomPhoto.objects.create(
                        room=room,
                        image=ContentFile(image_content, name=f"{owner.username}-room-{number}.jpg"),
                        caption=f"Local testing photo for room {number}",
                    )

        self.stdout.write(self.style.SUCCESS(
            "Local test properties are ready. Both have a ground floor and first floor, four measured rooms per floor, room photos, and email-verified owner accounts."
        ))
        self.stdout.write("Test owner usernames: rf_test_owner_1 and rf_test_owner_2")
        self.stdout.write("Test owner password: RoomFinder!2026")
