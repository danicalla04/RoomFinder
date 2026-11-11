import uuid
from django.db import models
from django.conf import settings


class Booking(models.Model):
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    room = models.ForeignKey(
        "rooms.Room", on_delete=models.PROTECT, related_name="bookings"
    )
    check_in = models.DateField()
    check_out = models.DateField()
    guests = models.PositiveSmallIntegerField(default=1)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    promotion_code = models.CharField(max_length=32, blank=True)
    status = models.CharField(
        max_length=12,
        choices=[("confirmed", "Confirmed"), ("cancelled", "Cancelled")],
        default="confirmed",
    )
    special_requests = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["room", "status", "check_in", "check_out"])]
        constraints = [
            models.CheckConstraint(
                check=models.Q(check_out__gt=models.F("check_in")),
                name="valid_booking_dates",
            ),
            models.CheckConstraint(
                check=models.Q(total__gte=0), name="booking_nonnegative_total"
            ),
            models.CheckConstraint(
                check=models.Q(guests__gte=1), name="booking_positive_guests"
            ),
        ]
