from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.PROTECT, related_name="review"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
