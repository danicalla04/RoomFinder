from django.db import models
from django.core.validators import MinValueValidator


class Floor(models.Model):
    hotel = models.ForeignKey(
        "hotels.Hotel", on_delete=models.CASCADE, related_name="floors"
    )
    number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=80)
    columns = models.PositiveSmallIntegerField(
        default=6, validators=[MinValueValidator(1)]
    )

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(
                fields=["hotel", "number"], name="unique_hotel_floor"
            )
        ]


class Room(models.Model):
    floor = models.ForeignKey(Floor, on_delete=models.PROTECT, related_name="rooms")
    number = models.CharField(max_length=12)
    kind = models.CharField(max_length=40, default="Deluxe")
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(1)]
    )
    capacity = models.PositiveSmallIntegerField(
        default=2, validators=[MinValueValidator(1)]
    )
    beds = models.CharField(max_length=80, default="1 queen bed")
    area = models.PositiveSmallIntegerField(
        default=28, validators=[MinValueValidator(1)]
    )
    row = models.PositiveSmallIntegerField(default=0)
    column = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["floor__number", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["floor", "number"], name="unique_floor_room"
            ),
            models.UniqueConstraint(
                fields=["floor", "row", "column"], name="unique_floor_position"
            ),
            models.CheckConstraint(
                check=models.Q(price__gt=0), name="room_positive_price"
            ),
            models.CheckConstraint(
                check=models.Q(capacity__gte=1), name="room_positive_capacity"
            ),
        ]

    def __str__(self):
        return self.number


class RoomPhoto(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="rooms/%Y/%m/")
    caption = models.CharField(max_length=160, blank=True)
