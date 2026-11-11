from django.db import models
from django.conf import settings
from .location import CITY_NAME, LOCATION_LABEL
from django.core.validators import MinValueValidator, MaxValueValidator


class Hotel(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="hotels"
    )
    name = models.CharField(max_length=160)
    description = models.TextField()
    city = models.CharField(
        max_length=80,
        choices=[(CITY_NAME, CITY_NAME)],
        default=CITY_NAME,
        help_text=f"RoomFinder serves {LOCATION_LABEL} only.",
    )
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    amenities = models.JSONField(default=list)
    stars = models.PositiveSmallIntegerField(
        default=3, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    status = models.CharField(
        max_length=12,
        choices=[
            ("pending", "Pending"),
            ("verified", "Verified"),
            ("rejected", "Rejected"),
        ],
        default="pending",
    )
    verification_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(city=CITY_NAME), name="hotel_city_calapan_only"
            )
        ]

    def __str__(self):
        return self.name


class HotelPhoto(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="hotels/%Y/%m/")
    caption = models.CharField(max_length=160, blank=True)
